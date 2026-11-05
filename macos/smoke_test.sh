#!/bin/bash
# ==========================================================
#   TEE Encryption - macOS Smoke-Test (fuer CI gedacht)
#
#   Installiert die gebauten Installer auf DIESEM Mac, startet
#   die App und prueft:
#     - PKG installiert die App nach /Applications
#     - DMG enthaelt App + "Programme"-Verknuepfung + Laufwerks-Icon
#     - App laeuft als normale App MIT Dock-Symbol
#       (lsappinfo type="Foreground"), Name "TEE Encryption"
#     - der Python-Teil startet (Einstellungsordner wird angelegt),
#       kein Traceback im Python-Log
#     - native Module (cryptography, Pillow, zxing-cpp) sind geladen
#     - keine Rueckfrage "Zugriff auf Dokumente" (~/Documents unberuehrt)
#     - zweiter Start als Intel-App unter Rosetta 2 (x86_64-Teil)
#   Screenshots + Logs: dist/smoke-test/
#
#   ACHTUNG: ersetzt "/Applications/TEE Encryption.app" und loescht
#   die Einstellungen der App. Aufruf: ./macos/smoke_test.sh
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
fail() { echo -e "${RED}[FEHLER] $*${NC}" >&2; FAILED=true; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${TEE_DIST_DIR:-$ROOT_DIR/dist}"
OUT="$DIST_DIR/smoke-test"
APP_NAME="TEE Encryption"
BUNDLE_ID="com.tee.encryption"
INSTALLED="/Applications/$APP_NAME.app"
EXE_PATTERN="$APP_NAME.app/Contents/MacOS/$APP_NAME"
SUPPORT_DIR="$HOME/Library/Application Support/TEE Encryption"
CACHE_DIR="$HOME/Library/Caches/$BUNDLE_ID"
CONSOLE_LOG="$CACHE_DIR/console.log"
FAILED=false

mkdir -p "$OUT"
DMG="$(ls "$DIST_DIR"/TEE_Encryption_V*_macOS.dmg 2>/dev/null | head -1 || true)"
PKG="$(ls "$DIST_DIR"/TEE_Encryption_V*_macOS.pkg 2>/dev/null | head -1 || true)"
[ -n "$DMG" ] || { echo "DMG nicht gefunden in $DIST_DIR"; exit 1; }

app_pids() { pgrep -f "$EXE_PATTERN" || true; }

stop_app() {
    local pids
    pids="$(app_pids)"
    [ -z "$pids" ] && return 0
    # shellcheck disable=SC2086  # mehrere PIDs -> Aufteilen ist gewollt
    kill $pids 2>/dev/null || true
    for _ in $(seq 1 15); do
        [ -z "$(app_pids)" ] && return 0
        sleep 1
    done
    # shellcheck disable=SC2046  # mehrere PIDs -> Aufteilen ist gewollt
    kill -9 $(app_pids) 2>/dev/null || true
}

# ----------------------------------------------------------
# 1. PKG-Installer
# ----------------------------------------------------------
if [ -n "$PKG" ]; then
    step "PKG installieren: $(basename "$PKG")"
    stop_app
    sudo rm -rf "$INSTALLED"
    sudo installer -pkg "$PKG" -target / | tee "$OUT/pkg-install.log"
    if [ -x "$INSTALLED/Contents/MacOS/$APP_NAME" ]; then
        ok "PKG hat die App nach /Applications installiert"
    else
        fail "PKG-Installation: $INSTALLED fehlt"
    fi
    codesign --verify --deep --strict "$INSTALLED" && ok "Signatur nach PKG-Installation gueltig" \
        || fail "Signatur nach PKG-Installation ungueltig"
    pkgutil --pkg-info "$BUNDLE_ID.pkg" || fail "Paket-Beleg $BUNDLE_ID.pkg fehlt"
    sudo rm -rf "$INSTALLED"
    sudo pkgutil --forget "$BUNDLE_ID.pkg" >/dev/null 2>&1 || true
else
    warn "Kein PKG gefunden - PKG-Test uebersprungen"
fi

# ----------------------------------------------------------
# 2. DMG pruefen und App daraus installieren
# ----------------------------------------------------------
step "DMG pruefen: $(basename "$DMG")"
hdiutil verify "$DMG" >/dev/null 2>&1 && ok "DMG-Pruefsumme gueltig" || fail "hdiutil verify fehlgeschlagen"
MNT="$(mktemp -d /tmp/teedmg.XXXXXX)"
hdiutil attach -nobrowse -readonly -noautoopen -mountpoint "$MNT" "$DMG" >/dev/null
ls -la "$MNT" | tee "$OUT/dmg-contents.txt"
[ -d "$MNT/$APP_NAME.app" ] && ok "App im DMG" || fail "App fehlt im DMG"
[ -L "$MNT/Applications" ] && [ "$(readlink "$MNT/Applications")" = "/Applications" ] \
    && ok "Verknuepfung 'Applications' -> /Applications" || fail "Applications-Verknuepfung fehlt"
[ -f "$MNT/.VolumeIcon.icns" ] && ok "Laufwerks-Icon vorhanden" || fail "Laufwerks-Icon fehlt"
[ -f "$MNT/.background/background.tiff" ] && ok "DMG-Hintergrund vorhanden" || fail "DMG-Hintergrund fehlt"
[ -f "$MNT/.DS_Store" ] && ok "Fensterlayout (.DS_Store) gespeichert" \
    || warn "Kein .DS_Store - Finder zeigt das Standardlayout"
stop_app
rm -rf "$INSTALLED"
ditto "$MNT/$APP_NAME.app" "$INSTALLED"
hdiutil detach "$MNT" -quiet || hdiutil detach "$MNT" -force -quiet || true
codesign --verify --deep --strict "$INSTALLED" && ok "Aus DMG kopierte App: Signatur gueltig" \
    || fail "Aus DMG kopierte App: Signatur ungueltig"
lipo -archs "$INSTALLED/Contents/MacOS/$APP_NAME" | tee "$OUT/main-exe-archs.txt"

# ----------------------------------------------------------
# 3. App starten und pruefen
# ----------------------------------------------------------
check_running_app() {
    local label=$1 expect_arch=$2
    local pid="" asn info

    for _ in $(seq 1 45); do
        pid="$(app_pids | head -1)"
        [ -n "$pid" ] && break
        sleep 1
    done
    if [ -z "$pid" ]; then
        fail "[$label] App-Prozess startet nicht"
        return
    fi
    ok "[$label] Prozess laeuft (PID $pid)"

    # Python-Teil: main.py legt beim Import den Einstellungsordner an
    for _ in $(seq 1 120); do
        [ -d "$SUPPORT_DIR" ] && break
        sleep 1
    done
    [ -d "$SUPPORT_DIR" ] && ok "[$label] Python-App gestartet (Einstellungsordner angelegt)" \
        || fail "[$label] Python-App hat nicht gestartet ($SUPPORT_DIR fehlt)"

    sleep 10   # Fenster fertig zeichnen lassen

    asn="$(lsappinfo find bundleid="$BUNDLE_ID" 2>/dev/null | head -1 || true)"
    info="$(lsappinfo info "$asn" 2>/dev/null || true)"
    echo "$info" | tee "$OUT/lsappinfo-$label.txt"
    grep -q 'type="Foreground"' <<< "$info" \
        && ok "[$label] Normale App mit Dock-Symbol (lsappinfo type=Foreground)" \
        || fail "[$label] App ist nicht als Dock-App registriert"
    grep -q "\"$APP_NAME\"" <<< "$info" \
        && ok "[$label] Name im Dock/Menue: $APP_NAME" \
        || fail "[$label] App-Name stimmt nicht"
    if [ -n "$expect_arch" ]; then
        if grep -qi "arch=$expect_arch" <<< "$info"; then
            ok "[$label] Laeuft als $expect_arch"
        else
            warn "[$label] Architektur laut lsappinfo nicht eindeutig ($expect_arch erwartet)"
        fi
    fi

    lsof -p "$pid" 2>/dev/null > "$OUT/loaded-files-$label.txt" || true
    for lib in "_rust.abi3.so:cryptography" "_imaging.cpython:Pillow" "zxingcpp:zxing-cpp"; do
        if grep -q "${lib%%:*}" "$OUT/loaded-files-$label.txt"; then
            ok "[$label] ${lib##*:} geladen"
        else
            fail "[$label] ${lib##*:} NICHT geladen"
        fi
    done

    if [ -f "$CONSOLE_LOG" ]; then
        cp "$CONSOLE_LOG" "$OUT/console-$label.log"
        if grep -q "Traceback" "$CONSOLE_LOG"; then
            fail "[$label] Python-Fehler im Log:"
            cat "$CONSOLE_LOG"
        else
            ok "[$label] Python-Log ohne Fehler"
        fi
    fi

    [ ! -e "$HOME/Documents/flet" ] && ok "[$label] Keine Daten in ~/Documents (keine Datenschutz-Rueckfrage)" \
        || fail "[$label] App hat ~/Documents/flet angelegt"

    screencapture -x "$OUT/screenshot-$label.png" 2>/dev/null \
        && ok "[$label] Screenshot: $OUT/screenshot-$label.png" \
        || warn "[$label] Screenshot nicht moeglich"

    osascript -e 'tell application "System Events" to get name of every UI element of list 1 of application process "Dock"' \
        > "$OUT/dock-items-$label.txt" 2>&1 || true
    if grep -q "$APP_NAME" "$OUT/dock-items-$label.txt"; then
        ok "[$label] Im Dock sichtbar: $(cat "$OUT/dock-items-$label.txt")"
    else
        warn "[$label] Dock-Eintraege nicht lesbar (Bedienungshilfen-Recht fehlt): $(head -c 300 "$OUT/dock-items-$label.txt")"
    fi
}

step "Start 1: native Architektur ($(uname -m))"
stop_app
rm -rf "$SUPPORT_DIR" "$CACHE_DIR"
open "$INSTALLED"
check_running_app "native-$(uname -m)" ""
stop_app

if [ "$(uname -m)" = "arm64" ]; then
    step "Start 2: Intel-Version (x86_64) unter Rosetta 2"
    if ! arch -x86_64 /usr/bin/true 2>/dev/null; then
        sudo softwareupdate --install-rosetta --agree-to-license >/dev/null 2>&1 || true
    fi
    if arch -x86_64 /usr/bin/true 2>/dev/null; then
        rm -rf "$SUPPORT_DIR" "$CACHE_DIR"
        if ! open --arch x86_64 "$INSTALLED" 2>/dev/null; then
            arch -x86_64 "$INSTALLED/Contents/MacOS/$APP_NAME" >/dev/null 2>&1 &
        fi
        check_running_app "rosetta-x86_64" "x86_64"
        stop_app
    else
        warn "Rosetta 2 nicht verfuegbar - Intel-Test uebersprungen"
    fi
fi

echo ""
if [ "$FAILED" = true ]; then
    echo -e "${RED}Smoke-Test FEHLGESCHLAGEN - Details siehe oben und $OUT${NC}"
    exit 1
fi
echo -e "${GREEN}Smoke-Test bestanden.${NC}"
