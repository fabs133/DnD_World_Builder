"""TLS utilities for multiplayer session encryption.

Generates a self-signed certificate at session start so all
WebSocket traffic is encrypted. The certificate is ephemeral —
new one per hosting session.

Requires no external dependencies beyond Python's ``ssl`` module.
Uses ``cryptography`` if available for proper X.509 generation,
falls back to a temporary OpenSSL subprocess otherwise.
"""

from __future__ import annotations

import logging
import os
import ssl
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def create_self_signed_ssl_context() -> ssl.SSLContext | None:
    """Create an SSL context with a self-signed certificate.

    Returns ``None`` if certificate generation fails (missing
    ``cryptography`` library and no ``openssl`` on PATH).
    """
    try:
        return _create_with_cryptography()
    except ImportError:
        pass
    try:
        return _create_with_openssl()
    except Exception as exc:
        logger.warning(f"Failed to create SSL context: {exc}")
        return None


def _create_with_cryptography() -> ssl.SSLContext:
    """Generate using the ``cryptography`` library (preferred)."""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import datetime

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "DnD World Builder Session"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )

    # Write to temp files
    cert_path, key_path = _write_temp_pem(cert, key)

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(str(cert_path), str(key_path))
    logger.info("TLS: self-signed certificate generated (cryptography)")
    return ctx


def _create_with_openssl() -> ssl.SSLContext:
    """Fallback: generate using the ``openssl`` CLI tool."""
    import subprocess

    tmp_dir = Path(tempfile.mkdtemp(prefix="dnd_tls_"))
    cert_path = tmp_dir / "cert.pem"
    key_path = tmp_dir / "key.pem"

    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(key_path), "-out", str(cert_path),
            "-days", "1", "-nodes",
            "-subj", "/CN=DnD World Builder Session",
        ],
        check=True,
        capture_output=True,
        timeout=10,
    )

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(str(cert_path), str(key_path))
    logger.info("TLS: self-signed certificate generated (openssl CLI)")
    return ctx


def _write_temp_pem(cert, key) -> tuple[Path, Path]:
    """Write certificate and key to temporary PEM files."""
    from cryptography.hazmat.primitives import serialization

    tmp_dir = Path(tempfile.mkdtemp(prefix="dnd_tls_"))
    cert_path = tmp_dir / "cert.pem"
    key_path = tmp_dir / "key.pem"

    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    return cert_path, key_path
