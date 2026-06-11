from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from shared.updater.client import detect_platform_tag, select_asset_for_platform
from shared.updater.manifest import (
    ReleaseManifest,
    canonical_json_bytes,
    load_manifest_bytes,
    sha256_file,
    sign_manifest_payload,
    verify_manifest_signature,
)
from shared.updater.versioning import is_newer_version


def test_manifest_signature_round_trip():
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    payload = {
        "schema_version": 1,
        "app_id": "mesc",
        "channel": "stable",
        "version": "1.2.0",
        "published_at": "2026-06-05T00:00:00+00:00",
        "notes": "Bug fixes",
        "release_page_url": "https://example.invalid/release",
        "assets": [],
    }
    manifest_bytes = canonical_json_bytes(payload)
    signature_text = sign_manifest_payload(payload, private_pem)

    verify_manifest_signature(manifest_bytes, signature_text, public_pem)
    manifest = load_manifest_bytes(manifest_bytes)

    assert manifest.version == "1.2.0"
    assert manifest.channel == "stable"


def test_select_asset_for_current_platform():
    manifest = ReleaseManifest.from_dict(
        {
            "schema_version": 1,
            "app_id": "mesc",
            "channel": "stable",
            "version": "1.1.0",
            "published_at": "",
            "notes": "",
            "release_page_url": "",
            "assets": [
                {
                    "platform": detect_platform_tag(),
                    "kind": "installer",
                    "filename": "MESC-Setup.exe",
                    "url": "https://example.invalid/MESC-Setup.exe",
                    "sha256": "00" * 32,
                    "size_bytes": 123,
                }
            ],
        }
    )

    asset = select_asset_for_platform(manifest, detect_platform_tag())

    assert asset is not None
    assert asset.filename == "MESC-Setup.exe"


def test_version_comparison():
    assert is_newer_version("1.0.1", "1.0.0")
    assert is_newer_version("1.2.0", "1.1.9")
    assert not is_newer_version("1.0.0", "1.0.0")


def test_sha256_file(tmp_path):
    payload_path = tmp_path / "payload.bin"
    payload_path.write_bytes(b"mesc")

    digest = sha256_file(payload_path)

    assert len(digest) == 64
