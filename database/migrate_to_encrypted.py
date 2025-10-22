#!/usr/bin/env python3
"""
Database Migration Script
Migrates existing SQLite database to SQLCipher encrypted database
"""

import sqlite3
import os
import shutil
from datetime import datetime
from database.encryption import get_encrypted_connection, verify_encryption, EncryptionKeyManager


def migrate_database(source_db='analysis_batches.db', backup=True):
    """
    Migrate unencrypted database to encrypted SQLCipher database

    Args:
        source_db: Path to source database
        backup: Whether to create backup of original database

    Returns:
        bool: True if migration successful
    """
    print("=" * 60)
    print("DATABASE ENCRYPTION MIGRATION")
    print("=" * 60)
    print()

    # Check if source database exists
    if not os.path.exists(source_db):
        print(f"[ERROR] Source database not found: {source_db}")
        return False

    # Check if already encrypted
    if verify_encryption(source_db):
        print(f"[INFO] Database is already encrypted: {source_db}")
        return True

    # Create backup
    if backup:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{source_db}.backup.{timestamp}"
        print(f"[BACKUP] Creating backup: {backup_path}")
        shutil.copy2(source_db, backup_path)
        print(f"[BACKUP] Backup created successfully")
        print()

    # Get table schemas and data from source database
    print("[MIGRATION] Reading source database...")
    source_conn = sqlite3.connect(source_db)
    source_cursor = source_conn.cursor()

    # Get all tables
    source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in source_cursor.fetchall()]

    print(f"[MIGRATION] Found {len(tables)} tables: {', '.join(tables)}")
    print()

    # Store schemas and data
    table_data = {}
    for table in tables:
        # Get table schema
        source_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
        schema = source_cursor.fetchone()[0]

        # Get table data
        source_cursor.execute(f"SELECT * FROM {table}")
        rows = source_cursor.fetchall()

        # Get column names
        source_cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in source_cursor.fetchall()]

        table_data[table] = {
            'schema': schema,
            'columns': columns,
            'rows': rows
        }

        print(f"[MIGRATION] Table '{table}': {len(rows)} rows")

    source_conn.close()
    print()

    # Create temporary encrypted database
    temp_db = f"{source_db}.encrypted.tmp"
    if os.path.exists(temp_db):
        os.remove(temp_db)

    print("[MIGRATION] Creating encrypted database...")

    # Initialize encryption key
    key_manager = EncryptionKeyManager()
    encryption_key = key_manager.get_or_create_db_key()
    print(f"[SECURITY] Using encryption key from: {key_manager.key_file}")
    print()

    # Create encrypted database
    encrypted_conn = get_encrypted_connection(temp_db)
    encrypted_cursor = encrypted_conn.cursor()

    # Create tables and insert data
    for table, data in table_data.items():
        print(f"[MIGRATION] Migrating table '{table}'...")

        # Create table
        encrypted_cursor.execute(data['schema'])

        # Insert data
        if data['rows']:
            placeholders = ','.join(['?'] * len(data['columns']))
            insert_sql = f"INSERT INTO {table} VALUES ({placeholders})"
            encrypted_cursor.executemany(insert_sql, data['rows'])

        print(f"[MIGRATION] Migrated {len(data['rows'])} rows")

    encrypted_conn.commit()
    encrypted_conn.close()
    print()

    # Verify encryption
    print("[VERIFICATION] Verifying database encryption...")
    if verify_encryption(temp_db):
        print("[VERIFICATION] ✓ Database is properly encrypted")
    else:
        print("[VERIFICATION] ✗ Database encryption verification failed")
        os.remove(temp_db)
        return False

    print()

    # Replace original database with encrypted version
    print("[MIGRATION] Replacing original database with encrypted version...")
    os.remove(source_db)
    os.rename(temp_db, source_db)

    print()
    print("=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print()
    print("[SUCCESS] Database has been encrypted successfully")
    print(f"[SUCCESS] Encrypted database: {source_db}")
    print(f"[SUCCESS] Encryption key: {key_manager.key_file}")
    print()
    print("[IMPORTANT] Keep the encryption key file secure!")
    print("[IMPORTANT] Without the key, the database cannot be accessed!")
    print()

    # Verify we can read the encrypted database
    print("[TEST] Testing encrypted database access...")
    try:
        test_conn = get_encrypted_connection(source_db)
        test_cursor = test_conn.cursor()
        test_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        test_tables = [row[0] for row in test_cursor.fetchall()]
        test_conn.close()
        print(f"[TEST] ✓ Successfully accessed encrypted database")
        print(f"[TEST] ✓ Found {len(test_tables)} tables: {', '.join(test_tables)}")
    except Exception as e:
        print(f"[TEST] ✗ Failed to access encrypted database: {e}")
        return False

    print()
    return True


if __name__ == '__main__':
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else 'analysis_batches.db'
    success = migrate_database(db_path)

    sys.exit(0 if success else 1)
