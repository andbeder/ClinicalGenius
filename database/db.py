"""
Database initialization and management for Clinical Genius application
"""
import sqlite3


DB_NAME = 'analysis_batches.db'


def get_connection():
    """Get a database connection"""
    return sqlite3.connect(DB_NAME)


def init_db():
    """Initialize SQLite database for analysis batches and dataset configurations"""
    conn = get_connection()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS dataset_configs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            crm_dataset_id TEXT NOT NULL,
            crm_dataset_name TEXT NOT NULL,
            record_id_field TEXT NOT NULL,
            saql_filter TEXT,
            selected_fields TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS batches (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            dataset_id TEXT NOT NULL,
            dataset_name TEXT NOT NULL,
            dataset_config_id TEXT,
            description TEXT,
            status TEXT DEFAULT 'pending',
            record_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS prompts (
            batch_id TEXT PRIMARY KEY,
            prompt_template TEXT NOT NULL,
            response_schema TEXT,
            schema_description TEXT,
            provider TEXT DEFAULT 'lm_studio',
            endpoint TEXT,
            temperature REAL DEFAULT 0.7,
            max_tokens INTEGER DEFAULT 4000,
            timeout INTEGER DEFAULT 60,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES batches(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS execution_history (
            batch_id TEXT PRIMARY KEY,
            batch_name TEXT NOT NULL,
            dataset_name TEXT NOT NULL,
            total_records INTEGER NOT NULL,
            success_count INTEGER NOT NULL,
            error_count INTEGER NOT NULL,
            execution_time REAL NOT NULL,
            csv_data TEXT NOT NULL,
            executed_at TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS execution_status (
            batch_id TEXT PRIMARY KEY,
            execution_id TEXT NOT NULL,
            status TEXT NOT NULL,
            current INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            started_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            complete INTEGER DEFAULT 0,
            success INTEGER DEFAULT 0,
            error TEXT,
            FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()


def migrate_db():
    """Migrate database schema for existing installations"""
    conn = get_connection()
    c = conn.cursor()

    # Check if dataset_config_id column exists
    c.execute("PRAGMA table_info(batches)")
    columns = [col[1] for col in c.fetchall()]

    if 'dataset_config_id' not in columns:
        print("Running migration: Adding dataset_config_id column to batches table")
        c.execute('ALTER TABLE batches ADD COLUMN dataset_config_id TEXT')
        conn.commit()

    conn.close()
