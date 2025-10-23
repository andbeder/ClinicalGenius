# HTTPS/TLS Setup Guide - Clinical Genius

**Last Updated:** October 22, 2025
**Status:** ✅ Implemented
**HIPAA Impact:** Encryption in Transit (§164.312(e))

---

## Overview

This guide explains the HTTPS/TLS implementation for Clinical Genius. While **not strictly required** for localhost-only deployments, HTTPS provides defense-in-depth security by encrypting all traffic, even on the local machine.

### Why HTTPS for Localhost?

1. **Defense-in-Depth:** Protects against local process sniffing
2. **Best Practice:** Trains secure habits
3. **HIPAA Alignment:** Demonstrates commitment to encryption
4. **Future-Proof:** Easy to deploy to network if needed
5. **Browser Features:** Some modern browser features require HTTPS

---

## Quick Start

### Step 1: Generate SSL Certificate

Run the certificate generator script:

```bash
python generate_ssl_cert.py
```

This creates:
- `ssl/localhost.crt` - Self-signed certificate
- `ssl/localhost.key` - Private key (4096-bit RSA)

**Output:**
```
Clinical Genius - SSL Certificate Generator
============================================================
Generating SSL certificate for localhost...
============================================================

1. Generating RSA private key (4096 bits)...
2. Creating self-signed certificate...
3. Writing private key to ssl\localhost.key...
4. Writing certificate to ssl\localhost.crt...

5. Setting file permissions...
   - ssl\localhost.key: Read/Write for owner only

============================================================
✅ SSL Certificate generated successfully!
============================================================

Certificate: ssl\localhost.crt
Private Key: ssl\localhost.key
Valid for:   10 years (until 2035-10-22)

Common Name: localhost
Alt Names:   localhost, 127.0.0.1

Note: This is a self-signed certificate for development/localhost use.
Your browser will show a security warning - this is expected.
Click 'Advanced' and 'Proceed to localhost' to continue.
```

### Step 2: Start Application with HTTPS

The application automatically detects the certificate and enables HTTPS:

```bash
python app.py
```

**Output:**
```
🔒 SSL/TLS Enabled - Using self-signed certificate
Starting Clinical Genius on localhost:4000
Access URL: https://localhost:4000
Access restricted to: localhost only (127.0.0.1)
Debug mode: False
```

### Step 3: Access via HTTPS

Open your browser to:
```
https://localhost:4000
```

**Expected Behavior:**
- Browser shows security warning (self-signed cert)
- Click "Advanced" → "Proceed to localhost (unsafe)"
- Application loads normally

---

## Configuration

### Environment Variables

Add to your `.env` file:

```env
# HTTPS Configuration
USE_HTTPS=true          # Set to 'false' to disable HTTPS
PORT=4000               # Port number (default: 4000)
```

### Disabling HTTPS

If you need to temporarily disable HTTPS:

1. **Option 1:** Set environment variable
   ```env
   USE_HTTPS=false
   ```

2. **Option 2:** Rename/remove certificate files
   ```bash
   mv ssl/localhost.crt ssl/localhost.crt.bak
   ```

Application will automatically fall back to HTTP.

---

## Certificate Details

### Technical Specifications

| Property | Value |
|----------|-------|
| **Type** | Self-signed X.509 |
| **Algorithm** | RSA 4096-bit |
| **Hash** | SHA-256 |
| **Validity** | 10 years from generation |
| **Common Name** | localhost |
| **Subject Alt Names** | localhost, 127.0.0.1 |
| **Key Usage** | Digital Signature, Key Encipherment |
| **Extended Key Usage** | TLS Web Server Authentication |

### Certificate Information

View certificate details:

```bash
# Windows (PowerShell)
certutil -dump ssl\localhost.crt

# Or with OpenSSL
openssl x509 -in ssl\localhost.crt -text -noout
```

### File Permissions

The generator script attempts to set restrictive permissions:
- `ssl/localhost.key` - Read/Write for owner only (0600)
- `ssl/localhost.crt` - Standard permissions (certificate is public)

**Windows Note:** File permissions work differently than Unix. Ensure your user account is the only one with access to the `ssl/` directory.

---

## Security Headers

The application automatically adds HIPAA-compliant security headers to all responses:

### Headers Implemented

| Header | Value | Purpose |
|--------|-------|---------|
| **Strict-Transport-Security** | max-age=31536000; includeSubDomains | Force HTTPS for 1 year |
| **X-Content-Type-Options** | nosniff | Prevent MIME type sniffing |
| **X-Frame-Options** | DENY | Prevent clickjacking |
| **X-XSS-Protection** | 1; mode=block | Enable XSS filtering |
| **Content-Security-Policy** | (see below) | Restrict resource loading |
| **Referrer-Policy** | strict-origin-when-cross-origin | Limit referrer information |
| **Permissions-Policy** | (see below) | Disable unnecessary features |

### Content Security Policy (CSP)

```
default-src 'self';
script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;
style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;
font-src 'self' https://cdn.jsdelivr.net;
img-src 'self' data:;
connect-src 'self';
frame-ancestors 'none';
base-uri 'self';
form-action 'self'
```

**What this does:**
- Only load resources from localhost and approved CDNs
- Prevent XSS attacks
- Block embedding in frames
- Restrict form submissions to same origin

### Permissions Policy

Disables unnecessary browser features:
- Geolocation
- Microphone
- Camera
- Payment APIs
- USB
- Motion sensors (magnetometer, gyroscope, accelerometer)

---

## Browser Warnings

### Why You See Warnings

Self-signed certificates are **not signed by a trusted Certificate Authority (CA)**. Browsers show warnings to protect users from man-in-the-middle attacks.

**For localhost use, this is expected and safe** because:
1. Traffic never leaves your machine
2. You generated the certificate yourself
3. No external CA validation needed for localhost

### How to Proceed

#### Chrome
1. Click "Advanced"
2. Click "Proceed to localhost (unsafe)"
3. (Optional) Type `thisisunsafe` to bypass

#### Firefox
1. Click "Advanced"
2. Click "Accept the Risk and Continue"

#### Edge
1. Click "Advanced"
2. Click "Continue to localhost (unsafe)"

### Trusting the Certificate (Optional)

To avoid repeated warnings, add the certificate to your trusted root store:

**Windows:**
1. Double-click `ssl\localhost.crt`
2. Click "Install Certificate"
3. Select "Current User"
4. Select "Place all certificates in the following store"
5. Browse → "Trusted Root Certification Authorities"
6. Click "OK" → "Next" → "Finish"

**Warning:** Only do this for certificates you generated yourself!

---

## TLS Configuration

### Supported Protocols

Flask's development server with `ssl_context` supports:
- TLS 1.2 (minimum)
- TLS 1.3 (if available in Python/OpenSSL version)

### Cipher Suites

Python's `ssl` module selects secure cipher suites automatically. To verify:

```python
import ssl
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
print(context.get_ciphers())
```

---

## Troubleshooting

### Certificate Not Found

**Error:**
```
⚠️  SSL certificate not found at ssl/localhost.crt
   Run: python generate_ssl_cert.py
   Starting without HTTPS...
```

**Solution:**
```bash
python generate_ssl_cert.py
```

### Permission Denied

**Error:**
```
PermissionError: [Errno 13] Permission denied: 'ssl/localhost.key'
```

**Solution:**
- Check file permissions
- Ensure you own the `ssl/` directory
- On Windows, run as your user (not Administrator)

### Browser Still Shows HTTP

**Check:**
1. Verify HTTPS is enabled in startup logs
2. Check you're accessing `https://` not `http://`
3. Clear browser cache
4. Try incognito/private mode

### Connection Refused

**Error:**
```
This site can't be reached
localhost refused to connect.
```

**Solution:**
1. Check application is running
2. Verify correct port (4000 by default)
3. Check firewall settings
4. Try `127.0.0.1` instead of `localhost`

---

## Production Considerations

### For Network Deployment

If you deploy to a network (not just localhost), you **MUST**:

1. **Get a Real Certificate**
   - Use Let's Encrypt (free, automated)
   - Or purchase from a CA (DigiCert, Sectigo, etc.)
   - Self-signed is NOT acceptable for network use

2. **Use a Production WSGI Server**
   ```bash
   pip install gunicorn
   gunicorn app:app --certfile=ssl/cert.pem --keyfile=ssl/key.pem --bind 0.0.0.0:443
   ```

3. **Or Use a Reverse Proxy (Nginx/Apache)**
   ```nginx
   server {
       listen 443 ssl;
       server_name yourdomain.com;
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
       ssl_protocols TLSv1.2 TLSv1.3;
       # ... other SSL settings
   }
   ```

4. **Update Access Controls**
   - Remove localhost-only restriction
   - Implement full authentication system
   - Add rate limiting and CSRF protection

### HIPAA Requirements for Network Deployment

- ✅ TLS 1.2 or higher
- ✅ Valid CA-signed certificate
- ✅ HSTS enabled
- ✅ Forward secrecy cipher suites
- ✅ Certificate pinning (recommended)
- ✅ Regular certificate renewal

---

## Testing HTTPS

### Manual Testing

1. **Check HTTPS is Active:**
   ```bash
   curl -k https://localhost:4000/health
   ```
   (The `-k` flag ignores self-signed cert warnings)

2. **Check Security Headers:**
   ```bash
   curl -k -I https://localhost:4000
   ```

   Should show headers like:
   ```
   Strict-Transport-Security: max-age=31536000; includeSubDomains
   X-Content-Type-Options: nosniff
   X-Frame-Options: DENY
   ```

3. **Check Certificate:**
   ```bash
   openssl s_client -connect localhost:4000 -servername localhost
   ```

### Automated Testing

Use `sslscan` or `testssl.sh` to verify TLS configuration:

```bash
# With sslscan
sslscan localhost:4000

# Or testssl.sh
./testssl.sh localhost:4000
```

---

## Certificate Renewal

### Validity Period

The self-signed certificate is valid for **10 years**. You should regenerate it before expiration.

### Renewal Process

1. **Backup old certificate (optional):**
   ```bash
   mv ssl/localhost.crt ssl/localhost.crt.old
   mv ssl/localhost.key ssl/localhost.key.old
   ```

2. **Generate new certificate:**
   ```bash
   python generate_ssl_cert.py
   ```

3. **Restart application:**
   ```bash
   # Stop app (Ctrl+C)
   python app.py
   ```

4. **Clear browser cache** to load new certificate

---

## Security Best Practices

### DO ✅
- ✅ Generate new certificate for each environment
- ✅ Restrict access to `ssl/localhost.key` file
- ✅ Keep certificates inside the application directory
- ✅ Backup certificates with encrypted database backups
- ✅ Use strong passwords if encrypting the private key
- ✅ Regenerate if certificate is ever compromised

### DON'T ❌
- ❌ Share private keys
- ❌ Commit certificates to version control
- ❌ Use self-signed certs on public networks
- ❌ Trust certificates from unknown sources
- ❌ Disable certificate validation in production
- ❌ Use weak key sizes (<2048 bits)

---

## HIPAA Compliance

### Requirements Met

| HIPAA Control | Status | Implementation |
|---------------|--------|----------------|
| §164.312(e)(1) Transmission Security | ✅ | TLS 1.2+ encryption |
| §164.312(e)(2)(i) Integrity Controls | ✅ | TLS integrity checks |
| §164.312(e)(2)(ii) Encryption | ✅ | AES-256 (via TLS) |

### Audit Documentation

For HIPAA audits, document:
1. ✅ HTTPS enabled with TLS 1.2+
2. ✅ Security headers implemented
3. ✅ Self-signed certificate appropriate for localhost
4. ✅ Certificate validity period managed
5. ✅ Private key protected with file permissions

---

## Files Reference

### Generated Files
```
ssl/
├── localhost.crt     # Public certificate (safe to share)
└── localhost.key     # Private key (KEEP SECRET!)
```

### Script Files
```
generate_ssl_cert.py  # Certificate generation script
```

### Configuration
```
.env                  # USE_HTTPS=true
app.py               # SSL context configuration (lines 153-182)
```

---

## Support

### Common Questions

**Q: Do I need HTTPS for localhost?**
A: Not strictly required for HIPAA, but highly recommended for defense-in-depth.

**Q: Can I use this certificate for network deployment?**
A: No. Self-signed certificates are only for localhost. Get a CA-signed cert for networks.

**Q: How do I disable the browser warning?**
A: Add the certificate to your OS trusted root store (see "Trusting the Certificate" section).

**Q: Is this secure?**
A: Yes, for localhost. The certificate provides encryption even though it's self-signed.

**Q: Do I need to renew?**
A: Yes, after 10 years. Set a calendar reminder to regenerate before expiration.

---

## Document Control

- **Version:** 1.0
- **Created:** October 22, 2025
- **Last Updated:** October 22, 2025
- **Classification:** Internal - Technical Documentation
- **Review Schedule:** Annually

---

## Related Documents

- `HIPAA_IMPLEMENTATION_SUMMARY.md` - Overall HIPAA compliance status
- `HIPAA_COMPLIANCE_ANALYSIS.md` - Original compliance assessment
- `app.py` - Flask application with HTTPS configuration
- `generate_ssl_cert.py` - Certificate generation script

---

**Status:** ✅ HTTPS Fully Implemented and Documented
