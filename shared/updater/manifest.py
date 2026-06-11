from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
import base64
import hashlib
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


DEFAULT_PUBLIC_KEY_RESOURCE = ("shared.updater.public", "update-public-key.pem")
DEFAULT_APP_ID = "mesc"


class ManifestError(RuntimeError):
    """Raised when release metadata is malformed or untrusted."""


@dataclass(frozen=True)
class ReleaseAsset:
    platform: str
    kind: str
    filename: str
    url: str
    sha256: str
    size_bytes: int | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "ReleaseAsset":
        return cls(
            platform=str(data["platform"]),
            kind=str(data["kind"]),
            filename=str(data["filename"]),
            url=str(data["url"]),
            sha256=str(data["sha256"]).lower(),
            size_bytes=int(data["size_bytes"]) if data.get("size_bytes") is not None else None,
        )


@dataclass(frozen=True)
class ReleaseManifest:
    schema_version: int
    app_id: str
    channel: str
    version: str
    published_at: str
    notes: str
    release_page_url: str
    assets: tuple[ReleaseAsset, ...]

    @classmethod
    def from_dict(cls, data: dict) -> "ReleaseManifest":
        assets = tuple(ReleaseAsset.from_dict(item) for item in data.get("assets", []))
        return cls(
            schema_version=int(data["schema_version"]),
            app_id=str(data["app_id"]),
            channel=str(data["channel"]),
            version=str(data["version"]),
            published_at=str(data.get("published_at", "")),
            notes=str(data.get("notes", "")),
            release_page_url=str(data.get("release_page_url", "")),
            assets=assets,
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "app_id": self.app_id,
            "channel": self.channel,
            "version": self.version,
            "published_at": self.published_at,
            "notes": self.notes,
            "release_page_url": self.release_page_url,
            "assets": [
                {
                    "platform": asset.platform,
                    "kind": asset.kind,
                    "filename": asset.filename,
                    "url": asset.url,
                    "sha256": asset.sha256,
                    "size_bytes": asset.size_bytes,
                }
                for asset in self.assets
            ],
        }


def canonical_json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def load_manifest_bytes(manifest_bytes: bytes) -> ReleaseManifest:
    try:
        payload = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"Invalid manifest JSON: {exc}") from exc

    manifest = ReleaseManifest.from_dict(payload)
    if manifest.app_id != DEFAULT_APP_ID:
        raise ManifestError(f"Unexpected app id '{manifest.app_id}'.")
    if manifest.schema_version != 1:
        raise ManifestError(f"Unsupported manifest schema version '{manifest.schema_version}'.")
    return manifest


def sign_manifest_payload(payload: dict, private_key_pem: bytes) -> str:
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ManifestError("Release signing key must be an Ed25519 private key.")
    signature = private_key.sign(canonical_json_bytes(payload))
    return base64.b64encode(signature).decode("ascii")


def verify_manifest_signature(manifest_bytes: bytes, signature_text: str, public_key_pem: bytes) -> None:
    public_key = serialization.load_pem_public_key(public_key_pem)
    if not isinstance(public_key, Ed25519PublicKey):
        raise ManifestError("Embedded update verification key is not an Ed25519 public key.")
    try:
        signature_bytes = base64.b64decode(signature_text.strip())
        public_key.verify(signature_bytes, canonical_json_bytes(json.loads(manifest_bytes.decode("utf-8"))))
    except (InvalidSignature, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError("Release manifest signature verification failed.") from exc


def read_embedded_public_key() -> bytes:
    package_name, filename = DEFAULT_PUBLIC_KEY_RESOURCE
    return resources.files(package_name).joinpath(filename).read_bytes()


def public_key_is_configured() -> bool:
    try:
        key_text = read_embedded_public_key().decode("utf-8").strip()
    except Exception:
        return False
    return "BEGIN PUBLIC KEY" in key_text


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
