# MESC Release Process

This repository now includes a signed desktop release flow for Windows.

## One-time setup

1. Generate the update signing keypair:

```bash
.venv\Scripts\python.exe scripts\release\generate_update_keypair.py
```

2. Keep `release/private/mesc-update-private-key.pem` secret.
3. Commit `shared/updater/public/update-public-key.pem`.
4. Add the private key PEM to GitHub Actions as the `MESC_UPDATE_PRIVATE_KEY_PEM` secret.

## Local Windows release build

```powershell
.\packaging\windows\build_windows_release.ps1 -Version 1.0.0
```

This produces:

- `dist\MESC\` from PyInstaller
- `dist\MESC-Setup-<version>.exe` from Inno Setup

To generate signed update metadata too:

```powershell
.\packaging\windows\build_windows_release.ps1 `
  -Version 1.0.0 `
  -PrivateKeyPath .\release\private\mesc-update-private-key.pem `
  -ReleaseBaseUrl https://github.com/<owner>/<repo>/releases/download/v1.0.0 `
  -ReleasePageUrl https://github.com/<owner>/<repo>/releases/tag/v1.0.0
```

That also produces:

- `dist\release\release-manifest.json`
- `dist\release\release-manifest.json.sig`
- `dist\release\SHA256SUMS.txt`

## GitHub Releases

The workflow in `.github/workflows/release.yml` runs on `v*` tags and publishes:

- the Windows installer
- the signed release manifest
- the detached signature
- the SHA-256 checksum list

## App update behavior

- MESC checks `release-manifest.json`
- verifies the detached signature with the bundled public key
- selects the current platform installer
- downloads it
- verifies the SHA-256 hash
- launches the installer

If the public key has not been configured yet, update checks stay disabled instead of trusting unsigned metadata.
