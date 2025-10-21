#!/usr/bin/env python3

"""
Salesforce JWT Authentication Script
Decrypts JWT key and authenticates to Salesforce using sf CLI
"""

import os
import sys
import subprocess
import json
import time
import tempfile
import hashlib
import platform
from pathlib import Path
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Detect if running on Windows
IS_WINDOWS = platform.system() == 'Windows'

# In-memory token cache
_token_cache = {
    'access_token': None,
    'instance_url': None,
    'expiry': None
}


def run_sf_command(cmd_args, **kwargs):
    """
    Run Salesforce CLI command with platform-specific handling

    Args:
        cmd_args: List of command arguments (e.g., ['sf', 'org', 'display'])
        **kwargs: Additional arguments to pass to subprocess.run

    Returns:
        subprocess.CompletedProcess
    """
    if IS_WINDOWS:
        # On Windows, use shell=True to find sf.cmd
        cmd_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd_args)
        return subprocess.run(cmd_str, shell=True, **kwargs)
    else:
        # On Unix-like systems, use the command list directly
        return subprocess.run(cmd_args, **kwargs)


def decrypt_jwt_key(encrypted_key_path: str, password: str) -> str:
    """
    Decrypts the encrypted JWT key file using AES-256-CBC with PBKDF2
    Compatible with OpenSSL encryption format
    """
    try:
        with open(encrypted_key_path, 'rb') as f:
            encrypted_data = f.read()

        # OpenSSL format: "Salted__" + 8-byte salt + encrypted data
        if encrypted_data[:8] != b'Salted__':
            raise Exception('Invalid OpenSSL encrypted file format')

        salt = encrypted_data[8:16]
        encrypted = encrypted_data[16:]

        # Derive key and IV using PBKDF2 (OpenSSL uses 10000 iterations by default)
        password_bytes = password.encode('utf-8')
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=48,  # 32 bytes for key + 16 bytes for IV
            salt=salt,
            iterations=10000,
            backend=default_backend()
        )
        key_and_iv = kdf.derive(password_bytes)
        key = key_and_iv[:32]
        iv = key_and_iv[32:48]

        # Decrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(encrypted) + decryptor.finalize()

        # Remove PKCS7 padding
        padding_len = decrypted[-1]
        decrypted = decrypted[:-padding_len]

        return decrypted.decode('utf-8')

    except Exception as e:
        raise Exception(f'Failed to decrypt JWT key: {str(e)}')


def is_token_accepted(token: str, instance_url: str) -> bool:
    """Check if a token is valid by making a test API call"""
    try:
        import requests
        response = requests.get(
            f"{instance_url}/services/data/v60.0",
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        return response.status_code == 200
    except:
        return False


def authorize() -> dict:
    """
    Performs JWT-based Salesforce login and returns access token and instance URL
    """
    alias = "myJwtOrg"
    client_id = os.environ.get('SFDC_CLIENT_ID')
    script_dir = Path(__file__).parent.absolute()
    # JWT key is in parent directory
    encrypted_key_file = script_dir.parent / 'jwt.key.enc'
    key_pass = os.environ.get('KEY_PASS')
    username = os.environ.get('SFDC_USERNAME')
    login_url = os.environ.get('SFDC_LOGIN_URL', 'https://login.salesforce.com')
    instance_url = os.environ.get('SF_INSTANCE_URL', login_url)

    # Validate required environment variables
    if not key_pass:
        raise Exception("KEY_PASS environment variable is required to decrypt JWT key")
    if not client_id:
        raise Exception("SFDC_CLIENT_ID environment variable is required")
    if not username:
        raise Exception("SFDC_USERNAME environment variable is required")

    try:
        # -1) Allow token to be provided via environment to support offline usage
        if os.environ.get('SF_ACCESS_TOKEN'):
            env_token = os.environ['SF_ACCESS_TOKEN']
            if is_token_accepted(env_token, instance_url):
                print("✔ Using SF_ACCESS_TOKEN from environment")
                _token_cache['access_token'] = env_token
                _token_cache['instance_url'] = os.environ.get('SF_INSTANCE_URL', login_url)
                _token_cache['expiry'] = time.time() + (2 * 60 * 60)  # 2 hours
                return {
                    'accessToken': env_token,
                    'instanceUrl': _token_cache['instance_url']
                }
            print("ℹ Provided SF_ACCESS_TOKEN was rejected; obtaining new token...")

        # 0) Reuse cached token when possible and not expired
        if _token_cache['access_token'] and _token_cache['expiry'] and _token_cache['expiry'] > time.time():
            if is_token_accepted(_token_cache['access_token'], instance_url):
                print("✔ Reusing cached access token")
                os.environ['SF_ACCESS_TOKEN'] = _token_cache['access_token']
                os.environ['SF_INSTANCE_URL'] = _token_cache['instance_url']
                return {
                    'accessToken': _token_cache['access_token'],
                    'instanceUrl': _token_cache['instance_url']
                }
            print("ℹ Cached access token rejected; obtaining new token...")
            _token_cache.update({'access_token': None, 'instance_url': None, 'expiry': None})
        elif _token_cache['access_token']:
            print("ℹ Cached token expired; obtaining new token...")
            _token_cache.update({'access_token': None, 'instance_url': None, 'expiry': None})

        # 1) Decrypt the JWT key
        decrypted_key = decrypt_jwt_key(str(encrypted_key_file), key_pass)

        # 2) Create a temporary file with restricted permissions
        with tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False) as temp_file:
            temp_key_file = temp_file.name
            temp_file.write(decrypted_key)

        try:
            # Set restrictive permissions (owner read-only)
            os.chmod(temp_key_file, 0o600)

            # 3) Log in via JWT using temporary key file
            cmd = [
                'sf', 'org', 'login', 'jwt',
                '-i', client_id,
                '--jwt-key-file', temp_key_file,
                '--username', username,
                '--alias', alias,
                '--instance-url', login_url,
                '--set-default'
            ]

            result = run_sf_command(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=30
            )

            if result.returncode != 0:
                raise Exception(f"sf org login jwt failed: {result.stderr}")

        finally:
            # Immediately clean up temporary key file
            if os.path.exists(temp_key_file):
                # Overwrite with random data before deletion for security
                with open(temp_key_file, 'wb') as f:
                    f.write(os.urandom(len(decrypted_key)))
                os.unlink(temp_key_file)

        # 4) Retrieve the org info as JSON
        result = run_sf_command(
            ['sf', 'org', 'display', '--target-org', alias, '--json'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=10
        )

        if result.returncode != 0:
            raise Exception(f"sf org display failed: {result.stderr}")

        info = json.loads(result.stdout).get('result', {})
        token = info.get('accessToken')

        if not token:
            raise Exception("No accessToken found in sf org display output")

        if info.get('instanceUrl'):
            os.environ['SF_INSTANCE_URL'] = info['instanceUrl']

        os.environ['SF_ACCESS_TOKEN'] = token

        # 5) Cache token in memory
        _token_cache['access_token'] = token
        _token_cache['instance_url'] = os.environ.get('SF_INSTANCE_URL', instance_url)
        _token_cache['expiry'] = time.time() + (2 * 60 * 60)  # 2 hours

        print(f"✔ Access token cached in memory")

        return {
            'accessToken': token,
            'instanceUrl': _token_cache['instance_url']
        }

    except Exception as e:
        print(f"❌ Error during JWT login or token retrieval: {str(e)}", file=sys.stderr)
        raise


if __name__ == '__main__':
    try:
        result = authorize()
        print(f"\nAuthentication successful!")
        print(f"Instance URL: {result['instanceUrl']}")
    except Exception as e:
        print(f"\nAuthentication failed: {str(e)}", file=sys.stderr)
        sys.exit(1)
