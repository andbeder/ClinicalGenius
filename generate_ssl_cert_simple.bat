@echo off
REM Simple SSL Certificate Generator for Windows
REM Uses OpenSSL if available, otherwise provides manual instructions

echo ============================================================
echo Clinical Genius - SSL Certificate Generator
echo ============================================================
echo.

REM Check if ssl directory exists
if not exist ssl mkdir ssl

REM Try to use OpenSSL if available
where openssl >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo OpenSSL found! Generating certificate...
    echo.

    openssl req -x509 -newkey rsa:4096 -nodes -keyout ssl\localhost.key -out ssl\localhost.crt -days 3650 -subj "/C=US/ST=Local/L=Localhost/O=Clinical Genius/OU=Development/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

    if %ERRORLEVEL% EQU 0 (
        echo.
        echo ============================================================
        echo ✅ SSL Certificate generated successfully!
        echo ============================================================
        echo.
        echo Certificate: ssl\localhost.crt
        echo Private Key: ssl\localhost.key
        echo Valid for: 10 years
        echo.
        echo You can now start the application:
        echo   python app.py
        echo.
        echo Access via: https://localhost:4000
        echo ============================================================
    ) else (
        echo.
        echo ❌ OpenSSL command failed.
        goto manual_instructions
    )
) else (
    echo OpenSSL not found on system.
    goto manual_instructions
)

goto end

:manual_instructions
echo.
echo ============================================================
echo Manual Installation Required
echo ============================================================
echo.
echo OpenSSL is not available. You have two options:
echo.
echo OPTION 1 (EASIEST): Run without HTTPS for now
echo   1. Add to .env: USE_HTTPS=false
echo   2. python app.py
echo   3. Access: http://localhost:4000
echo.
echo OPTION 2: Install OpenSSL then re-run this script
echo   Download from: https://slproweb.com/products/Win32OpenSSL.html
echo   Install "Win64 OpenSSL" (Light version is fine)
echo   Then run this script again
echo.
echo OPTION 3: Install cryptography library
echo   pip install cryptography
echo   python generate_ssl_cert.py
echo.
echo ============================================================

:end
echo.
pause
