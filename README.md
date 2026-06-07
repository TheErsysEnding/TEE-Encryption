# TEE Encryption V4.2.1

A cross-platform AES-256-GCM encryption tool with a modern graphical interface.  
Available for **Windows** (EXE), **Android** (APK) — and **macOS coming soon**.

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
| **Android** | [Google Play Store](https://play.google.com/store/apps/details?id=com.tee.encryption&utm_source=emea_Med) |
| **macOS** | Coming soon |

> **Cross-save compatible** — files encrypted on Windows can be decrypted on Android and vice versa. Same password, same keyfile, same result. No format differences between platforms.

---

## Build it yourself (Windows)

**Requirements:**
```
Python 3.10+
pip install flet==0.85.2 flet-desktop==0.85.2 cryptography pyzbar pillow
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

## Credits

Made by **TheErsysEnding**

| Platform | Link |
|----------|------|
| GitHub | [@TheErsysEnding](https://github.com/TheErsysEnding) |
| YouTube | [@TheErsysEnding](https://www.youtube.com/@TheErsysEnding) |
| Linktree | [linktr.ee/theersysending](https://linktr.ee/theersysending) |

---

*If you like this project, feel free to leave a star ⭐*
