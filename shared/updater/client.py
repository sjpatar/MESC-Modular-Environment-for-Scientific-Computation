from __future__ import annotations

from dataclasses import dataclass
import platform as py_platform
from pathlib import Path
from tempfile import mkdtemp
from urllib.request import urlopen

from shared.updater.manifest import (
    ManifestError,
    ReleaseAsset,
    ReleaseManifest,
    load_manifest_bytes,
    public_key_is_configured,
    read_embedded_public_key,
    sha256_file,
    verify_manifest_signature,
)
from shared.updater.versioning import get_current_version, is_newer_version


class UpdateError(RuntimeError):
    """Raised when update discovery or download fails."""


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: str
    latest_version: str
    update_available: bool
    manifest: ReleaseManifest | None
    asset: ReleaseAsset | None


def detect_platform_tag() -> str:
    system = py_platform.system().lower()
    machine = py_platform.machine().lower()

    if system == "windows":
        arch = "x64" if "64" in machine or machine == "amd64" else machine
        return f"windows-{arch}"
    if system == "darwin":
        arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
        return f"macos-{arch}"
    arch = "x64" if machine in {"x86_64", "amd64"} else machine
    return f"linux-{arch}"


def fetch_release_manifest(manifest_url: str, expected_channel: str) -> ReleaseManifest:
    if not public_key_is_configured():
        raise UpdateError(
            "Update verification is not configured yet. Generate a signing keypair before publishing releases."
        )

    manifest_bytes = _fetch_url_bytes(manifest_url)
    signature_text = _fetch_url_bytes(f"{manifest_url}.sig").decode("utf-8")
    verify_manifest_signature(manifest_bytes, signature_text, read_embedded_public_key())
    manifest = load_manifest_bytes(manifest_bytes)

    if manifest.channel != expected_channel:
        raise UpdateError(
            f"Expected release channel '{expected_channel}', but manifest channel was '{manifest.channel}'."
        )
    return manifest


def check_for_updates(manifest_url: str, expected_channel: str, target_platform: str | None = None) -> UpdateCheckResult:
    current_version = get_current_version()
    manifest = fetch_release_manifest(manifest_url, expected_channel)
    asset = select_asset_for_platform(manifest, target_platform or detect_platform_tag())
    latest_version = manifest.version
    return UpdateCheckResult(
        current_version=current_version,
        latest_version=latest_version,
        update_available=is_newer_version(latest_version, current_version),
        manifest=manifest,
        asset=asset,
    )


def select_asset_for_platform(manifest: ReleaseManifest, platform_tag: str) -> ReleaseAsset | None:
    for asset in manifest.assets:
        if asset.platform == platform_tag:
            return asset
    return None


def download_asset(asset: ReleaseAsset) -> Path:
    temp_dir = Path(mkdtemp(prefix="mesc-update-"))
    destination = temp_dir / asset.filename
    with urlopen(asset.url, timeout=30) as response, open(destination, "wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)

    actual_sha256 = sha256_file(destination)
    if actual_sha256.lower() != asset.sha256.lower():
        raise UpdateError(
            f"Downloaded asset hash mismatch for '{asset.filename}'. Expected {asset.sha256}, got {actual_sha256}."
        )
    return destination


def _fetch_url_bytes(url: str) -> bytes:
    try:
        with urlopen(url, timeout=15) as response:
            return response.read()
    except Exception as exc:
        raise UpdateError(f"Failed to fetch '{url}': {exc}") from exc
