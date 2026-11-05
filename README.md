# TEE Encryption V4.2.1

A cross-platform AES-256-GCM encryption tool with a modern graphical interface.  
Available for **Windows** (EXE), **macOS** (DMG / PKG installer), **Linux** and **Android** (APK).

---

## Features

- **AES-256-GCM** authenticated encryption (256-bit key)
- **PBKDF2-HMAC-SHA256** with 200,000 iterations as key derivation
- **Keyfile support** — optional second factor (2FA-style)
- **Text & file** encryption/decryption
- **Large file support** — streaming mode for files > 100 MB
- **QR code** import/export for encrypted text
- **Password generator** built-in
- **9 languages**: English, Deutsch, Español, Français, Türkçe, Русский, العربية, 日本語, 中文
- Dark / Light mode
- Adjustable window opacity & always-on-top mode
- SHA-256 hash display for input and output

---

## Download

| Platform | Link |
|----------|------|
| **Windows** | [Latest Release](../../releases) — just double-click, no install needed |
| **Linux** | See below — one script installs everything automatically |
| **Android** | [Google Play Store](https://play.google.com/store/apps/details?id=com.tee.encryption&utm_source=emea_Med) |
| **macOS** | [Latest Release](../../releases) — `TEE_Encryption_V4.2.1_macOS.dmg` (drag & drop) or `.pkg` (installer). One app for Apple Silicon **and** Intel Macs |

> **Cross-save compatible** — files encrypted on Windows can be decrypted on macOS, Linux or Android and vice versa. Same password, same keyfile, same result. No format differences between platforms.

---

## Linux — Quick Start

No EXE needed. One script handles everything automatically.

**1. Download** `TEE_Encryption_V4.2.1_Linux.tar.gz` from the [Releases](../../releases) page and extract it:
```bash
tar xzf TEE_Encryption_V4.2.1_Linux.tar.gz
cd TEE_Encryption_V4.2.1_Linux
```

**2. Run the installer/launcher:**
```bash
chmod +x start_linux.sh
./start_linux.sh
```

> Alternatively, grab `TEE_Encryption_V4.2.1_GUI.py` and `start_linux.sh` directly from the source and run the same command.

The script will:
- Check Python 3.10+
- Ask to install the required system libraries (one `sudo` prompt):
  `libzbar0` (QR codes) plus `libsecret`, `gtk3`, and the OpenGL/EGL/GLES
  libraries that the GUI needs
- Create a local Python environment (`.venv`)
- Install all Python packages automatically
- Launch the app

Every subsequent start just runs `./start_linux.sh` — packages are already installed, it starts instantly.

**Verified on:** Ubuntu 26.04 LTS with Python 3.14 (full end-to-end: install → encrypt/decrypt → GUI launch).
Package names are also handled for Debian, Fedora, Arch and openSUSE.

---

## macOS — Install

**1. Download** `TEE_Encryption_V4.2.1_macOS.dmg` from the [Releases](../../releases) page.
It is one universal app — it runs natively on Apple Silicon and on Intel Macs (macOS 11 Big Sur or newer).

**2. Install:** open the DMG and drag **TEE Encryption** onto the **Applications** folder.
Prefer a classic installer? Use `TEE_Encryption_V4.2.1_macOS.pkg` instead — it installs the app into Applications.

**3. First start:** the app is not notarized by Apple (that needs a paid developer account), so macOS asks once:
- **macOS 15 Sequoia and newer:** open the app → click **Done** in the warning → open
  **System Settings → Privacy & Security** → scroll down to *"TEE Encryption" was blocked* → **Open Anyway** → confirm.
- **macOS 14 Sonoma and older:** right-click (Control-click) the app → **Open** → **Open**.
- Or in Terminal — on the **installed app**, not on the DMG:
  `xattr -dr com.apple.quarantine "/Applications/TEE Encryption.app"`

The `.pkg` installer is allowed the same way. After that the app starts with a normal double-click.

**Install from Terminal** (if Finder or Gatekeeper get in the way):
```bash
hdiutil verify ~/Downloads/TEE_Encryption_V4.2.1_macOS.dmg      # must end with "VALID"
hdiutil attach -nobrowse ~/Downloads/TEE_Encryption_V4.2.1_macOS.dmg
ditto "/Volumes/TEE Encryption/TEE Encryption.app" "/Applications/TEE Encryption.app"
hdiutil detach "/Volumes/TEE Encryption"
xattr -dr com.apple.quarantine "/Applications/TEE Encryption.app"
open "/Applications/TEE Encryption.app"
```

While the app runs, the **golden TEE lock** sits in the Dock (named *TEE Encryption*, also in the menu bar and
in Cmd+Tab). Right-click it → **Options → Keep in Dock** to pin it there permanently.
Settings (language, theme, opacity …) are stored in `~/Library/Application Support/TEE Encryption/`.

---

## Build it yourself (Windows)

**Requirements:**
```
Python 3.10+
pip install flet==0.85.2 flet-desktop==0.85.2 cryptography qrcode pyzbar pillow
```

**Copy native DLLs** (required for QR reading):
```
Copy libiconv.dll and libzbar-64.dll from .venv\Lib\site-packages\pyzbar\ to the project root
```

**Build command:**
```
flet pack TEE_Encryption_V4.2.1_GUI.py ^
  --name "TEE_Encryption_V4.2.1" ^
  --icon "app_icon.ico" ^
  --add-data "app_icon.ico:." ^
  --hidden-import "pyzbar.pyzbar" ^
  --add-binary "libiconv.dll:pyzbar" ^
  --add-binary "libzbar-64.dll:pyzbar"
```

The EXE will be in the `dist\` folder.

---

## Build it yourself (macOS)

**Requirements:** a Mac with [Xcode](https://apps.apple.com/app/xcode/id497799835) (start it once to accept the
licence), CocoaPods (`brew install cocoapods`) and Python 3.10+.

**Build command:**
```bash
./macos/build_macos.sh
```

The script sets up everything else by itself — a local Python environment with `flet build` and, on the first
run, the matching Flutter SDK (about 1.5 GB; the first build takes 10–20 minutes). Result:

| File | What it is |
|------|------------|
| `dist/TEE_Encryption_V4.2.1_macOS.dmg` | Disk image — drag the app into Applications |
| `dist/TEE_Encryption_V4.2.1_macOS.pkg` | Classic installer — installs the app into Applications |
| `dist/TEE Encryption.app` | The app itself |
| `dist/SHA256SUMS.txt` | SHA-256 checksums of the installers |

What it does:
- `flet build macos` turns the app into **one native macOS app with embedded Python** — the Dock therefore shows a
  single icon: the golden lock, named *TEE Encryption*
- the app icon, the DMG background and the installer logo are generated from `TEE_encryption_GOLD.png`
  (`macos/make_assets.py`)
- `macos/universal_fixup.py` makes every native library universal (Apple Silicon + Intel), re-signs the app and
  verifies it
- options: `--clean` (fresh build), `--no-pkg` (DMG only), `--no-dmg-layout` (skip the Finder window design)

**Automatic builds:** the GitHub Actions workflow [`build-macos.yml`](.github/workflows/build-macos.yml) builds the
DMG and PKG on a real Mac for every change, installs both, launches the app (natively and as Intel build under
Rosetta 2) and checks that it runs as a normal app with its Dock icon. The installers are attached to each run,
and pull requests refresh an unpublished draft release *"macOS test build"* (only visible to people with write
access — publish it with one click). Pushing a tag such as `v4.2.1` attaches them to the GitHub release.

---

## Encryption Details

| Parameter         | Value                        |
|-------------------|------------------------------|
| Algorithm         | AES-256-GCM                  |
| Key derivation    | PBKDF2-HMAC-SHA256           |
| Iterations        | 200,000                      |
| Salt              | 16 bytes random (per file)   |
| IV / Nonce        | 12 bytes random (per file)   |
| Keyfile (optional)| SHA-256 hash appended to pw  |

Fresh salt and IV are generated for every encryption operation — no nonce reuse.

---

## Licence

TEE Encryption is MIT-licensed — see [`LICENSE`](LICENSE).

Two LGPL-licensed libraries ship with the Windows build (`libzbar-64.dll` and `libiconv.dll`, both
taken unmodified from `pyzbar`). Their licence text, copyright holders and sources are documented in
[`THIRD-PARTY-LICENSES.md`](THIRD-PARTY-LICENSES.md), along with everything else this project builds on.
The macOS app embeds the Flutter engine, CPython and the Python packages listed there as well
(QR reading on macOS uses zxing-cpp instead of ZBar).

## Credits

Made by **TheErsysEnding**

| Platform | Link |
|----------|------|
| GitHub | [@TheErsysEnding](https://github.com/TheErsysEnding) |
| YouTube | [@TheErsysEnding](https://www.youtube.com/@TheErsysEnding) |
| Linktree | [linktr.ee/theersysending](https://linktr.ee/theersysending) |

---

*If you like this project, feel free to leave a star ⭐*
