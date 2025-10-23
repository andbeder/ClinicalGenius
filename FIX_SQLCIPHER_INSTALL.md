# Fix SQLCipher Installation Issues on Windows

**Problem:** `pysqlcipher3` fails to install on Windows due to compilation requirements

**Solution:** Use pre-compiled alternatives or disable encryption during development

---

## Option 1: Use sqlcipher3-binary (RECOMMENDED - Easiest)

Pre-compiled binary wheel that works on Windows without compilation.

### Installation:

```bash
pip uninstall pysqlcipher3
pip install sqlcipher3-binary
```

### Update Code:

The import statement needs to change slightly. I'll update the files for you.

**No other changes needed** - the API is identical to pysqlcipher3.

---

## Option 2: Use sqlcipher3 (Alternative)

Another pre-compiled option:

```bash
pip uninstall pysqlcipher3
pip install sqlcipher3
```

Same import change as Option 1.

---

## Option 3: Disable Encryption (Development Only)

If you're just testing and not using production PHI yet, you can temporarily disable database encryption:

### Add to .env:

```env
DB_ENCRYPTION=false
```

### How it works:

- Database uses standard SQLite (no encryption)
- Still HIPAA compliant if:
  - Only used for development/testing
  - No production PHI in database
  - Re-enable encryption before production use

### To re-enable encryption later:

1. Remove `DB_ENCRYPTION=false` from .env
2. Run migration script:
   ```bash
   python database/migrate_to_encrypted.py
   ```

---

## Option 4: Install sqlcipher-windows (Advanced)

For users who want native SQLCipher:

### Prerequisites:

1. Install Visual Studio Build Tools
2. Install SQLCipher for Windows
3. Set environment variables

### Steps:

```bash
# Download from: https://github.com/sqlcipher/sqlcipher-windows
# Follow installation instructions
# Then:
pip install pysqlcipher3
```

**Warning:** This is complex and error-prone. Use Option 1 instead.

---

## Comparison

| Option | Difficulty | Encryption | Production Ready |
|--------|-----------|------------|------------------|
| **sqlcipher3-binary** | ⭐ Easy | ✅ Yes | ✅ Yes |
| **sqlcipher3** | ⭐ Easy | ✅ Yes | ✅ Yes |
| **DB_ENCRYPTION=false** | ⭐ Easy | ❌ No | ⚠️ Dev only |
| **Native sqlcipher** | ⭐⭐⭐⭐⭐ Hard | ✅ Yes | ✅ Yes |

---

## Recommended Solution

**Use sqlcipher3-binary** - it's the easiest and production-ready:

```bash
pip install sqlcipher3-binary
```

I'll update your code files to use this library instead.

---

## After Installation

Test the installation:

```bash
python -c "import sqlcipher3; print('✅ SQLCipher installed successfully!')"
```

Expected output:
```
✅ SQLCipher installed successfully!
```

---

## Need Help?

If you still have issues, let me know:
1. What error message you're seeing
2. Your Python version (`python --version`)
3. Your Windows version

Common errors:
- **"Microsoft Visual C++ required"** → Use Option 1 (sqlcipher3-binary)
- **"error: command 'cl.exe' failed"** → Use Option 1 (sqlcipher3-binary)
- **"unable to find vcvarsall.bat"** → Use Option 1 (sqlcipher3-binary)

**The pattern:** Use Option 1! 😊
