# Installation Guide - Clinical Genius

**For Windows Users Having SQLCipher Installation Issues**

---

## Quick Fix (Recommended)

### Option 1: Use Pre-Compiled Binary (Easiest - 30 seconds)

```bash
pip install sqlcipher3-binary
```

That's it! This works on Windows without any compilation.

---

## Full Installation Guide

### Step 1: Install Python Dependencies

**Option A: Use the batch script (Automatic)**

```bash
install_dependencies.bat
```

This script will:
- Install all core dependencies
- Try to install sqlcipher3-binary
- Fall back to alternative if needed
- Test the installation

**Option B: Manual installation**

```bash
# Core dependencies
pip install Flask==3.0.0
pip install python-dotenv==1.0.0
pip install requests==2.31.0
pip install cryptography==41.0.7

# Database encryption (choose ONE):
pip install sqlcipher3-binary  # Recommended for Windows
```

### Step 2: Verify Installation

```bash
python -c "import sqlcipher3; print('✅ SQLCipher works!')"
```

**Expected output:**
```
✅ SQLCipher works!
```

---

## If Installation Still Fails

### Temporary Workaround: Disable Encryption (Development Only)

⚠️ **WARNING: Only use this for development/testing without production PHI**

1. Add to your `.env` file:
   ```env
   DB_ENCRYPTION=false
   ```

2. Start the application:
   ```bash
   python app.py
   ```

3. The application will use unencrypted SQLite

4. **Before using production PHI**, install SQLCipher and remove `DB_ENCRYPTION=false`

---

## Different SQLCipher Options

| Library | Installation | Windows Support | Notes |
|---------|-------------|-----------------|-------|
| **sqlcipher3-binary** | `pip install sqlcipher3-binary` | ✅ Excellent | Pre-compiled, recommended |
| **sqlcipher3** | `pip install sqlcipher3` | ✅ Good | Alternative pre-compiled |
| **pysqlcipher3** | `pip install pysqlcipher3` | ❌ Poor | Requires Visual Studio |

**The code automatically detects which library you have installed** - just install one of them.

---

## Troubleshooting Common Errors

### Error: "Microsoft Visual C++ 14.0 or greater is required"

**Solution:** Use pre-compiled binary:
```bash
pip install sqlcipher3-binary
```

### Error: "error: command 'cl.exe' failed"

**Solution:** Use pre-compiled binary:
```bash
pip install sqlcipher3-binary
```

### Error: "Unable to find vcvarsall.bat"

**Solution:** Use pre-compiled binary:
```bash
pip install sqlcipher3-binary
```

**Pattern:** All compilation errors → Use `sqlcipher3-binary`

### Error: "No module named 'sqlcipher3'"

**Solution:** Install it:
```bash
pip install sqlcipher3-binary
```

### Error: "ImportError: No SQLCipher library found"

**Solution:** Install one of the SQLCipher libraries:
```bash
pip install sqlcipher3-binary
```

Or temporarily disable encryption (dev only):
```env
# In .env file
DB_ENCRYPTION=false
```

---

## After Installation

### Test the Application

1. **Configure .env file:**
   ```env
   SFDC_USERNAME=your-email@example.com
   SFDC_CLIENT_ID=your-salesforce-client-id
   SFDC_LOGIN_URL=https://login.salesforce.com
   KEY_PASS=your-key-passphrase

   # Optional: HTTPS (recommended)
   USE_HTTPS=true

   # Optional: LLM Provider
   LLM_PROVIDER=lm_studio
   ```

2. **Generate SSL certificate (if using HTTPS):**
   ```bash
   python generate_ssl_cert.py
   ```

3. **Start the application:**
   ```bash
   python app.py
   ```

4. **Access the application:**
   - With HTTPS: https://localhost:4000
   - Without HTTPS: http://localhost:4000

---

## Encryption Status Check

### How to verify encryption is working:

```bash
python -c "from database.db import USE_ENCRYPTION; print(f'Encryption: {'✅ Enabled' if USE_ENCRYPTION else '❌ Disabled'}')"
```

### Check which SQLCipher library is installed:

```bash
python -c "try:
    import sqlcipher3
    print('✅ sqlcipher3-binary or sqlcipher3')
except:
    try:
        import pysqlcipher3
        print('✅ pysqlcipher3')
    except:
        print('❌ No SQLCipher library installed')"
```

---

## Production Checklist

Before using with production PHI:

- [ ] SQLCipher installed (not `DB_ENCRYPTION=false`)
- [ ] `.encryption_key` file generated
- [ ] Database encrypted (test with verify script)
- [ ] HTTPS enabled (`USE_HTTPS=true`)
- [ ] `SFDC_USERNAME` configured in .env
- [ ] BAA status documented for all providers
- [ ] Audit logging enabled (automatic)

---

## Full Dependency List

```
Flask==3.0.0              # Web framework
python-dotenv==1.0.0      # Environment variables
requests==2.31.0          # HTTP requests
cryptography==41.0.7      # Cryptographic functions
sqlcipher3-binary         # Database encryption (Windows-friendly)
```

---

## Getting Help

1. **Installation Issues:**
   - See `FIX_SQLCIPHER_INSTALL.md`
   - Try the batch script: `install_dependencies.bat`
   - Use temporary workaround: `DB_ENCRYPTION=false` in .env

2. **HTTPS Issues:**
   - See `HTTPS_SETUP.md`
   - Run: `python generate_ssl_cert.py`

3. **General Setup:**
   - See `README.md`
   - See `QUICKSTART_HTTPS.md`

---

## Summary

**Easiest path to get started:**

```bash
# 1. Install dependencies
pip install sqlcipher3-binary Flask python-dotenv requests cryptography

# 2. Configure .env
# (Add SFDC_USERNAME and Salesforce config)

# 3. Generate SSL certificate (optional but recommended)
python generate_ssl_cert.py

# 4. Start application
python app.py

# 5. Access via browser
https://localhost:4000
```

**Total time:** ~5 minutes

---

## Still Having Issues?

Check your Python version:
```bash
python --version
```

**Supported:** Python 3.8 or higher

If you're using an older Python version, upgrade first:
- Download from: https://www.python.org/downloads/

---

**Status:** ✅ Installation guide complete!
