#!/usr/bin/env python3
"""
Generate self-signed SSL certificate for localhost HTTPS
For HIPAA compliance - encrypts traffic even on localhost
"""

import os
import sys
from datetime import datetime, timedelta

def generate_certificate():
    """Generate self-signed certificate using cryptography library"""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
    except ImportError:
        print("Error: cryptography library not installed")
        print("Install with: pip install cryptography")
        sys.exit(1)

    print("Generating SSL certificate for localhost...")
    print("=" * 60)

    # Create directory for SSL files
    ssl_dir = 'ssl'
    os.makedirs(ssl_dir, exist_ok=True)

    # Generate private key
    print("\n1. Generating RSA private key (4096 bits)...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
        backend=default_backend()
    )

    # Create certificate subject
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Local"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Localhost"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Clinical Genius"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Development"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    # Create certificate
    print("2. Creating self-signed certificate...")

    # Import ipaddress for proper IP handling
    import ipaddress

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        # Valid for 10 years
        datetime.utcnow() + timedelta(days=3650)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True,
    ).add_extension(
        x509.KeyUsage(
            digital_signature=True,
            key_encipherment=True,
            content_commitment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False,
        ),
        critical=True,
    ).add_extension(
        x509.ExtendedKeyUsage([
            x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256(), default_backend())

    # Write private key
    key_path = os.path.join(ssl_dir, 'localhost.key')
    print(f"3. Writing private key to {key_path}...")
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Write certificate
    cert_path = os.path.join(ssl_dir, 'localhost.crt')
    print(f"4. Writing certificate to {cert_path}...")
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    # Set restrictive permissions on Windows (best effort)
    print("\n5. Setting file permissions...")
    try:
        # On Windows, this is less critical but we try anyway
        import stat
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
        print(f"   - {key_path}: Read/Write for owner only")
    except Exception as e:
        print(f"   - Warning: Could not set permissions: {e}")
        print("   - Please manually restrict access to SSL files")

    print("\n" + "=" * 60)
    print("✅ SSL Certificate generated successfully!")
    print("=" * 60)
    print(f"\nCertificate: {cert_path}")
    print(f"Private Key: {key_path}")
    print(f"Valid for:   10 years (until {(datetime.utcnow() + timedelta(days=3650)).strftime('%Y-%m-%d')})")
    print(f"\nCommon Name: localhost")
    print(f"Alt Names:   localhost, 127.0.0.1")
    print("\nNote: This is a self-signed certificate for development/localhost use.")
    print("Your browser will show a security warning - this is expected.")
    print("Click 'Advanced' and 'Proceed to localhost' to continue.")
    print("\n" + "=" * 60)

    return True


def check_existing_certificates():
    """Check if certificates already exist"""
    ssl_dir = 'ssl'
    key_path = os.path.join(ssl_dir, 'localhost.key')
    cert_path = os.path.join(ssl_dir, 'localhost.crt')

    if os.path.exists(key_path) and os.path.exists(cert_path):
        print("⚠️  SSL certificates already exist!")
        print(f"   - {cert_path}")
        print(f"   - {key_path}")
        response = input("\nOverwrite existing certificates? (yes/no): ")
        return response.lower() in ['yes', 'y']

    return True


if __name__ == '__main__':
    print("Clinical Genius - SSL Certificate Generator")
    print("=" * 60)
    print("This script generates a self-signed SSL certificate for HTTPS")
    print("=" * 60)

    if check_existing_certificates():
        if generate_certificate():
            print("\n✅ Setup complete!")
            print("\nNext steps:")
            print("1. Restart your application with: python app.py")
            print("2. Access via HTTPS: https://localhost:4000")
            print("3. Accept the browser security warning (self-signed cert)")
        else:
            print("\n❌ Certificate generation failed!")
            sys.exit(1)
    else:
        print("\n❌ Certificate generation cancelled.")
        sys.exit(0)
