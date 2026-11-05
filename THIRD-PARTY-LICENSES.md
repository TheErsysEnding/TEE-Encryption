# Third-party licences

TEE Encryption itself is MIT-licensed (see `LICENSE`). This file lists everything else that is
either **shipped inside this repository** or pulled in at build time, together with its licence and
where it came from.

---

## Redistributed in this repository

These two files sit in the project root and are copied into the Windows build. Both are unmodified
binaries taken from the `pyzbar` package (`.venv\Lib\site-packages\pyzbar\`), which vendors them for
its Windows wheels.

### libzbar-64.dll — ZBar Barcode Reader

| | |
|---|---|
| Licence | **GNU LGPL, version 2.1 or later** — full text in [`LICENSES/LGPL-2.1.txt`](LICENSES/LGPL-2.1.txt) |
| Copyright | © 2007–2009 Jeff Brown and contributors |
| Upstream | https://github.com/mchehab/zbar (maintained fork) · originally http://zbar.sourceforge.net/ |
| Windows build | ZBarWin64 — https://github.com/dani4/ZBarWin64 |
| Shipped via | pyzbar — https://github.com/NaturalHistoryMuseum/pyzbar |

Used for reading QR codes. The library is dynamically linked and unmodified; you may replace the DLL
with your own build of ZBar, which is what the LGPL asks for.

### libiconv.dll — GNU libiconv

| | |
|---|---|
| Licence | **GNU LGPL, version 2.1 or later** — full text in [`LICENSES/LGPL-2.1.txt`](LICENSES/LGPL-2.1.txt) |
| Copyright | © 1999–2009 Free Software Foundation, Inc. |
| Upstream | https://www.gnu.org/software/libiconv/ |
| Shipped via | pyzbar — https://github.com/NaturalHistoryMuseum/pyzbar |

Character-set conversion, required by ZBar on Windows. Dynamically linked and unmodified.

**Note on the LGPL:** both libraries are used as separate, dynamically linked DLLs and are not
modified. Anyone may replace them with their own build by dropping a different DLL of the same name
next to the executable. The complete licence text is included above; the sources are available from
the upstream links.

---

## Installed at build time (not redistributed here)

These are pulled in with `pip` and end up inside the packaged executable. They are listed for
transparency; each project's own licence text ships with its package.

| Package | Licence | Project |
|---|---|---|
| flet | Apache-2.0 | https://github.com/flet-dev/flet |
| cryptography | Apache-2.0 **or** BSD-3-Clause | https://github.com/pyca/cryptography |
| qrcode | BSD-3-Clause | https://github.com/lincolnloop/python-qrcode |
| pyzbar | MIT | https://github.com/NaturalHistoryMuseum/pyzbar |
| Pillow | MIT-CMU (formerly HPND) | https://github.com/python-pillow/Pillow |
| PyInstaller | GPL-2.0-or-later **with** a bootloader exception that permits proprietary and MIT-licensed output | https://github.com/pyinstaller/pyinstaller |
| zxing-cpp (fallback QR reader; used by the macOS app) | Apache-2.0 | https://github.com/zxing-cpp/zxing-cpp |

`cryptography` in turn links **OpenSSL** (Apache-2.0), which its own wheels bundle and document.

---

## Bundled inside the macOS app

`flet build macos` produces a self-contained `TEE Encryption.app`: it embeds the Flutter engine, a CPython
runtime and the Python packages below. Nothing is modified; each Python package's own licence text ships inside
the app bundle (in its `*.dist-info` folder), and Flutter collects the licences of the engine and of all Dart
packages of the Flet client into `NOTICES.Z` inside the app.

| Component | Licence | Project |
|---|---|---|
| Flutter engine & framework | BSD-3-Clause | https://github.com/flutter/flutter |
| Flet (Flutter client + Python package, build template) | Apache-2.0 | https://github.com/flet-dev/flet |
| serious_python (embedded Python runtime for Flutter) | Apache-2.0 | https://github.com/flet-dev/serious-python |
| CPython 3.12 | PSF License 2.0 | https://www.python.org/ |
| zxing-cpp — QR code reading in the macOS app | Apache-2.0 | https://github.com/zxing-cpp/zxing-cpp |
| cryptography (bundles OpenSSL, Apache-2.0) | Apache-2.0 **or** BSD-3-Clause | https://github.com/pyca/cryptography |
| cffi / pycparser | MIT-0 / BSD-3-Clause | https://github.com/python-cffi/cffi · https://github.com/eliben/pycparser |
| Pillow | MIT-CMU | https://github.com/python-pillow/Pillow |
| qrcode | BSD-3-Clause | https://github.com/lincolnloop/python-qrcode |
| msgpack | Apache-2.0 | https://github.com/msgpack/msgpack-python |
| httpx / httpcore | BSD-3-Clause | https://github.com/encode/httpx |
| h11 / anyio | MIT | https://github.com/python-hyper/h11 · https://github.com/agronholm/anyio |
| idna | BSD-3-Clause | https://github.com/kjd/idna |
| certifi (CA certificate bundle) | MPL-2.0 | https://github.com/certifi/python-certifi |
| oauthlib | BSD-3-Clause | https://github.com/oauthlib/oauthlib |
| repath / six | MIT | https://github.com/nickcoutsos/python-repath · https://github.com/benjaminp/six |

Pillow's macOS wheels bundle image libraries (libjpeg-turbo, libpng, zlib-ng, libtiff, libwebp, libavif, LCMS2,
FreeType, HarfBuzz, OpenJPEG, Brotli, liblzma, libxcb/libXau). Their licences are collected in Pillow's licence
file, which ships inside the app (`pillow-<version>.dist-info/licenses/LICENSE`).

The build uses Flet's official build template with one change, applied by `macos/build_macos.sh`: the app keeps
its data folder in `~/Library/Application Support` instead of `~/Documents` (so macOS does not ask for access to
the Documents folder). The ZBar/libiconv DLLs listed above are **not** part of the macOS app.

---

If you believe something is missing or attributed incorrectly, please open an issue — the aim here is
to credit everything properly.
