# Quick Start - Get Running in 2 Minutes

**Skip SQLCipher issues - Start the app NOW!**

---

## Step 1: Install Dependencies (30 seconds)

```bash
pip install Flask python-dotenv requests cryptography
```

---

## Step 2: Configure .env (30 seconds)

Create `.env` file with:

```env
# Disable encryption for development (EASY FIX for Windows)
DB_ENCRYPTION=false

# Your Salesforce username
SFDC_USERNAME=your-email@example.com

# Salesforce configuration
SFDC_CLIENT_ID=your-salesforce-client-id
SFDC_LOGIN_URL=https://login.salesforce.com
KEY_PASS=your-key-passphrase

# HTTPS (optional but recommended)
USE_HTTPS=true

# LLM Provider
LLM_PROVIDER=lm_studio
LM_STUDIO_ENDPOINT=http://localhost:1234
```

---

## Step 3: Generate SSL Certificate (30 seconds) - Optional

```bash
python generate_ssl_cert.py
```

Skip this if you want to start even faster (HTTPS will be disabled).

---

## Step 4: Start Application (10 seconds)

```bash
python app.py
```

---

## Step 5: Open Browser (10 seconds)

**With HTTPS:**
https://localhost:4000

**Without HTTPS (if you skipped step 3):**
http://localhost:4000

---

## ✅ Done! Application is running!

---

## About DB_ENCRYPTION=false

**What it means:**
- Database uses standard SQLite (no encryption)
- All other security features still work (HTTPS, audit logs, access control)
- Safe for development and testing
- Not recommended for production PHI

**When to enable encryption:**
- Before using production patient data
- See `SQLCIPHER_WINDOWS_FIX.md` for options

**Alternative: Enable Windows BitLocker**
- Encrypts your entire drive (including database)
- Settings → Privacy & Security → Device encryption
- Achieves same security goal as SQLCipher

---

## HIPAA Status with DB_ENCRYPTION=false

**Still Have (7/8 controls):**
- ✅ HTTPS/TLS encryption
- ✅ Localhost-only access
- ✅ User authentication
- ✅ Audit logging
- ✅ Access controls
- ✅ Security headers
- ✅ BAA management

**Missing:**
- ❌ Database file encryption (mitigated by Windows BitLocker)

---

## Next Steps

1. **Explore the application** - it's fully functional!
2. **Enable BitLocker** for disk encryption
3. **Read HIPAA documentation** before production use
4. **Try SQLCipher later** if you want database-level encryption

---

## Troubleshooting

### Port already in use?

Change port in `.env`:
```env
PORT=5000
```

### Can't connect to Salesforce?

Check your SFDC credentials in `.env` file.

### SSL certificate warning?

This is normal for self-signed certificates. Click "Advanced" → "Proceed to localhost".

---

## For More Information

- `SQLCIPHER_WINDOWS_FIX.md` - Encryption options
- `HTTPS_SETUP.md` - SSL/TLS details
- `HIPAA_COMPLETE.md` - HIPAA compliance guide
- `README.md` - Full documentation

---

**Total Time: 2 minutes**
**Status: ✅ Running and ready to use!**
