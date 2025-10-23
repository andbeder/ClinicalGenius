"""
Audit Logging System for Clinical Genius
Tracks all PHI access, modifications, and security events for HIPAA compliance
"""

import json
import logging
from datetime import datetime
from functools import wraps
from flask import request, g
from database.db import get_connection


class AuditLogger:
    """HIPAA-compliant audit logger"""

    # Event types
    EVENT_PHI_ACCESS = "phi_access"
    EVENT_PHI_MODIFY = "phi_modify"
    EVENT_PHI_EXPORT = "phi_export"
    EVENT_AUTH_SUCCESS = "auth_success"
    EVENT_AUTH_FAILURE = "auth_failure"
    EVENT_ACCESS_DENIED = "access_denied"
    EVENT_SYSTEM_CONFIG = "system_config"
    EVENT_BATCH_EXECUTE = "batch_execute"
    EVENT_PROMPT_CREATE = "prompt_create"
    EVENT_PROMPT_MODIFY = "prompt_modify"
    EVENT_DATASET_ACCESS = "dataset_access"
    EVENT_LLM_REQUEST = "llm_request"

    def __init__(self, log_file='logs/audit.log'):
        """Initialize audit logger"""
        self.log_file = log_file
        self.logger = self._setup_logger()
        self._init_db()

    def _setup_logger(self):
        """Setup JSON structured logging"""
        import os
        os.makedirs('logs', exist_ok=True)

        logger = logging.getLogger('audit')
        logger.setLevel(logging.INFO)

        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        handler = RotatingFileHandler(
            self.log_file,
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=50  # Keep 50 files = 5GB total
        )

        # JSON formatter
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _init_db(self):
        """Initialize audit log database table"""
        conn = get_connection()
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                user_id TEXT,
                ip_address TEXT,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                dataset_id TEXT,
                record_count INTEGER,
                success INTEGER NOT NULL,
                error_message TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
        ''')

        # Create indices for common queries
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp
            ON audit_log(timestamp DESC)
        ''')

        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_event_type
            ON audit_log(event_type)
        ''')

        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_dataset
            ON audit_log(dataset_id)
        ''')

        conn.commit()
        conn.close()

    def log(self, event_type, action, success=True, **kwargs):
        """
        Log an audit event

        Args:
            event_type: Type of event (use EVENT_* constants)
            action: Description of action performed
            success: Whether action succeeded
            **kwargs: Additional metadata (user_id, ip_address, resource_type, etc.)
        """
        timestamp = datetime.utcnow().isoformat() + 'Z'

        # Get user from Flask request context (set by middleware)
        user_id = kwargs.get('user_id')
        if not user_id:
            try:
                user_id = g.current_user if hasattr(g, 'current_user') else 'system'
            except RuntimeError:
                # Outside request context
                user_id = 'system'

        # Get IP address from Flask request context
        ip_address = kwargs.get('ip_address')
        if not ip_address:
            try:
                ip_address = g.user_ip if hasattr(g, 'user_ip') else None
            except RuntimeError:
                # Outside request context
                pass
            if not ip_address and request:
                try:
                    ip_address = request.remote_addr
                except RuntimeError:
                    pass

        # Build audit entry
        entry = {
            'timestamp': timestamp,
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address,
            'action': action,
            'resource_type': kwargs.get('resource_type'),
            'resource_id': kwargs.get('resource_id'),
            'dataset_id': kwargs.get('dataset_id'),
            'record_count': kwargs.get('record_count'),
            'success': success,
            'error_message': kwargs.get('error_message'),
            'metadata': json.dumps(kwargs.get('metadata', {}))
        }

        # Log to JSON file
        self.logger.info(json.dumps(entry))

        # Store in database
        try:
            conn = get_connection()
            c = conn.cursor()

            c.execute('''
                INSERT INTO audit_log (
                    timestamp, event_type, user_id, ip_address, action,
                    resource_type, resource_id, dataset_id, record_count,
                    success, error_message, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry['timestamp'],
                entry['event_type'],
                entry['user_id'],
                entry['ip_address'],
                entry['action'],
                entry['resource_type'],
                entry['resource_id'],
                entry['dataset_id'],
                entry['record_count'],
                1 if success else 0,
                entry['error_message'],
                entry['metadata'],
                timestamp
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            # Log database error but don't fail the request
            print(f"[AUDIT] Failed to write to database: {e}")

    def log_phi_access(self, dataset_id, record_count, action="read", **kwargs):
        """Log PHI access event"""
        self.log(
            self.EVENT_PHI_ACCESS,
            action=f"Accessed PHI from dataset {dataset_id}",
            dataset_id=dataset_id,
            record_count=record_count,
            resource_type='dataset',
            **kwargs
        )

    def log_phi_export(self, dataset_id, record_count, format='csv', **kwargs):
        """Log PHI export event"""
        self.log(
            self.EVENT_PHI_EXPORT,
            action=f"Exported {record_count} records from dataset {dataset_id} as {format}",
            dataset_id=dataset_id,
            record_count=record_count,
            resource_type='dataset',
            metadata={'format': format},
            **kwargs
        )

    def log_batch_execution(self, batch_id, batch_name, dataset_id, record_count, success=True, **kwargs):
        """Log batch execution event"""
        self.log(
            self.EVENT_BATCH_EXECUTE,
            action=f"Executed batch '{batch_name}' on {record_count} records",
            resource_type='batch',
            resource_id=batch_id,
            dataset_id=dataset_id,
            record_count=record_count,
            success=success,
            **kwargs
        )

    def log_llm_request(self, provider, model, record_id, success=True, **kwargs):
        """Log LLM API request"""
        self.log(
            self.EVENT_LLM_REQUEST,
            action=f"LLM request to {provider} ({model}) for record {record_id}",
            resource_type='llm_request',
            resource_id=record_id,
            success=success,
            metadata={'provider': provider, 'model': model},
            **kwargs
        )

    def log_access_denied(self, reason, **kwargs):
        """Log access denied event"""
        self.log(
            self.EVENT_ACCESS_DENIED,
            action=f"Access denied: {reason}",
            success=False,
            error_message=reason,
            **kwargs
        )

    def get_recent_logs(self, limit=100, event_type=None):
        """
        Get recent audit logs

        Args:
            limit: Maximum number of logs to return
            event_type: Optional filter by event type

        Returns:
            list: List of audit log entries
        """
        conn = get_connection()
        c = conn.cursor()

        if event_type:
            c.execute('''
                SELECT * FROM audit_log
                WHERE event_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (event_type, limit))
        else:
            c.execute('''
                SELECT * FROM audit_log
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))

        columns = [desc[0] for desc in c.description]
        rows = c.fetchall()
        conn.close()

        return [dict(zip(columns, row)) for row in rows]

    def get_logs_for_dataset(self, dataset_id, limit=100):
        """Get audit logs for specific dataset"""
        conn = get_connection()
        c = conn.cursor()

        c.execute('''
            SELECT * FROM audit_log
            WHERE dataset_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (dataset_id, limit))

        columns = [desc[0] for desc in c.description]
        rows = c.fetchall()
        conn.close()

        return [dict(zip(columns, row)) for row in rows]


# Global audit logger instance
_audit_logger = None


def get_audit_logger():
    """Get global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def audit_log(event_type, action=None):
    """
    Decorator to automatically log function calls

    Usage:
        @audit_log(AuditLogger.EVENT_PHI_ACCESS, "Access patient records")
        def get_records(dataset_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_audit_logger()
            action_desc = action or f"Called {func.__name__}"

            try:
                result = func(*args, **kwargs)
                logger.log(event_type, action_desc, success=True)
                return result
            except Exception as e:
                logger.log(event_type, action_desc, success=False, error_message=str(e))
                raise

        return wrapper
    return decorator
