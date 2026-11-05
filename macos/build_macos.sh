#!/bin/bash
# ==========================================================
#   TEE Encryption V4.2.1 - macOS Build (App + Installer)
#
#   Baut "TEE Encryption.app" als Universal-App (Apple Silicon
#   + Intel) mit dem goldenen TEE-Logo als App-/Dock-Icon und
#   erzeugt daraus die Installer-Dateien:
#
#     dist/TEE_Encryption_V4.2.1_macOS.dmg  (oeffnen -> App in
#                                            "Programme" ziehen)
#     dist/TEE_Encryption_V4.2.1_macOS.pkg  (klassischer Installer)
#     dist/TEE Encryption.app               (die App selbst)
#     dist/SHA256SUMS.txt
#
#   Voraussetzungen: macOS 13+, Xcode (aus dem App Store, einmal
#   gestartet), CocoaPods (brew install cocoapods), Python 3.10+.
#   Das Flutter-SDK laedt `flet build` beim ersten Mal selbst.
#
#   Aufruf:  ./macos/build_macos.sh [--clean] [--no-pkg] [--no-dmg-layout]
# ==========================================================

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

step() { echo -e "\n${CYAN}==> $*${NC}"; }
ok()   { echo -e "${GREEN}[OK] $*${NC}"; }
warn() { echo -e "${YELLOW}[WARNUNG] $*${NC}"; }
fail() { echo -e "${RED}[FEHLER] $*${NC}" >&2; exit 1; }

# ----------------------------------------------------------
# Optionen
# ----------------------------------------------------------
CLEAN=false
BUILD_PKG=true
DMG_LAYOUT=true
for arg in "$@"; do
    case "$arg" in
        --clean)         CLEAN=true ;;
        --no-pkg)        BUILD_PKG=false ;;
        --no-dmg-layout) DMG_LAYOUT=false ;;
        -h|--help)       sed -n '2,24p' "$0"; exit 0 ;;
        *)               fail "Unbekannte Option: $arg (siehe --help)" ;;
    esac
done

# ----------------------------------------------------------
# Pfade & Projektdaten
# ----------------------------------------------------------
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MACOS_DIR="$ROOT_DIR/macos"
BUILD_DIR="${TEE_BUILD_DIR:-$ROOT_DIR/build/macos}"
DIST_DIR="${TEE_DIST_DIR:-$ROOT_DIR/dist}"
PYTHON="${PYTHON:-python3}"

APP_NAME="TEE Encryption"
BUNDLE_ID="com.tee.encryption"
APP_SCRIPT="$ROOT_DIR/TEE_Encryption_V4.2.1_GUI.py"
LOGO="$ROOT_DIR/TEE_encryption_GOLD.png"
PYPROJECT="$MACOS_DIR/pyproject.toml"
MIN_MACOS="11.0"

VERSION="$(sed -nE 's/^version *= *"([^"]+)".*/\1/p' "$PYPROJECT" | head -1)"
FLET_VERSION="$(sed -nE 's/.*"flet==([^"]+)".*/\1/p' "$PYPROJECT" | head -1)"
[ -n "$VERSION" ] || fail "Version nicht in $PYPROJECT gefunden."
[ -n "$FLET_VERSION" ] || fail "flet-Version (flet==x.y.z) nicht in $PYPROJECT gefunden."

DMG_NAME="TEE_Encryption_V${VERSION}_macOS.dmg"
PKG_NAME="TEE_Encryption_V${VERSION}_macOS.pkg"

# DMG-Fensterlayout (Punkte) - passend zu macos/make_assets.py
DMG_WINDOW_W=660
DMG_WINDOW_H=428
DMG_APP_POS="165, 190"
DMG_APPS_POS="495, 190"

START_TIME=$(date +%s)

echo ""
echo -e "${CYAN}=========================================="
echo -e "   TEE Encryption V${VERSION} - macOS Build"
echo -e "==========================================${NC}"

# ----------------------------------------------------------
# 1. Voraussetzungen pruefen
# ----------------------------------------------------------
step "Pruefe Voraussetzungen"
[ "$(uname -s)" = "Darwin" ] || fail "Dieses Skript laeuft nur auf macOS."
[ -f "$APP_SCRIPT" ] || fail "App-Skript fehlt: $APP_SCRIPT"
[ -f "$LOGO" ] || fail "Logo fehlt: $LOGO"

if ! xcodebuild -version >/dev/null 2>&1; then
    fail "Xcode wurde nicht gefunden. Bitte Xcode aus dem App Store installieren,
       einmal starten und danach ausfuehren:
         sudo xcode-select -s /Applications/Xcode.app/Contents/Developer"
fi
ok "$(xcodebuild -version | head -1)"

if ! command -v pod >/dev/null 2>&1; then
    fail "CocoaPods fehlt. Installieren mit:  brew install cocoapods"
fi
ok "CocoaPods $(pod --version 2>/dev/null)"

command -v "$PYTHON" >/dev/null 2>&1 || fail "Python 3.10+ fehlt (python.org oder: brew install python)."
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
    || fail "Python $("$PYTHON" -V 2>&1) ist zu alt - mindestens Python 3.10 benoetigt."
ok "$("$PYTHON" -V 2>&1)"

for tool in hdiutil codesign lipo otool sips iconutil tiffutil pkgbuild productbuild ditto unzip curl; do
    command -v "$tool" >/dev/null 2>&1 || fail "Systemwerkzeug fehlt: $tool"
done
ok "Systemwerkzeuge vorhanden"

if [ "$CLEAN" = true ]; then
    step "Raeume alten Build auf"
    rm -rf "$BUILD_DIR"
fi
mkdir -p "$BUILD_DIR" "$DIST_DIR"

# ----------------------------------------------------------
# 2. Build-Umgebung (Python venv mit flet-cli)
# ----------------------------------------------------------
step "Richte Build-Umgebung ein (flet $FLET_VERSION)"
VENV="$BUILD_DIR/venv"
if [ ! -x "$VENV/bin/python" ]; then
    "$PYTHON" -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --disable-pip-version-check --quiet --upgrade pip
"$VENV/bin/python" -m pip install --disable-pip-version-check --quiet \
    "flet[cli]==$FLET_VERSION" "pillow>=12"
ok "flet-cli $FLET_VERSION installiert"

# ----------------------------------------------------------
# 3. Grafiken: App-Icon, DMG-Hintergrund, Volume-Icon
# ----------------------------------------------------------
step "Erzeuge App-Icon und Installer-Grafiken aus dem Logo"
ASSETS="$BUILD_DIR/assets"
rm -rf "$ASSETS"
"$VENV/bin/python" "$MACOS_DIR/make_assets.py" "$LOGO" "$ASSETS" --version "$VERSION"
tiffutil -cathidpicheck "$ASSETS/dmg_background.png" "$ASSETS/dmg_background@2x.png" \
    -out "$ASSETS/dmg_background.tiff" >/dev/null

# .icns (fuer das DMG-Laufwerk) aus dem App-Icon
ICONSET="$ASSETS/TEE_Encryption.iconset"
mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
    sips -z "$size" "$size" "$ASSETS/icon.png" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z "$double" "$double" "$ASSETS/icon.png" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$ASSETS/TEE_Encryption.icns"
ok "Grafiken erstellt"

# ----------------------------------------------------------
# 4. Flet-Projekt zusammenstellen
# ----------------------------------------------------------
step "Stelle Flet-Projekt zusammen"
PROJECT="$BUILD_DIR/project"
rm -rf "$PROJECT/src"
mkdir -p "$PROJECT/src/assets"
cp "$PYPROJECT" "$PROJECT/pyproject.toml"
cp "$APP_SCRIPT" "$PROJECT/src/main.py"
cp "$ASSETS/icon.png" "$PROJECT/src/assets/icon.png"
ok "Projekt: $PROJECT"

# ----------------------------------------------------------
# 5. Flet-Build-Vorlage (offizielle Vorlage + 1 Korrektur)
#    Die Vorlage legt beim Start einen Datenordner in ~/Documents an.
#    macOS fragt dafuer "Zugriff auf Dokumente erlauben?" - und lehnt man
#    ab, startet die App nicht. Wir verwenden stattdessen
#    ~/Library/Application Support (ohne Rueckfrage, Apple-Standard).
# ----------------------------------------------------------
step "Bereite Flet-Build-Vorlage vor"
TPL_ROOT="$BUILD_DIR/template-$FLET_VERSION"
TPL_DIR="$TPL_ROOT/build"
if [ ! -f "$TPL_DIR/cookiecutter.json" ]; then
    rm -rf "$TPL_ROOT"
    mkdir -p "$TPL_ROOT"
    curl -fsSL --retry 5 --retry-delay 3 -o "$TPL_ROOT/template.zip" \
        "https://github.com/flet-dev/flet/releases/download/v${FLET_VERSION}/flet-build-template.zip"
    (cd "$TPL_ROOT" && unzip -q template.zip && rm -f template.zip)
fi
"$VENV/bin/python" - "$TPL_DIR" <<'PY'
import pathlib
import sys

main_dart = pathlib.Path(sys.argv[1]) / "{{cookiecutter.out_dir}}" / "lib" / "main.dart"
src = main_dart.read_text(encoding="utf-8")
old = "path_provider.getApplicationDocumentsDirectory()"
new = "path_provider.getApplicationSupportDirectory()"
if src.count(old) == 1:
    main_dart.write_text(src.replace(old, new), encoding="utf-8")
    print("Vorlage angepasst: Datenordner -> ~/Library/Application Support")
elif old not in src and new in src:
    print("Vorlage bereits angepasst")
else:
    sys.exit("[FEHLER] Unerwarteter Aufbau von lib/main.dart in der Flet-Vorlage - "
             "bitte macos/build_macos.sh an die neue flet-Version anpassen.")
PY
ok "Vorlage: $TPL_DIR"

# ----------------------------------------------------------
# 6. App bauen (flet build macos -> Flutter/Xcode)
# ----------------------------------------------------------
step "Baue ${APP_NAME}.app (flet build macos) - beim ersten Mal 10-20 Minuten"
APP_OUT="$BUILD_DIR/app"
rm -rf "$APP_OUT"
FLET_VERBOSE="${TEE_FLET_VERBOSE:--v}"
(
    cd "$PROJECT"
    # shellcheck disable=SC2086  # FLET_VERBOSE darf leer sein oder "-v"/"-vv" enthalten
    PYTHONUNBUFFERED=1 "$VENV/bin/flet" build macos \
        --yes --no-rich-output $FLET_VERBOSE \
        --template "$TPL_DIR" \
        --output "$APP_OUT"
) 2>&1 | tee "$BUILD_DIR/flet-build.log"

APP="$APP_OUT/$APP_NAME.app"
[ -d "$APP" ] || fail "Build-Ergebnis fehlt: $APP (Details: $BUILD_DIR/flet-build.log)"
ok "App gebaut: $APP"

# ----------------------------------------------------------
# 7. App pruefen: Name, Bundle-ID, Version, Icon
# ----------------------------------------------------------
step "Pruefe App-Bundle"
PLIST="$APP/Contents/Info.plist"
plist_get() { /usr/libexec/PlistBuddy -c "Print :$1" "$PLIST" 2>/dev/null || true; }

[ "$(plist_get CFBundleIdentifier)" = "$BUNDLE_ID" ] \
    || fail "CFBundleIdentifier ist '$(plist_get CFBundleIdentifier)' statt '$BUNDLE_ID'"
[ "$(plist_get CFBundleName)" = "$APP_NAME" ] \
    || fail "CFBundleName ist '$(plist_get CFBundleName)' statt '$APP_NAME'"
[ "$(plist_get CFBundleDisplayName)" = "$APP_NAME" ] \
    || fail "CFBundleDisplayName ist '$(plist_get CFBundleDisplayName)' statt '$APP_NAME'"
[ "$(plist_get CFBundleShortVersionString)" = "$VERSION" ] \
    || fail "Version ist '$(plist_get CFBundleShortVersionString)' statt '$VERSION'"
ICON_FILE="$(plist_get CFBundleIconFile)"
ICON_FILE="${ICON_FILE:-AppIcon}"
ICNS="$APP/Contents/Resources/${ICON_FILE%.icns}.icns"
[ -f "$ICNS" ] || fail "App-Icon fehlt im Bundle: $ICNS"
ok "Name: $(plist_get CFBundleName) | ID: $(plist_get CFBundleIdentifier) | Version: $(plist_get CFBundleShortVersionString) ($(plist_get CFBundleVersion))"

# Ist das App-Icon wirklich das TEE-Logo (und nicht das Flet-Standard-Icon)?
sips -s format png "$ICNS" --out "$BUILD_DIR/built_app_icon.png" >/dev/null
"$VENV/bin/python" - "$BUILD_DIR/built_app_icon.png" "$ASSETS/icon.png" <<'PY'
import sys
from PIL import Image, ImageChops, ImageStat

def norm(path):
    im = Image.open(path).convert("RGBA").resize((64, 64), Image.LANCZOS)
    bg = Image.new("RGBA", im.size, (128, 128, 128, 255))
    bg.alpha_composite(im)
    return bg.convert("RGB")

diff = ImageStat.Stat(ImageChops.difference(norm(sys.argv[1]), norm(sys.argv[2]))).mean
score = sum(diff) / len(diff)
print(f"Icon-Abweichung zum TEE-Logo: {score:.2f} (0 = identisch, anderes Icon > 40)")
sys.exit(0 if score < 15 else "[FEHLER] Das App-Icon ist nicht das TEE-Logo!")
PY
ok "App-Icon = TEE-Logo"

# ----------------------------------------------------------
# 8. Universal-Pruefung (arm64 + x86_64) und Signatur
# ----------------------------------------------------------
step "Mache alle Bibliotheken universal (Apple Silicon + Intel) und pruefe die Signatur"
EMBEDDED_PY="$( (find "$APP" -name '*.cpython-3*-darwin.so' -print -quit 2>/dev/null || true) \
    | sed -nE 's/.*cpython-3([0-9]+)-darwin\.so$/3.\1/p')"
EMBEDDED_PY="${EMBEDDED_PY:-3.12}"
echo "Eingebettetes Python: $EMBEDDED_PY"
"$VENV/bin/python" "$MACOS_DIR/universal_fixup.py" "$APP" "$BUILD_DIR/universal" \
    --python-version "$EMBEDDED_PY" --min-macos "$MIN_MACOS"
ok "Universal-App (arm64 + x86_64), Signatur gueltig"

rm -rf "$DIST_DIR/$APP_NAME.app"
ditto "$APP" "$DIST_DIR/$APP_NAME.app"

# ----------------------------------------------------------
# 9. DMG (oeffnen -> App auf "Programme" ziehen)
# ----------------------------------------------------------
run_with_timeout() {
    local secs=$1; shift
    "$@" &
    local pid=$!
    ( sleep "$secs"; kill -TERM "$pid" 2>/dev/null ) &
    local watchdog=$!
    local rc=0
    wait "$pid" || rc=$?
    kill "$watchdog" 2>/dev/null || true
    wait "$watchdog" 2>/dev/null || true
    return $rc
}

detach_volume() {
    local target=$1
    for _ in 1 2 3 4 5; do
        if hdiutil detach "$target" -quiet 2>/dev/null; then
            return 0
        fi
        sleep 2
    done
    hdiutil detach "$target" -force -quiet 2>/dev/null || true
}

step "Erzeuge DMG: $DMG_NAME"
DMG_STAGE="$BUILD_DIR/dmg-stage"
RW_DMG="$BUILD_DIR/tmp-rw.dmg"
rm -rf "$DMG_STAGE" "$RW_DMG"
mkdir -p "$DMG_STAGE/.background"
ditto "$APP" "$DMG_STAGE/$APP_NAME.app"
ln -s /Applications "$DMG_STAGE/Applications"
cp "$ASSETS/dmg_background.tiff" "$DMG_STAGE/.background/background.tiff"

if [ -d "/Volumes/$APP_NAME" ]; then
    warn "Ein Laufwerk '/Volumes/$APP_NAME' ist bereits eingebunden - wird ausgeworfen."
    detach_volume "/Volumes/$APP_NAME"
fi

STAGE_MB=$(du -sm "$DMG_STAGE" | awk '{print $1}')
hdiutil create -srcfolder "$DMG_STAGE" -volname "$APP_NAME" -fs HFS+ \
    -format UDRW -size "$((STAGE_MB + 60))m" -ov "$RW_DMG" >/dev/null

ATTACH_OUT="$(hdiutil attach -readwrite -noverify -noautoopen "$RW_DMG")"
MOUNT_DIR="$(echo "$ATTACH_OUT" | grep -E '/Volumes/' | sed -E 's|^.*(/Volumes/.*)$|\1|' | tail -1)"
[ -d "$MOUNT_DIR" ] || fail "DMG konnte nicht eingebunden werden:\n$ATTACH_OUT"
echo "Eingebunden: $MOUNT_DIR"

# eigenes Laufwerks-Icon: erst ins eingebundene Image kopieren (hdiutil -srcfolder
# uebernimmt .VolumeIcon.icns nicht) und dann das "Custom Icon"-Flag setzen
cp "$ASSETS/TEE_Encryption.icns" "$MOUNT_DIR/.VolumeIcon.icns"
if command -v SetFile >/dev/null 2>&1; then
    SetFile -c icnC "$MOUNT_DIR/.VolumeIcon.icns" || true
    SetFile -a C "$MOUNT_DIR" || true
else
    xattr -wx com.apple.FinderInfo \
        "0000000000000000040000000000000000000000000000000000000000000000" "$MOUNT_DIR" || true
fi
[ -f "$MOUNT_DIR/.VolumeIcon.icns" ] || fail "Laufwerks-Icon konnte nicht ins DMG kopiert werden"

if [ "$DMG_LAYOUT" = true ]; then
    LAYOUT_SCRIPT="$BUILD_DIR/dmg-layout.applescript"
    cat > "$LAYOUT_SCRIPT" <<APPLESCRIPT
on run argv
    set volName to item 1 of argv
    tell application "Finder"
        tell disk volName
            open
            set current view of container window to icon view
            set toolbar visible of container window to false
            set statusbar visible of container window to false
            set the bounds of container window to {200, 120, $((200 + DMG_WINDOW_W)), $((120 + DMG_WINDOW_H))}
            set viewOptions to the icon view options of container window
            set arrangement of viewOptions to not arranged
            set icon size of viewOptions to 128
            set text size of viewOptions to 13
            set background picture of viewOptions to file ".background:background.tiff"
            set position of item "$APP_NAME.app" of container window to {$DMG_APP_POS}
            set position of item "Applications" of container window to {$DMG_APPS_POS}
            close
            open
            update without registering applications
            delay 2
            close
        end tell
    end tell
end run
APPLESCRIPT
    if run_with_timeout 120 osascript "$LAYOUT_SCRIPT" "$APP_NAME"; then
        # Finder schreibt .DS_Store verzoegert
        for _ in $(seq 1 20); do
            [ -f "$MOUNT_DIR/.DS_Store" ] && break
            sleep 1
        done
        if [ -f "$MOUNT_DIR/.DS_Store" ]; then
            ok "DMG-Fenster gestaltet (Hintergrund, Pfeil, Icon-Positionen)"
        else
            warn "Finder hat das Fensterlayout nicht gespeichert - DMG funktioniert trotzdem."
        fi
    else
        warn "Finder-Layout nicht moeglich (keine Automations-Erlaubnis?) - DMG funktioniert trotzdem."
    fi
fi

rm -rf "$MOUNT_DIR/.fseventsd" "$MOUNT_DIR/.Trashes" 2>/dev/null || true
chmod -Rf go-w "$MOUNT_DIR" 2>/dev/null || true
sync
detach_volume "$MOUNT_DIR"

rm -f "$DIST_DIR/$DMG_NAME"
hdiutil convert "$RW_DMG" -format UDZO -imagekey zlib-level=9 -o "$DIST_DIR/$DMG_NAME" >/dev/null
rm -f "$RW_DMG"
hdiutil verify "$DIST_DIR/$DMG_NAME" >/dev/null 2>&1 || fail "DMG-Pruefung fehlgeschlagen"
ok "DMG: $DIST_DIR/$DMG_NAME ($(du -h "$DIST_DIR/$DMG_NAME" | awk '{print $1}'))"

# ----------------------------------------------------------
# 10. PKG (klassischer Installer -> /Programme)
# ----------------------------------------------------------
if [ "$BUILD_PKG" = true ]; then
    step "Erzeuge PKG-Installer: $PKG_NAME"
    PKG_WORK="$BUILD_DIR/pkg"
    PKG_ROOT="$PKG_WORK/root"
    rm -rf "$PKG_WORK"
    mkdir -p "$PKG_ROOT" "$PKG_WORK/resources"
    ditto "$APP" "$PKG_ROOT/$APP_NAME.app"
    cp "$ASSETS/installer_logo.png" "$PKG_WORK/resources/installer_logo.png"

    # Nicht "relocatable": sonst installiert macOS ein Update dorthin, wo zufaellig
    # schon eine Kopie mit derselben Bundle-ID liegt, statt nach /Programme.
    pkgbuild --analyze --root "$PKG_ROOT" "$PKG_WORK/components.plist" >/dev/null
    /usr/libexec/PlistBuddy -c "Set :0:BundleIsRelocatable false" "$PKG_WORK/components.plist"

    pkgbuild --root "$PKG_ROOT" \
        --component-plist "$PKG_WORK/components.plist" \
        --identifier "$BUNDLE_ID.pkg" \
        --version "$VERSION" \
        --install-location /Applications \
        "$PKG_WORK/TEE_Encryption-component.pkg" >/dev/null

    cat > "$PKG_WORK/distribution.xml" <<XML
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
    <title>TEE Encryption $VERSION</title>
    <organization>com.tee</organization>
    <background file="installer_logo.png" mime-type="image/png" alignment="bottomleft" scaling="none"/>
    <background-darkAqua file="installer_logo.png" mime-type="image/png" alignment="bottomleft" scaling="none"/>
    <options customize="never" require-scripts="false" hostArchitectures="arm64,x86_64"/>
    <domains enable_localSystem="true"/>
    <volume-check>
        <allowed-os-versions>
            <os-version min="$MIN_MACOS"/>
        </allowed-os-versions>
    </volume-check>
    <choices-outline>
        <line choice="default">
            <line choice="$BUNDLE_ID.pkg"/>
        </line>
    </choices-outline>
    <choice id="default"/>
    <choice id="$BUNDLE_ID.pkg" visible="false">
        <pkg-ref id="$BUNDLE_ID.pkg"/>
    </choice>
    <pkg-ref id="$BUNDLE_ID.pkg" version="$VERSION" onConclusion="none">TEE_Encryption-component.pkg</pkg-ref>
</installer-gui-script>
XML

    rm -f "$DIST_DIR/$PKG_NAME"
    productbuild --distribution "$PKG_WORK/distribution.xml" \
        --package-path "$PKG_WORK" \
        --resources "$PKG_WORK/resources" \
        "$DIST_DIR/$PKG_NAME" >/dev/null

    pkgutil --payload-files "$PKG_WORK/TEE_Encryption-component.pkg" > "$PKG_WORK/payload.txt"
    grep -q "$APP_NAME.app/Contents/MacOS/$APP_NAME" "$PKG_WORK/payload.txt" \
        || fail "PKG enthaelt die App nicht"
    ok "PKG: $DIST_DIR/$PKG_NAME ($(du -h "$DIST_DIR/$PKG_NAME" | awk '{print $1}'))"
fi

# ----------------------------------------------------------
# 11. Pruefsummen & Zusammenfassung
# ----------------------------------------------------------
step "Pruefsummen"
(
    cd "$DIST_DIR"
    files=("$DMG_NAME")
    [ "$BUILD_PKG" = true ] && files+=("$PKG_NAME")
    shasum -a 256 "${files[@]}" | tee SHA256SUMS.txt
)

ELAPSED=$(( $(date +%s) - START_TIME ))
echo ""
echo -e "${GREEN}=========================================="
echo -e "   Fertig in $((ELAPSED / 60)) min $((ELAPSED % 60)) s"
echo -e "==========================================${NC}"
echo "  DMG:  $DIST_DIR/$DMG_NAME"
[ "$BUILD_PKG" = true ] && echo "  PKG:  $DIST_DIR/$PKG_NAME"
echo "  App:  $DIST_DIR/$APP_NAME.app"
echo ""
