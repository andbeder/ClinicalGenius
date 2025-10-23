@echo off
REM Clinical Genius - Dependency Installation Script for Windows
REM Installs all required packages

echo ============================================================
echo Clinical Genius - Installing Dependencies
echo ============================================================
echo.

echo Installing core dependencies...
pip install Flask==3.0.0
pip install python-dotenv==1.0.0
pip install requests==2.31.0
pip install cryptography==41.0.7

echo.
echo ============================================================
echo Core dependencies installed successfully!
echo ============================================================
echo.
echo ============================================================
echo SQLCipher (Database Encryption) - Optional
echo ============================================================
echo.
echo SQLCipher is difficult to install on Windows.
echo.
echo RECOMMENDED: Run without encryption for development:
echo   1. Add this to your .env file: DB_ENCRYPTION=false
echo   2. Start the app: python app.py
echo   3. This is safe for development/testing
echo.
echo ============================================================
echo.
choice /C YN /M "Do you want to try installing SQLCipher now"

if errorlevel 2 goto skip_sqlcipher
if errorlevel 1 goto install_sqlcipher

:install_sqlcipher
echo.
echo Trying pysqlcipher3-wheels...
pip install pysqlcipher3-wheels

if %ERRORLEVEL% EQU 0 (
    echo ✅ SQLCipher installed successfully!
    goto done
)

echo.
echo Trying sqlcipher3...
pip install sqlcipher3

if %ERRORLEVEL% EQU 0 (
    echo ✅ SQLCipher installed successfully!
    goto done
)

echo.
echo Trying pysqlcipher3...
pip install pysqlcipher3

if %ERRORLEVEL% EQU 0 (
    echo ✅ SQLCipher installed successfully!
    goto done
)

echo.
echo ============================================================
echo ⚠️  All SQLCipher installation attempts failed
echo ============================================================
echo.
echo This is NORMAL on Windows. You have two options:
echo.
echo OPTION 1 (EASIEST): Run without encryption for dev/testing
echo   1. Add to .env file: DB_ENCRYPTION=false
echo   2. python app.py
echo.
echo OPTION 2: Enable Windows BitLocker (whole-disk encryption)
echo   Settings -^> Privacy ^& Security -^> Device encryption
echo.
echo See SQLCIPHER_WINDOWS_FIX.md for detailed solutions.
echo ============================================================
goto done

:skip_sqlcipher
echo.
echo ============================================================
echo Skipping SQLCipher installation
echo ============================================================
echo.
echo To run without encryption (development mode):
echo   1. Add to .env file: DB_ENCRYPTION=false
echo   2. python app.py
echo.
echo See SQLCIPHER_WINDOWS_FIX.md for more information.
echo ============================================================

:done
echo.
echo ============================================================
echo Installation Complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Configure .env file (see README.md)
echo   2. Generate SSL certificate: python generate_ssl_cert.py
echo   3. Start application: python app.py
echo.
pause
