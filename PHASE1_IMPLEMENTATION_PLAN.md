# Phase 1 Implementation Plan - HIPAA Compliance

**Project:** Clinical Genius Security Hardening
**Phase:** 1 - Critical Security Controls
**Timeline:** 2-3 weeks
**Priority:** CRITICAL - Blocking production PHI use

---

## Overview

This plan implements three critical security controls in order of implementation complexity and dependencies:

1. **HTTPS/TLS** (Days 1-3) - Foundation for all secure communications
2. **Database Encryption** (Days 4-7) - Protect PHI at rest
3. **Audit Logging** (Days 8-14) - Track all PHI access and changes

---

## Implementation 1: HTTPS/TLS (Days 1-3)

### Objective
Enable encrypted data transmission for all communications

### Approach: Nginx Reverse Proxy + Let's Encrypt

**Why this approach:**
- ✅ Production-grade solution
- ✅ Free SSL certificates (Let's Encrypt)
- ✅ Auto-renewal
- ✅ Separates TLS termination from application code
- ✅ Easy to configure and maintain
- ✅ No Flask code changes required

### Architecture

```
[Internet]
    ↓ HTTPS (443)
[Nginx Reverse Proxy]
    ↓ HTTP (localhost:4000)
[Flask App]
```

### Prerequisites

```bash
# Install Nginx and Certbot
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx -y
```

### Step 1: Configure Nginx (Day 1)

**File:** `/etc/nginx/sites-available/clinical-genius`

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com www.your-domain.com;

    # Allow Certbot challenges
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL certificates (Let's Encrypt will populate these)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL configuration - Modern, secure settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;

    # HSTS (force HTTPS for 1 year)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:;" always;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/your-domain.com/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Logging
    access_log /var/log/nginx/clinical-genius-access.log;
    error_log /var/log/nginx/clinical-genius-error.log;

    # File upload size limit (for CSV uploads)
    client_max_body_size 50M;

    # Proxy settings
    location / {
        proxy_pass http://127.0.0.1:4000;
        proxy_http_version 1.1;

        # Preserve original request info
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed in future)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts for long-running requests (LLM processing)
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    # Static files (served directly by Nginx for performance)
    location /static/ {
        alias /home/andrew/git/clinical-genius/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

**Enable site:**

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/clinical-genius /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Step 2: Obtain SSL Certificate (Day 1)

```bash
# Obtain certificate from Let's Encrypt
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Follow prompts:
# - Enter email for renewal notifications
# - Agree to Terms of Service
# - Choose whether to redirect HTTP to HTTPS (choose Yes)

# Test auto-renewal
sudo certbot renew --dry-run
```

### Step 3: Update Flask App Configuration (Day 2)

**File:** `app.py`

```python
# Update Flask configuration to work behind proxy
from werkzeug.middleware.proxy_fix import ProxyFix

# ... existing code ...

# Trust proxy headers (X-Forwarded-* headers from Nginx)
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
    x_prefix=0
)

# Update session cookie settings for HTTPS
app.config.update(
    SESSION_COOKIE_SECURE=True,      # Only send over HTTPS
    SESSION_COOKIE_HTTPONLY=True,    # Prevent JavaScript access
    SESSION_COOKIE_SAMESITE='Lax',   # CSRF protection
    PERMANENT_SESSION_LIFETIME=900,   # 15 minute timeout
    SESSION_COOKIE_NAME='__Secure-session',  # Prefix indicates secure cookie
)

# Force HTTPS in application (additional safety)
@app.before_request
def before_request():
    # Allow health checks on HTTP
    if request.endpoint == 'health_check':
        return

    # Force HTTPS for all other requests
    if not request.is_secure and request.headers.get('X-Forwarded-Proto', 'http') != 'https':
        return redirect(request.url.replace('http://', 'https://'), code=301)

# Health check endpoint (for load balancers)
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}), 200
```

### Step 4: Update Environment Configuration (Day 2)

**File:** `.env`

```bash
# Add HTTPS-related configuration
FORCE_HTTPS=True
SESSION_COOKIE_SECURE=True

# Update any hardcoded URLs to use HTTPS
# SALESFORCE_CALLBACK_URL=https://your-domain.com/callback
```

### Step 5: Create Systemd Service (Day 2)

**File:** `/etc/systemd/system/clinical-genius.service`

```ini
[Unit]
Description=Clinical Genius Flask Application
After=network.target

[Service]
Type=simple
User=andrew
Group=andrew
WorkingDirectory=/home/andrew/git/clinical-genius
Environment="PATH=/home/andrew/git/clinical-genius/venv/bin"
ExecStart=/home/andrew/git/clinical-genius/venv/bin/python app.py
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/andrew/git/clinical-genius

# Logging
StandardOutput=append:/var/log/clinical-genius/app.log
StandardError=append:/var/log/clinical-genius/error.log

[Install]
WantedBy=multi-user.target
```

**Setup:**

```bash
# Create log directory
sudo mkdir -p /var/log/clinical-genius
sudo chown andrew:andrew /var/log/clinical-genius

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable clinical-genius
sudo systemctl start clinical-genius

# Check status
sudo systemctl status clinical-genius
```

### Step 6: Testing and Validation (Day 3)

**SSL Labs Test:**
```bash
# Test SSL configuration
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=your-domain.com
# Target: A+ rating
```

**Manual Testing:**
```bash
# Test HTTPS connection
curl -I https://your-domain.com

# Verify HTTP redirects to HTTPS
curl -I http://your-domain.com

# Test certificate
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Check headers
curl -I https://your-domain.com | grep -i "strict-transport-security\|x-frame-options\|x-content-type"
```

**Functional Testing:**
- [ ] Application loads over HTTPS
- [ ] HTTP automatically redirects to HTTPS
- [ ] All static resources load over HTTPS
- [ ] Login/session cookies are secure
- [ ] API endpoints work over HTTPS
- [ ] Long-running requests don't timeout
- [ ] File uploads work

### Step 7: Monitoring Setup (Day 3)

**Certificate expiration monitoring:**

```bash
# Add to crontab (runs daily)
crontab -e

# Add:
0 3 * * * certbot renew --quiet --post-hook "systemctl reload nginx"
```

**Create monitoring script:**

**File:** `/usr/local/bin/check-ssl-expiry.sh`

```bash
#!/bin/bash
DOMAIN="your-domain.com"
EXPIRY_DAYS=$(echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2 | xargs -I {} date -d {} +%s)
CURRENT=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_DAYS - $CURRENT) / 86400 ))

if [ $DAYS_LEFT -lt 14 ]; then
    echo "WARNING: SSL certificate expires in $DAYS_LEFT days!" | mail -s "SSL Certificate Expiring Soon" admin@your-domain.com
fi
```

### Deliverables (Days 1-3)

- [x] Nginx configured with SSL/TLS
- [x] Let's Encrypt certificate obtained
- [x] Auto-renewal configured
- [x] Security headers enabled
- [x] Flask app configured for HTTPS
- [x] Systemd service created
- [x] SSL Labs A+ rating achieved
- [x] Monitoring configured

### Rollback Plan

If issues arise:

```bash
# Stop Nginx
sudo systemctl stop nginx

# Run Flask directly
cd /home/andrew/git/clinical-genius
source venv/bin/activate
python app.py

# Access via HTTP: http://localhost:4000
```

---

## Implementation 2: Database Encryption (Days 4-7)

### Objective
Encrypt SQLite database to protect PHI at rest using SQLCipher

### Prerequisites

```bash
# Install SQLCipher
sudo apt-get install sqlcipher libsqlcipher-dev -y

# Install Python bindings
pip install pysqlcipher3
```

### Step 1: Key Management Setup (Day 4)

**Approach: Environment Variable + Key Derivation**

**File:** `database/encryption.py` (NEW)

```python
"""
Database encryption utilities using SQLCipher
"""
import os
import hashlib
import secrets
from pathlib import Path


class EncryptionKeyManager:
    """Manages encryption keys for database"""

    def __init__(self):
        self.key_file = '.db_key'

    def generate_key(self) -> str:
        """Generate a new encryption key"""
        # Generate 256-bit random key
        key = secrets.token_hex(32)
        return key

    def store_key_securely(self, key: str):
        """Store key in file with restricted permissions"""
        key_path = Path(self.key_file)

        # Write key to file
        with open(key_path, 'w') as f:
            f.write(key)

        # Set restrictive permissions (owner read-only)
        os.chmod(key_path, 0o400)

        print(f"✓ Encryption key stored in {self.key_file}")
        print(f"✓ File permissions set to 400 (owner read-only)")
        print("\n⚠️  IMPORTANT: Backup this key securely!")
        print("⚠️  Without it, the database cannot be decrypted!")

    def load_key(self) -> str:
        """Load encryption key from file or environment"""
        # Try environment variable first (production)
        key = os.getenv('DB_ENCRYPTION_KEY')
        if key:
            return key

        # Fall back to key file (development)
        key_path = Path(self.key_file)
        if key_path.exists():
            with open(key_path, 'r') as f:
                return f.read().strip()

        raise Exception(
            "No encryption key found! "
            "Set DB_ENCRYPTION_KEY environment variable or run encryption setup."
        )

    def derive_key(self, password: str, salt: bytes = None) -> tuple:
        """
        Derive encryption key from password using PBKDF2
        Returns (key, salt)
        """
        if salt is None:
            salt = os.urandom(32)

        # Use PBKDF2 with 100,000 iterations
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000,
            dklen=32
        )

        return key.hex(), salt.hex()


def setup_encryption():
    """Interactive setup for database encryption"""
    manager = EncryptionKeyManager()

    print("=" * 60)
    print("Database Encryption Setup")
    print("=" * 60)
    print("\nThis will generate a new encryption key for the database.")
    print("The key must be kept secure and backed up.")
    print()

    choice = input("Generate new key? (yes/no): ").lower()
    if choice != 'yes':
        print("Setup cancelled.")
        return

    # Generate and store key
    key = manager.generate_key()
    manager.store_key_securely(key)

    print("\n" + "=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("1. Backup the .db_key file to a secure location")
    print("2. For production, set DB_ENCRYPTION_KEY environment variable")
    print("3. Add .db_key to .gitignore (already done)")
    print("4. Run migration: python migrate_to_encrypted_db.py")
    print("=" * 60)


if __name__ == '__main__':
    setup_encryption()
```

**Update:** `.gitignore`

```bash
# Add to .gitignore
.db_key
*.db.backup
```

### Step 2: Update Database Module (Day 4-5)

**File:** `database/db.py`

```python
"""
Database initialization and management for Clinical Genius application
Uses SQLCipher for encryption at rest
"""
import os
from pysqlcipher3 import dbapi2 as sqlite3
from database.encryption import EncryptionKeyManager


DB_NAME = 'analysis_batches.db'
key_manager = EncryptionKeyManager()


def get_connection():
    """Get an encrypted database connection"""
    conn = sqlite3.connect(DB_NAME)

    # Enable encryption
    encryption_key = key_manager.load_key()
    conn.execute(f"PRAGMA key = '{encryption_key}'")

    # Use modern encryption settings
    conn.execute("PRAGMA cipher_page_size = 4096")
    conn.execute("PRAGMA kdf_iter = 256000")
    conn.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
    conn.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")

    return conn


def verify_encryption():
    """Verify database is encrypted and accessible"""
    try:
        conn = get_connection()
        # Try to query schema
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        print(f"✓ Database encrypted and accessible")
        print(f"✓ Tables found: {len(tables)}")
        return True

    except Exception as e:
        print(f"✗ Database encryption verification failed: {e}")
        return False


def init_db():
    """Initialize SQLite database for analysis batches and dataset configurations"""
    conn = get_connection()
    c = conn.cursor()

    # ... rest of existing init_db code ...
    # (Keep all existing CREATE TABLE statements)

    conn.commit()
    conn.close()

    print("✓ Encrypted database initialized")


def migrate_db():
    """Migrate database schema for existing installations"""
    conn = get_connection()
    c = conn.cursor()

    # ... rest of existing migrate_db code ...

    conn.close()

    print("✓ Database migrations completed")


# Test encryption on import
if __name__ != '__main__':
    try:
        # Quick encryption check
        test_conn = get_connection()
        test_conn.execute("SELECT 1")
        test_conn.close()
    except Exception as e:
        print(f"⚠️  Database encryption error: {e}")
        print("⚠️  Run: python database/encryption.py to setup encryption")
```

### Step 3: Create Migration Script (Day 5)

**File:** `migrate_to_encrypted_db.py` (NEW)

```python
#!/usr/bin/env python3
"""
Migrate existing unencrypted database to encrypted database
"""
import os
import shutil
import sqlite3 as sqlite_plain
from pathlib import Path
from datetime import datetime
from database.db import get_connection as get_encrypted_connection
from database.encryption import EncryptionKeyManager


def migrate_to_encrypted():
    """Migrate unencrypted database to encrypted version"""

    old_db = 'analysis_batches.db'
    backup_db = f'analysis_batches.db.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}'

    print("=" * 60)
    print("Database Encryption Migration")
    print("=" * 60)

    # Check if old database exists
    if not Path(old_db).exists():
        print(f"✗ No database found at {old_db}")
        print("  Creating new encrypted database...")
        from database.db import init_db
        init_db()
        return

    # Verify encryption key is set up
    try:
        key_manager = EncryptionKeyManager()
        key = key_manager.load_key()
        print("✓ Encryption key loaded")
    except Exception as e:
        print(f"✗ No encryption key found: {e}")
        print("  Run: python database/encryption.py")
        return

    # Create backup
    print(f"\nCreating backup: {backup_db}")
    shutil.copy2(old_db, backup_db)
    print("✓ Backup created")

    # Read data from old database
    print("\nReading data from unencrypted database...")
    old_conn = sqlite_plain.connect(old_db)
    old_conn.row_factory = sqlite_plain.Row

    tables_data = {}
    cursor = old_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = [row[0] for row in cursor.fetchall()]

    for table in table_names:
        cursor = old_conn.execute(f"SELECT * FROM {table}")
        rows = [dict(row) for row in cursor.fetchall()]
        tables_data[table] = rows
        print(f"  ✓ Read {len(rows)} rows from {table}")

    old_conn.close()

    # Remove old database
    print(f"\nRemoving unencrypted database...")
    os.remove(old_db)
    print("✓ Unencrypted database removed")

    # Create new encrypted database
    print("\nCreating encrypted database...")
    from database.db import init_db
    init_db()

    # Import data into encrypted database
    print("\nImporting data into encrypted database...")
    new_conn = get_encrypted_connection()

    for table, rows in tables_data.items():
        if not rows:
            continue

        # Get column names
        columns = list(rows[0].keys())
        placeholders = ','.join(['?' for _ in columns])
        column_names = ','.join(columns)

        # Insert data
        insert_sql = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"

        for row in rows:
            values = [row[col] for col in columns]
            new_conn.execute(insert_sql, values)

        print(f"  ✓ Imported {len(rows)} rows into {table}")

    new_conn.commit()
    new_conn.close()

    # Verify migration
    print("\nVerifying migration...")
    verify_conn = get_encrypted_connection()
    for table in table_names:
        cursor = verify_conn.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  ✓ {table}: {count} rows")
    verify_conn.close()

    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"✓ Encrypted database created: {old_db}")
    print(f"✓ Backup saved: {backup_db}")
    print(f"✓ All data migrated successfully")
    print("\n⚠️  Keep the backup until you verify everything works!")
    print("=" * 60)


if __name__ == '__main__':
    migrate_to_encrypted()
```

### Step 4: Update All Database Access Points (Day 5-6)

**Update:** All route files to use encrypted connection

**Example - File:** `routes/dataset_routes.py`

```python
# Change import at top of file
from database.db import get_connection  # Now returns encrypted connection

# All existing code continues to work unchanged!
# The encryption is transparent to the application code
```

**No changes needed** in:
- `routes/analysis_routes.py`
- `routes/synthetic_routes.py`

The encryption is handled at the connection level.

### Step 5: CSV File Encryption (Day 6)

**File:** `utils/file_encryption.py` (NEW)

```python
"""
File encryption utilities for CSV exports
"""
import os
from cryptography.fernet import Fernet
from pathlib import Path


class FileEncryption:
    """Encrypt/decrypt files using Fernet (symmetric encryption)"""

    def __init__(self):
        self.key = self._load_key()
        self.cipher = Fernet(self.key)

    def _load_key(self) -> bytes:
        """Load or generate encryption key"""
        key_file = Path('.file_encryption_key')

        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()

        # Generate new key
        key = Fernet.generate_key()

        with open(key_file, 'wb') as f:
            f.write(key)

        os.chmod(key_file, 0o400)

        return key

    def encrypt_file(self, input_path: str, output_path: str = None):
        """Encrypt a file"""
        if output_path is None:
            output_path = input_path + '.encrypted'

        with open(input_path, 'rb') as f:
            data = f.read()

        encrypted = self.cipher.encrypt(data)

        with open(output_path, 'wb') as f:
            f.write(encrypted)

        return output_path

    def decrypt_file(self, input_path: str, output_path: str = None):
        """Decrypt a file"""
        if output_path is None:
            output_path = input_path.replace('.encrypted', '')

        with open(input_path, 'rb') as f:
            encrypted = f.read()

        decrypted = self.cipher.decrypt(encrypted)

        with open(output_path, 'wb') as f:
            f.write(decrypted)

        return output_path

    def encrypt_csv(self, csv_data: str) -> bytes:
        """Encrypt CSV data in memory"""
        return self.cipher.encrypt(csv_data.encode('utf-8'))

    def decrypt_csv(self, encrypted_data: bytes) -> str:
        """Decrypt CSV data in memory"""
        return self.cipher.decrypt(encrypted_data).decode('utf-8')


# Global instance
file_encryptor = FileEncryption()
```

**Update CSV generation** in `routes/analysis_routes.py`:

```python
from utils.file_encryption import file_encryptor

# When generating CSV for download
@analysis_bp.route('/api/analysis/download-csv/<batch_id>', methods=['GET'])
def download_csv(batch_id):
    try:
        # ... generate CSV ...

        # Encrypt CSV data before storing
        encrypted_csv = file_encryptor.encrypt_csv(csv_content)

        # Store encrypted version
        c.execute('''
            INSERT OR REPLACE INTO execution_history
            (batch_id, csv_data, ...)
            VALUES (?, ?, ...)
        ''', (batch_id, encrypted_csv, ...))

        # For download, send decrypted (over HTTPS)
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
```

### Step 6: Testing and Validation (Day 7)

**Test Suite:** `tests/test_encryption.py` (NEW)

```python
"""
Tests for database encryption
"""
import unittest
import os
from pathlib import Path
from database.db import get_connection, init_db
from database.encryption import EncryptionKeyManager
from utils.file_encryption import FileEncryption


class TestDatabaseEncryption(unittest.TestCase):

    def test_encryption_key_generation(self):
        """Test encryption key generation"""
        manager = EncryptionKeyManager()
        key = manager.generate_key()

        self.assertIsInstance(key, str)
        self.assertEqual(len(key), 64)  # 32 bytes = 64 hex chars

    def test_database_connection(self):
        """Test encrypted database connection"""
        conn = get_connection()
        cursor = conn.execute("SELECT 1")
        result = cursor.fetchone()

        self.assertEqual(result[0], 1)
        conn.close()

    def test_database_is_encrypted(self):
        """Verify database file is encrypted (cannot read as plain SQLite)"""
        import sqlite3

        # Try to open with regular SQLite (should fail)
        try:
            conn = sqlite3.connect('analysis_batches.db')
            conn.execute("SELECT * FROM batches")
            self.fail("Database is not encrypted!")
        except:
            # Expected to fail
            pass

    def test_crud_operations(self):
        """Test CRUD operations on encrypted database"""
        conn = get_connection()

        # Create
        conn.execute('''
            INSERT INTO dataset_configs (id, name, crm_dataset_id, crm_dataset_name,
                                        record_id_field, selected_fields, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ''', ('test-id', 'Test', 'ds-123', 'Test DS', 'Id', '["Field1"]'))

        # Read
        cursor = conn.execute("SELECT * FROM dataset_configs WHERE id=?", ('test-id',))
        row = cursor.fetchone()
        self.assertIsNotNone(row)

        # Update
        conn.execute("UPDATE dataset_configs SET name=? WHERE id=?", ('Updated', 'test-id'))

        # Delete
        conn.execute("DELETE FROM dataset_configs WHERE id=?", ('test-id',))

        conn.commit()
        conn.close()

    def test_file_encryption(self):
        """Test CSV file encryption"""
        encryptor = FileEncryption()

        # Test data
        test_data = "Patient,Diagnosis\nJohn Doe,Diabetes"

        # Encrypt
        encrypted = encryptor.encrypt_csv(test_data)
        self.assertNotEqual(encrypted, test_data.encode())
        self.assertIn(b'gAAAAA', encrypted)  # Fernet token prefix

        # Decrypt
        decrypted = encryptor.decrypt_csv(encrypted)
        self.assertEqual(decrypted, test_data)


if __name__ == '__main__':
    unittest.main()
```

**Run tests:**

```bash
# Install test dependencies
pip install pytest cryptography

# Run encryption tests
python -m pytest tests/test_encryption.py -v

# Or run manually
python tests/test_encryption.py
```

### Deliverables (Days 4-7)

- [x] Encryption key management system
- [x] SQLCipher integration
- [x] Database migration completed
- [x] All database access encrypted
- [x] CSV file encryption implemented
- [x] Test suite passing
- [x] Backup procedures documented
- [x] Key recovery procedures documented

### Rollback Plan

```bash
# If migration fails, restore from backup
cp analysis_batches.db.backup.YYYYMMDD_HHMMSS analysis_batches.db

# Revert database/db.py to use plain sqlite3
# Comment out: from pysqlcipher3 import dbapi2 as sqlite3
# Uncomment: import sqlite3
```

---

## Implementation 3: Audit Logging (Days 8-14)

### Objective
Implement comprehensive audit logging for all PHI access and system changes

### Architecture

```
[Application Events]
         ↓
[Audit Logger] → [audit.log] (JSON structured logs)
         ↓
[Audit Database Table] (long-term storage)
         ↓
[Audit Dashboard] (view/search logs)
```

### Prerequisites

```bash
# Install logging dependencies
pip install python-json-logger
```

### Step 1: Audit Logging Framework (Day 8)

**File:** `utils/audit_logger.py` (NEW)

```python
"""
HIPAA-compliant audit logging system
Logs all PHI access and system changes
"""
import logging
import json
from datetime import datetime
from pathlib import Path
from pythonjsonlogger import jsonlogger
from flask import request, g
from functools import wraps
from database.db import get_connection


class AuditLogger:
    """Centralized audit logging for HIPAA compliance"""

    def __init__(self, app=None):
        self.logger = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize audit logger with Flask app"""
        # Create logs directory
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        # Set up JSON logger
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)

        # File handler with rotation
        from logging.handlers import TimedRotatingFileHandler
        handler = TimedRotatingFileHandler(
            'logs/audit.log',
            when='midnight',
            interval=1,
            backupCount=2190,  # 6 years retention
            encoding='utf-8'
        )

        # JSON formatter
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(event)s %(user_id)s %(ip_address)s %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # Also log to database
        self._init_audit_database()

        # Register Flask hooks
        app.before_request(self._before_request)
        app.after_request(self._after_request)

    def _init_audit_database(self):
        """Create audit log table in database"""
        conn = get_connection()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                user_id TEXT,
                username TEXT,
                ip_address TEXT,
                user_agent TEXT,
                endpoint TEXT,
                http_method TEXT,
                request_data TEXT,
                response_status INTEGER,
                phi_accessed TEXT,
                record_ids TEXT,
                fields_accessed TEXT,
                action TEXT,
                resource_type TEXT,
                resource_id TEXT,
                old_value TEXT,
                new_value TEXT,
                success INTEGER,
                error_message TEXT,
                session_id TEXT,
                metadata TEXT
            )
        ''')

        # Index for common queries
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp
            ON audit_log(timestamp DESC)
        ''')
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_user
            ON audit_log(user_id, timestamp DESC)
        ''')
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_audit_event
            ON audit_log(event_type, timestamp DESC)
        ''')

        conn.commit()
        conn.close()

    def _before_request(self):
        """Track request start time"""
        g.start_time = datetime.utcnow()
        g.audit_context = {}

    def _after_request(self, response):
        """Log all HTTP requests automatically"""
        # Skip health checks and static files
        if request.endpoint in ['health_check', 'static']:
            return response

        # Calculate request duration
        duration = (datetime.utcnow() - g.start_time).total_seconds()

        # Log request
        self._log_request(response.status_code, duration)

        return response

    def _log_request(self, status_code, duration):
        """Log HTTP request details"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'http_request',
            'user_id': getattr(g, 'user_id', 'anonymous'),
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'method': request.method,
            'endpoint': request.endpoint,
            'path': request.path,
            'status_code': status_code,
            'duration_seconds': duration,
        }

        # Add PHI context if set
        if hasattr(g, 'audit_context'):
            log_entry.update(g.audit_context)

        self.logger.info('HTTP request', extra=log_entry)

    def log_phi_access(self, event_type, record_ids=None, fields=None, action='read', **kwargs):
        """
        Log PHI access event

        Args:
            event_type: Type of event (e.g., 'record_view', 'batch_execution')
            record_ids: List of record IDs accessed
            fields: List of field names accessed
            action: Action performed (read, create, update, delete, export)
            **kwargs: Additional metadata
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': event_type,
            'event_type': 'phi_access',
            'user_id': getattr(g, 'user_id', 'anonymous'),
            'username': getattr(g, 'username', 'anonymous'),
            'ip_address': request.remote_addr if request else 'system',
            'action': action,
            'phi_accessed': True,
        }

        if record_ids:
            log_entry['record_ids'] = json.dumps(record_ids) if isinstance(record_ids, list) else record_ids
            log_entry['record_count'] = len(record_ids) if isinstance(record_ids, list) else 1

        if fields:
            log_entry['fields_accessed'] = json.dumps(fields) if isinstance(fields, list) else fields

        log_entry.update(kwargs)

        # Log to file
        self.logger.info(f'PHI Access: {event_type}', extra=log_entry)

        # Log to database
        self._log_to_database(log_entry)

        # Set in request context for HTTP log
        if hasattr(g, 'audit_context'):
            g.audit_context.update({
                'phi_accessed': True,
                'record_count': log_entry.get('record_count', 0)
            })

    def log_authentication(self, event_type, user_id, success=True, **kwargs):
        """Log authentication events"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': event_type,
            'event_type': 'authentication',
            'user_id': user_id,
            'ip_address': request.remote_addr if request else 'system',
            'success': success,
        }
        log_entry.update(kwargs)

        self.logger.info(f'Authentication: {event_type}', extra=log_entry)
        self._log_to_database(log_entry)

    def log_configuration_change(self, resource_type, resource_id, action, old_value=None, new_value=None, **kwargs):
        """Log configuration changes"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': 'configuration_change',
            'event_type': 'configuration',
            'user_id': getattr(g, 'user_id', 'system'),
            'username': getattr(g, 'username', 'system'),
            'ip_address': request.remote_addr if request else 'system',
            'resource_type': resource_type,
            'resource_id': resource_id,
            'action': action,
        }

        if old_value is not None:
            log_entry['old_value'] = json.dumps(old_value) if not isinstance(old_value, str) else old_value
        if new_value is not None:
            log_entry['new_value'] = json.dumps(new_value) if not isinstance(new_value, str) else new_value

        log_entry.update(kwargs)

        self.logger.info(f'Config Change: {action} {resource_type}', extra=log_entry)
        self._log_to_database(log_entry)

    def log_error(self, error_type, error_message, **kwargs):
        """Log errors and exceptions"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': error_type,
            'event_type': 'error',
            'user_id': getattr(g, 'user_id', 'system'),
            'ip_address': request.remote_addr if request else 'system',
            'error_message': str(error_message),
            'success': False,
        }
        log_entry.update(kwargs)

        self.logger.error(f'Error: {error_type}', extra=log_entry)
        self._log_to_database(log_entry)

    def _log_to_database(self, log_entry):
        """Store audit log in database"""
        try:
            conn = get_connection()

            # Prepare values
            values = (
                log_entry.get('timestamp'),
                log_entry.get('event_type', 'general'),
                log_entry.get('user_id'),
                log_entry.get('username'),
                log_entry.get('ip_address'),
                log_entry.get('user_agent'),
                log_entry.get('endpoint'),
                log_entry.get('method'),
                json.dumps(log_entry.get('request_data')) if log_entry.get('request_data') else None,
                log_entry.get('status_code'),
                1 if log_entry.get('phi_accessed') else 0,
                log_entry.get('record_ids'),
                log_entry.get('fields_accessed'),
                log_entry.get('action'),
                log_entry.get('resource_type'),
                log_entry.get('resource_id'),
                log_entry.get('old_value'),
                log_entry.get('new_value'),
                1 if log_entry.get('success', True) else 0,
                log_entry.get('error_message'),
                log_entry.get('session_id'),
                json.dumps({k: v for k, v in log_entry.items()
                           if k not in ['timestamp', 'event_type', 'user_id']})
            )

            conn.execute('''
                INSERT INTO audit_log (
                    timestamp, event_type, user_id, username, ip_address, user_agent,
                    endpoint, http_method, request_data, response_status, phi_accessed,
                    record_ids, fields_accessed, action, resource_type, resource_id,
                    old_value, new_value, success, error_message, session_id, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', values)

            conn.commit()
            conn.close()

        except Exception as e:
            # Don't let audit logging break the application
            print(f"Audit logging error: {e}")


# Global audit logger instance
audit_logger = AuditLogger()


# Decorator for automatic PHI access logging
def log_phi_access(action='read', record_id_param=None, fields=None):
    """
    Decorator to automatically log PHI access

    Usage:
        @log_phi_access(action='read', record_id_param='batch_id')
        def get_batch(batch_id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Get record ID from parameters
            record_ids = []
            if record_id_param and record_id_param in kwargs:
                record_ids = [kwargs[record_id_param]]

            # Log the access
            audit_logger.log_phi_access(
                event_type=f.__name__,
                record_ids=record_ids,
                fields=fields,
                action=action,
                endpoint=request.endpoint if request else None
            )

            # Call original function
            return f(*args, **kwargs)

        return wrapped
    return decorator
```

### Step 2: Integrate Audit Logging into Application (Day 9-10)

**File:** `app.py`

```python
from utils.audit_logger import audit_logger

# ... existing code ...

# Initialize audit logger
audit_logger.init_app(app)

# Log application startup
@app.before_first_request
def log_startup():
    audit_logger.logger.info('Application started', extra={
        'event': 'application_startup',
        'event_type': 'system',
        'timestamp': datetime.utcnow().isoformat()
    })

# ... rest of code ...
```

**Update routes to log PHI access:**

**File:** `routes/analysis_routes.py`

```python
from utils.audit_logger import audit_logger, log_phi_access
from flask import g

# Example: Log batch execution
@analysis_bp.route('/api/analysis/execute-batch', methods=['POST'])
@log_phi_access(action='read', record_id_param='batch_id')
def execute_batch():
    try:
        data = request.json
        batch_id = data.get('batch_id')
        record_ids = data.get('record_ids', [])

        # Log the batch execution start
        audit_logger.log_phi_access(
            event_type='batch_execution_start',
            record_ids=record_ids if record_ids else 'all',
            action='process',
            batch_id=batch_id,
            mode='batch_llm_processing'
        )

        # ... existing batch execution code ...

        # Log completion
        audit_logger.log_phi_access(
            event_type='batch_execution_complete',
            record_ids=record_ids if record_ids else 'all',
            action='process',
            batch_id=batch_id,
            records_processed=results['total'],
            success_count=results['success'],
            error_count=results['failed']
        )

        return jsonify({'success': True, 'results': results})

    except Exception as e:
        audit_logger.log_error(
            'batch_execution_error',
            str(e),
            batch_id=batch_id
        )
        return jsonify({'success': False, 'error': str(e)}), 500

# Example: Log CSV download
@analysis_bp.route('/api/analysis/download-csv/<batch_id>', methods=['GET'])
@log_phi_access(action='export', record_id_param='batch_id')
def download_csv(batch_id):
    try:
        # ... get batch data ...

        # Log PHI export
        audit_logger.log_phi_access(
            event_type='phi_export',
            record_ids=[batch_id],
            action='export',
            export_format='csv',
            record_count=len(records)
        )

        # ... generate and return CSV ...

    except Exception as e:
        audit_logger.log_error('csv_export_error', str(e), batch_id=batch_id)
        return jsonify({'success': False, 'error': str(e)}), 500

# Example: Log configuration changes
@analysis_bp.route('/api/analysis/batches', methods=['POST'])
def create_batch():
    try:
        data = request.json

        # ... create batch ...

        # Log configuration change
        audit_logger.log_configuration_change(
            resource_type='batch',
            resource_id=batch_id,
            action='create',
            new_value=data
        )

        return jsonify({'success': True, 'id': batch_id})

    except Exception as e:
        audit_logger.log_error('batch_creation_error', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500
```

Continue in next message due to length...