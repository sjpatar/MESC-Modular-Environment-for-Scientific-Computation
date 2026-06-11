from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.updater.manifest import canonical_json_bytes, sha256_file, sign_manifest_payload


def parse_asset(asset_spec: str) -> dict:
    parts = asset_spec.split("|")
    if len(parts) != 4:
        raise ValueError(
            "Asset specs must look like 'platform|kind|path|url'. "
            f"Received: {asset_spec}"
        )

    platform_tag, kind, file_path, url = parts
    asset_path = Path(file_path)
    if not asset_path.exists():
        raise FileNotFoundError(f"Asset file does not exist: {asset_path}")

    return {
        "platform": platform_tag,
        "kind": kind,
        "filename": asset_path.name,
        "url": url,
        "sha256": sha256_file(asset_path),
        "size_bytes": asset_path.stat().st_size,
    }


def main():
    parser = argparse.ArgumentParser(description="Build and sign a MESC release manifest.")
    parser.add_argument("--version", required=True)
    parser.add_argument("--channel", default="stable")
    parser.add_argument("--notes", default="")
    parser.add_argument("--release-page-url", required=True)
    parser.add_argument("--private-key", required=True)
    parser.add_argument(
        "--asset",
        action="append",
        default=[],
        help="Asset definition: platform|kind|path|url",
    )
    parser.add_argument("--output-dir", default="release/output")
    args = parser.parse_args()

    assets = [parse_asset(item) for item in args.asset]
    manifest = {
        "schema_version": 1,
        "app_id": "mesc",
        "channel": args.channel,
        "version": args.version,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "notes": args.notes,
        "release_page_url": args.release_page_url,
        "assets": assets,
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    private_key_pem = Path(args.private_key).read_bytes()
    signature_text = sign_manifest_payload(manifest, private_key_pem)

    manifest_path = output_dir / "release-manifest.json"
    signature_path = output_dir / "release-manifest.json.sig"
    checksums_path = output_dir / "SHA256SUMS.txt"

    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    signature_path.write_text(signature_text + "\n", encoding="utf-8")

    checksums_lines = [
        f"{sha256_file(manifest_path)}  {manifest_path.name}",
        f"{sha256_file(signature_path)}  {signature_path.name}",
    ]
    checksums_path.write_text("\n".join(checksums_lines) + "\n", encoding="utf-8")

    print(f"Wrote {manifest_path}")
    print(f"Wrote {signature_path}")
    print(f"Wrote {checksums_path}")


if __name__ == "__main__":
    main()
