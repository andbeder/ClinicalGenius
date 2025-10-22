"""
Database Encryption Module
Handles encryption key management and encrypted database connections
"""

import os
import secrets
from pathlib import Path
from cryptography.fernet import Fernet


class EncryptionKeyManager:
    """Manages encryption keys for database and file encryption"""

    def __init__(self, key_file_path='.encryption_key'):
        """
        Initialize key manager

        Args:
            key_file_path: Path to store encryption key (relative to project root)
        """
        self.key_file = Path(key_file_path)
        self._db_key = None
        self._fernet = None

    def get_or_create_db_key(self):
        """
        Get existing database encryption key or create new one

        Returns:
            str: 32-byte hex key for SQLCipher
        """
        if self._db_key:
            return self._db_key

        if self.key_file.exists():
            # Load existing key
            with open(self.key_file, 'r') as f:
                self._db_key = f.read().strip()
        else:
            # Generate new 32-byte key for SQLCipher
            self._db_key = secrets.token_hex(32)

            # Save key to file with restricted permissions
            self.key_file.touch(mode=0o600)
            with open(self.key_file, 'w') as f:
                f.write(self._db_key)

            print(f"[SECURITY] Generated new database encryption key: {self.key_file}")
            print(f"[SECURITY] Key file permissions: 0600 (owner read/write only)")

        return self._db_key

    def get_fernet(self):
        """
        Get Fernet cipher for file encryption

        Returns:
            Fernet: Cipher for encrypting files
        """
        if self._fernet:
            return self._fernet

        # Use database key to derive Fernet key
        db_key = self.get_or_create_db_key()

        # Fernet requires base64-encoded 32-byte key
        # Derive from database key using first 32 bytes
        fernet_key = Fernet.generate_key()

        # Store derived key in key file (append to db key)
        if not self.key_file.exists():
            self.get_or_create_db_key()

        with open(self.key_file, 'r') as f:
            content = f.read().strip().split('\n')

        if len(content) == 1:
            # First time - add fernet key
            with open(self.key_file, 'a') as f:
                f.write(f'\n{fernet_key.decode()}')
            self._fernet = Fernet(fernet_key)
        else:
            # Load existing fernet key
            self._fernet = Fernet(content[1].encode())

        return self._fernet

    def encrypt_file(self, file_path):
        """
        Encrypt a file in place

        Args:
            file_path: Path to file to encrypt
        """
        fernet = self.get_fernet()

        with open(file_path, 'rb') as f:
            data = f.read()

        encrypted_data = fernet.encrypt(data)

        # Write encrypted data with .enc extension
        encrypted_path = f"{file_path}.enc"
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)

        return encrypted_path

    def decrypt_file(self, encrypted_file_path, output_path=None):
        """
        Decrypt an encrypted file

        Args:
            encrypted_file_path: Path to encrypted file
            output_path: Optional output path (defaults to removing .enc extension)
        """
        fernet = self.get_fernet()

        with open(encrypted_file_path, 'rb') as f:
            encrypted_data = f.read()

        decrypted_data = fernet.decrypt(encrypted_data)

        if not output_path:
            output_path = encrypted_file_path.replace('.enc', '')

        with open(output_path, 'wb') as f:
            f.write(decrypted_data)

        return output_path


def get_encrypted_connection(db_path='analysis_batches.db'):
    """
    Get SQLCipher encrypted database connection

    Args:
        db_path: Path to database file

    Returns:
        Connection: SQLCipher database connection
    """
    import pysqlcipher3.dbapi2 as sqlcipher

    # Get encryption key
    key_manager = EncryptionKeyManager()
    encryption_key = key_manager.get_or_create_db_key()

    # Connect to encrypted database
    conn = sqlcipher.connect(db_path)

    # Set encryption key using PRAGMA
    conn.execute(f"PRAGMA key = '{encryption_key}'")

    # Set cipher compatibility and settings for SQLCipher 4.x
    conn.execute("PRAGMA cipher_page_size = 4096")
    conn.execute("PRAGMA kdf_iter = 256000")
    conn.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
    conn.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")

    return conn


def verify_encryption(db_path='analysis_batches.db'):
    """
    Verify that database is encrypted

    Args:
        db_path: Path to database file

    Returns:
        bool: True if encrypted, False otherwise
    """
    import sqlite3

    try:
        # Try to open with standard sqlite3 (should fail for encrypted db)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        conn.close()

        # If we got here, database is NOT encrypted
        return False
    except sqlite3.DatabaseError:
        # Database is encrypted (cannot be opened with standard sqlite3)
        return True
