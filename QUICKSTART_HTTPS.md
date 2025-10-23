# Quick Start - HTTPS Setup

**Time Required:** 2 minutes
**Prerequisites:** Application already installed and working on HTTP

---

## Step 1: Generate Certificate (30 seconds)

```bash
python generate_ssl_cert.py
```

**Expected Output:**
```
✅ SSL Certificate generated successfully!
Certificate: ssl\localhost.crt
Private Key: ssl\localhost.key
```

---

## Step 2: Start Application (10 seconds)

```bash
python app.py
```

**Expected Output:**
```
🔒 SSL/TLS Enabled - Using self-signed certificate
Starting Clinical Genius on localhost:4000
Access URL: https://localhost:4000
```

---

## Step 3: Open Browser (1 minute)

1. Open: **https://localhost:4000** (note the **https://**)

2. You'll see a security warning - this is **normal** for self-signed certificates

3. Click **"Advanced"** → **"Proceed to localhost (unsafe)"**

4. Application loads! ✅

---

## That's It!

Your application is now running with HTTPS encryption.

### Verify It's Working

Check for the lock icon (🔒) in your browser's address bar.

### What Just Happened?

- ✅ All traffic is now encrypted with TLS 1.2+
- ✅ Security headers are automatically added
- ✅ HIPAA encryption-in-transit requirement satisfied

---

## Troubleshooting

### Certificate Not Found?

```bash
# Regenerate it
python generate_ssl_cert.py
```

### Still See HTTP?

Make sure you're accessing **https://** not http://

### Connection Refused?

Check the application is running:
```bash
python app.py
```

---

## For More Information

See `HTTPS_SETUP.md` for complete documentation including:
- Certificate details
- Security headers explanation
- Production deployment guide
- Troubleshooting guide

---

**Status:** ✅ HTTPS Enabled - You're good to go!
