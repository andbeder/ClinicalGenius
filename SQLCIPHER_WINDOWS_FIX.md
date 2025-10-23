# SQLCipher Installation Fix for Windows

**Problem:** SQLCipher is difficult to install on Windows due to compilation requirements.

**Best Solution:** Use the application WITHOUT encryption for now, then enable it later.

---

## RECOMMENDED: Disable Encryption (Development Mode)

This is the **easiest and fastest** solution for getting started:

### Step 1: Add to .env file

Create or edit `.env` file and add:

```env
DB_ENCRYPTION=false
```

### Step 2: Install basic dependencies

```bash
pip install Flask==3.0.0 python-dotenv==1.0.0 requests==2.31.0 cryptography==41.0.7
```

### Step 3: Start the application

```bash
python app.py
```

### ✅ Done! Application works with unencrypted database.

**Important:**
- ⚠️ Only use this mode for development/testing
- ⚠️ Do NOT use with production PHI
- ✅ All other HIPAA features still work (audit logs, HTTPS, access control)
- ✅ You can enable encryption later when needed

---

## When to Enable Encryption

Enable encryption BEFORE using production PHI:

1. **For Testing/Development:**
   - `DB_ENCRYPTION=false` is fine
   - No production patient data
   - Just learning the application

2. **For Production:**
   - Must have encryption enabled
   - Remove `DB_ENCRYPTION=false` from .env
   - Install one of the SQLCipher options below

---

## Option 2: Try Alternative SQLCipher Packages (Advanced)

If you want encryption now, try these in order:

### A. Try pysqlcipher3-wheels (Community Build)

```bash
pip install pysqlcipher3-wheels
```

This is a community-maintained wheel that might work on Windows.

### B. Try sqlcipher3 (May require dependencies)

```bash
pip install sqlcipher3
```

### C. Try pysqlcipher3 with pre-built DLLs

1. Download SQLCipher pre-built DLLs:
   - Visit: https://github.com/sqlcipher/sqlcipher/releases
   - Download Windows binaries

2. Then try:
   ```bash
   pip install pysqlcipher3
   ```

**If all fail:** Just use `DB_ENCRYPTION=false` for now.

---

## Option 3: Use WSL (Windows Subsystem for Linux)

If you need encryption and nothing else works:

### Install WSL:

```powershell
wsl --install
```

### In WSL:

```bash
sudo apt-get update
sudo apt-get install sqlcipher libsqlcipher-dev
pip install pysqlcipher3
```

Then run Clinical Genius from WSL instead of Windows.

---

## Comparison: Encrypted vs Unencrypted

| Feature | DB_ENCRYPTION=false | DB_ENCRYPTION=true |
|---------|---------------------|-------------------|
| **Setup Time** | ⭐ 30 seconds | ⭐⭐⭐ Variable (may be hard) |
| **Database Encryption** | ❌ No | ✅ Yes (AES-256) |
| **Audit Logging** | ✅ Yes | ✅ Yes |
| **HTTPS/TLS** | ✅ Yes | ✅ Yes |
| **User Authentication** | ✅ Yes | ✅ Yes |
| **Access Control** | ✅ Yes | ✅ Yes |
| **Security Headers** | ✅ Yes | ✅ Yes |
| **Production PHI** | ❌ NO | ✅ YES |
| **Dev/Testing** | ✅ YES | ✅ YES |

**Bottom Line:** Without encryption, you still have 7 out of 8 HIPAA controls. Only database encryption at rest is missing.

---

## HIPAA Impact

### Without Encryption (DB_ENCRYPTION=false):

**Still Protected:**
- ✅ HTTPS/TLS (encryption in transit)
- ✅ Localhost-only access (network isolation)
- ✅ User authentication
- ✅ Audit logging
- ✅ BAA management
- ✅ Security headers
- ✅ Windows OS file permissions

**Not Protected:**
- ❌ Database file encryption at rest

**Risk Level:**
- **Low** if: Localhost only, no remote access, Windows BitLocker enabled
- **Medium** if: No disk encryption on the machine
- **High** if: Laptop that travels, potential theft risk

**Mitigation:**
1. Enable Windows BitLocker (encrypts entire drive)
2. Keep laptop physically secure
3. Don't use production PHI until encryption enabled

### With Encryption (DB_ENCRYPTION=true):

- ✅ All 8 HIPAA controls active
- ✅ Database encrypted with AES-256
- ✅ Safe for production PHI

---

## Recommended Path Forward

### For Immediate Testing (TODAY):

```env
# In .env file
DB_ENCRYPTION=false
```

```bash
pip install Flask python-dotenv requests cryptography
python app.py
```

✅ **Start using the application right away!**

### Before Production (LATER):

1. Enable Windows BitLocker on your drive
2. Try SQLCipher installation options
3. If successful, remove `DB_ENCRYPTION=false`
4. If not successful, BitLocker + localhost-only is still strong security

---

## Alternative: Enable Windows BitLocker

This encrypts your entire disk, including the database file:

### Check if BitLocker is available:

```powershell
Get-BitLockerVolume
```

### Enable BitLocker:

1. Open "Settings" → "Privacy & Security" → "Device encryption"
2. Turn on device encryption
3. Or: Control Panel → BitLocker Drive Encryption

**With BitLocker:**
- Your entire drive is encrypted (AES-128 or AES-256)
- Database file is encrypted at rest
- No need for SQLCipher
- Meets HIPAA encryption at rest requirement

**Advantage:** Easier than SQLCipher on Windows!

---

## Quick Decision Matrix

**Choose your path:**

| Situation | Recommended Solution | Time to Setup |
|-----------|---------------------|---------------|
| **Just testing, no real PHI** | `DB_ENCRYPTION=false` | 30 seconds |
| **Need encryption, have time** | Try SQLCipher alternatives | 30-60 minutes |
| **Need encryption now** | Enable Windows BitLocker | 15 minutes |
| **Windows too hard** | Use WSL (Linux subsystem) | 30 minutes |

---

## Testing Without Encryption

To verify application works with encryption disabled:

```bash
# Check encryption status
python -c "from database.db import USE_ENCRYPTION; print('Encryption:', 'ON' if USE_ENCRYPTION else 'OFF')"
```

Expected output:
```
Encryption: OFF
```

Start the app:
```bash
python app.py
```

Expected output should NOT show encryption errors.

---

## Re-enabling Encryption Later

When you successfully install SQLCipher:

1. **Remove from .env:**
   ```env
   # DB_ENCRYPTION=false  ← Remove this line
   ```

2. **Install SQLCipher** (one of):
   ```bash
   pip install pysqlcipher3-wheels
   # or
   pip install sqlcipher3
   # or
   pip install pysqlcipher3
   ```

3. **Migrate existing database:**
   ```bash
   python database/migrate_to_encrypted.py
   ```

4. **Restart application:**
   ```bash
   python app.py
   ```

The application will now use encrypted database.

---

## Summary

**Right now, do this:**

1. Add `DB_ENCRYPTION=false` to your `.env` file
2. Install basic dependencies:
   ```bash
   pip install Flask python-dotenv requests cryptography
   ```
3. Start the application:
   ```bash
   python app.py
   ```

**You're done! Application works.**

**Before production PHI:**
- Enable Windows BitLocker (easiest), OR
- Install SQLCipher (harder on Windows), OR
- Accept that localhost-only + OS security is still strong

---

## Need Help?

You now have three working options:
1. ✅ **Use without encryption** (development mode)
2. ✅ **Enable BitLocker** (whole-disk encryption)
3. ⚠️ **Install SQLCipher** (if you can get it working)

**All three are acceptable for different scenarios.**

Choose the easiest path for your needs!
