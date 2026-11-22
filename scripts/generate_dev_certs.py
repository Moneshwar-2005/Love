"""
LOVE Local Development Certificate Authority & TLS Certificate Generator.
Generates:
1. Local Development Root CA (love_dev_ca.crt & love_dev_ca.key)
2. Server TLS Certificate (love_dev_server.crt & love_dev_server.key) with SAN:
   - IP: 192.168.0.176
   - IP: 127.0.0.1
   - IP: 10.0.2.2
   - DNS: localhost
   - DNS: love.local
3. Concatenated bundle (love_dev_bundle.crt)
4. Copies CA certificate to Android debug resources:
   mobile/android/app/src/debug/res/raw/love_dev_ca.crt

Private keys are stored in `secrets/certs/` (gitignored) with restricted permissions.
Private keys are NEVER printed or exposed.
"""

import datetime
import ipaddress
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CERTS_DIR = PROJECT_ROOT / "secrets" / "certs"
ANDROID_RAW_DIR = PROJECT_ROOT / "mobile" / "android" / "app" / "src" / "debug" / "res" / "raw"


def generate_dev_certs() -> None:
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    ANDROID_RAW_DIR.mkdir(parents=True, exist_ok=True)

    ca_key_path = CERTS_DIR / "love_dev_ca.key"
    ca_crt_path = CERTS_DIR / "love_dev_ca.crt"
    server_key_path = CERTS_DIR / "love_dev_server.key"
    server_crt_path = CERTS_DIR / "love_dev_server.crt"
    bundle_crt_path = CERTS_DIR / "love_dev_bundle.crt"
    android_ca_path = ANDROID_RAW_DIR / "love_dev_ca.crt"

    print("=" * 70)
    print("  LOVE Local Development TLS Certificate Generator")
    print("=" * 70)

    now = datetime.datetime.now(datetime.timezone.utc)
    valid_from = now - datetime.timedelta(days=1)
    valid_to = now + datetime.timedelta(days=365)

    # 1. Generate Development Root CA
    print("[1/5] Generating Development Root CA...")
    ca_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    ca_subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "LOVE Development Root CA"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "LOVE Personal AI Assistant"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Development Security"),
    ])

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_subject)
        .issuer_name(ca_subject)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(valid_from)
        .not_valid_after(valid_to)
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=1),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=False,
                key_cert_sign=True,
                crl_sign=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    # Write CA Private Key with restricted permissions
    with open(ca_key_path, "wb") as f:
        f.write(
            ca_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    # Write CA Certificate
    with open(ca_crt_path, "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
    print(f"      Root CA generated: {ca_crt_path.name}")

    # 2. Generate Server Certificate
    print("[2/5] Generating Server TLS Certificate with SAN...")
    server_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    server_subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "192.168.0.176"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "LOVE Personal AI Assistant"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Development Server"),
    ])

    san_entries = [
        x509.IPAddress(ipaddress.IPv4Address("192.168.0.176")),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        x509.IPAddress(ipaddress.IPv4Address("10.0.2.2")),
        x509.DNSName("localhost"),
        x509.DNSName("love.local"),
    ]

    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_subject)
        .issuer_name(ca_subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(valid_from)
        .not_valid_after(valid_to)
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName(san_entries),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    # Write Server Private Key
    with open(server_key_path, "wb") as f:
        f.write(
            server_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    # Write Server Certificate
    server_pem = server_cert.public_bytes(serialization.Encoding.PEM)
    ca_pem = ca_cert.public_bytes(serialization.Encoding.PEM)
    with open(server_crt_path, "wb") as f:
        f.write(server_pem)

    # Write Bundle (Server + CA)
    with open(bundle_crt_path, "wb") as f:
        f.write(server_pem + b"\n" + ca_pem)
    print(f"      Server Certificate generated: {server_crt_path.name}")
    print(f"      Certificate Bundle created: {bundle_crt_path.name}")

    # 3. Restrict Permissions on Private Keys
    print("[3/5] Restricting filesystem permissions on private keys...")
    for key_file in (ca_key_path, server_key_path):
        try:
            os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)
            # On Windows, use icacls if available
            if sys.platform == "win32":
                username = os.environ.get("USERNAME", "ADMIN")
                subprocess.run(
                    ["icacls", str(key_file), "/inheritance:r", f"/grant:r", f"{username}:(R,W)"],
                    capture_output=True,
                    check=False,
                )
        except Exception as e:
            print(f"      Warning adjusting permissions for {key_file.name}: {e}")
    print("      Permissions restricted.")

    # 4. Copy Root CA to Android Debug Raw Resources
    print("[4/5] Deploying Root CA to Android debug resource directory...")
    shutil.copyfile(ca_crt_path, android_ca_path)
    print(f"      Copied to: {android_ca_path}")

    # 5. Verify Generated Certificate
    print("[5/5] Verifying Subject Alternative Name (SAN) & Extensions...")
    san_ext = server_cert.extensions.get_extension_for_oid(x509.OID_SUBJECT_ALTERNATIVE_NAME)
    names = [str(n.value) for n in san_ext.value]
    print(f"      SAN entries: {names}")
    assert "192.168.0.176" in names, "Missing 192.168.0.176 in SAN"
    assert "127.0.0.1" in names, "Missing 127.0.0.1 in SAN"
    assert "localhost" in names, "Missing localhost in SAN"
    print("=" * 70)
    print("  TLS Certificate Generation & Verification Successful!")
    print("=" * 70)


if __name__ == "__main__":
    generate_dev_certs()
