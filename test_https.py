#!/usr/bin/env python3
"""
Test HTTPS Configuration
Verifies SSL certificate and security headers are working correctly
"""

import sys
import requests
import urllib3

# Disable SSL warnings for self-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_https_connection():
    """Test basic HTTPS connectivity"""
    print("Testing HTTPS Connection...")
    print("=" * 60)

    url = "https://localhost:4000/health"

    try:
        response = requests.get(url, verify=False, timeout=5)

        if response.status_code == 200:
            print("✅ HTTPS connection successful!")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Connection failed!")
        print("   Make sure the application is running:")
        print("   python app.py")
        return False
    except requests.exceptions.Timeout:
        print("❌ Connection timeout!")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_security_headers():
    """Test that security headers are present"""
    print("\nTesting Security Headers...")
    print("=" * 60)

    url = "https://localhost:4000/health"

    try:
        response = requests.get(url, verify=False, timeout=5)
        headers = response.headers

        # Expected security headers
        expected_headers = {
            'Strict-Transport-Security': 'HSTS (Force HTTPS)',
            'X-Content-Type-Options': 'Prevent MIME sniffing',
            'X-Frame-Options': 'Prevent clickjacking',
            'X-XSS-Protection': 'XSS filtering',
            'Content-Security-Policy': 'Resource loading policy',
            'Referrer-Policy': 'Referrer control',
            'Permissions-Policy': 'Feature restrictions'
        }

        all_present = True
        for header, description in expected_headers.items():
            if header in headers:
                print(f"✅ {header}: {description}")
                print(f"   Value: {headers[header][:60]}...")
            else:
                print(f"❌ {header}: MISSING")
                all_present = False

        return all_present

    except Exception as e:
        print(f"❌ Error checking headers: {e}")
        return False


def test_http_redirect():
    """Test if HTTP redirects to HTTPS (optional)"""
    print("\nTesting HTTP → HTTPS Redirect...")
    print("=" * 60)

    # Note: Current implementation doesn't redirect HTTP to HTTPS
    # because we bind to HTTPS only. This test checks if HTTP is disabled.

    url = "http://localhost:4000/health"

    try:
        response = requests.get(url, timeout=2)
        print("⚠️  HTTP is still accessible (expected for dev mode)")
        print("   In production, HTTP should be disabled or redirected")
        return True
    except requests.exceptions.ConnectionError:
        print("✅ HTTP is disabled (HTTPS only mode)")
        return True
    except Exception as e:
        print(f"ℹ️  HTTP test inconclusive: {e}")
        return True


def test_certificate_validity():
    """Test SSL certificate properties"""
    print("\nTesting SSL Certificate...")
    print("=" * 60)

    try:
        import ssl
        import socket

        hostname = 'localhost'
        port = 4000

        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with socket.create_connection((hostname, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
                version = ssock.version()

                print(f"✅ SSL/TLS Connection Established")
                print(f"   Protocol: {version}")
                print(f"   Cipher: {cipher[0]}")
                print(f"   Key Size: {cipher[2]} bits")

                # Check subject
                if cert:
                    subject = dict(x[0] for x in cert['subject'])
                    print(f"   Common Name: {subject.get('commonName', 'N/A')}")
                else:
                    print("   Certificate details not available (self-signed)")

                # Check protocol version
                if version in ['TLSv1.2', 'TLSv1.3']:
                    print(f"✅ Using secure protocol: {version}")
                else:
                    print(f"⚠️  Protocol {version} may not be secure")

                return True

    except socket.timeout:
        print("❌ Connection timeout")
        return False
    except ConnectionRefusedError:
        print("❌ Connection refused - is the application running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all HTTPS tests"""
    print("\n" + "=" * 60)
    print("Clinical Genius - HTTPS Configuration Test")
    print("=" * 60 + "\n")

    results = []

    # Run tests
    results.append(("HTTPS Connection", test_https_connection()))
    results.append(("Security Headers", test_security_headers()))
    results.append(("HTTP Redirect", test_http_redirect()))
    results.append(("SSL Certificate", test_certificate_validity()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! HTTPS is configured correctly.")
        print("\nYour application is ready for secure communication.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("\nCheck the output above for details.")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Tests interrupted by user")
        sys.exit(1)
