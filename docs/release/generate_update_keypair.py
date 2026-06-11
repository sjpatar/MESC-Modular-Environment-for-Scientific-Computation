from __future__ import annotations

import argparse
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main():
    parser = argparse.ArgumentParser(description="Generate the MESC update signing keypair.")
    parser.add_argument(
        "--private-key-out",
        default="release/private/mesc-update-private-key.pem",
        help="Path to write the private signing key PEM.",
    )
    parser.add_argument(
        "--public-key-out",
        default="shared/updater/public/update-public-key.pem",
        help="Path to write the public verification key PEM.",
    )
    args = parser.parse_args()

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path = Path(args.private_key_out)
    public_path = Path(args.public_key_out)
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)

    print(f"Private key written to {private_path}")
    print(f"Public key written to {public_path}")
    print("Keep the private key secret and do not commit it.")


if __name__ == "__main__":
    main()
