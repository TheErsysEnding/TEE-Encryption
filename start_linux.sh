#!/bin/bash
# ==========================================================
#   TEE Encryption V4.2.1 - Linux Starter & Auto-Installer
# ==========================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo -e "${CYAN}=========================================="
echo -e "   TEE Encryption V4.2.1 - Linux Setup"
echo -e "==========================================${NC}"
echo ""

# ----------------------------------------------------------
# 1. Python 3.10+ prüfen
# ----------------------------------------------------------
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[FEHLER] Python3 wurde nicht gefunden.${NC}"
    echo ""
    echo "Bitte installiere Python 3.10 oder neuer:"
    echo "  Ubuntu / Debian:  sudo apt install python3 python3-pip python3-venv"
    echo "  Fedora:           sudo dnf install python3 python3-pip"
    echo "  Arch Linux:       sudo pacman -S python"
    echo ""
    exit 1
fi

PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo -e "${RED}[FEHLER] Python $PY_MAJOR.$PY_MINOR gefunden — mindestens Python 3.10 benötigt.${NC}"
    exit 1
fi

echo -e "${GREEN}[OK] Python $PY_MAJOR.$PY_MINOR gefunden.${NC}"

# ----------------------------------------------------------
# 2. python3-venv sicherstellen
# ----------------------------------------------------------
if ! python3 -m venv --help &>/dev/null; then
    echo -e "${YELLOW}[INFO] python3-venv fehlt. Wird installiert...${NC}"
    if command -v apt-get &>/dev/null; then
        sudo apt-get install -y python3-venv python3-pip
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3-pip
    fi
fi

# ----------------------------------------------------------
# 3. System-Bibliothek libzbar0 (für QR-Code-Funktion)
# ----------------------------------------------------------
ZBAR_OK=false
python3 -c "from pyzbar import pyzbar" 2>/dev/null && ZBAR_OK=true

if [ "$ZBAR_OK" = false ]; then
    echo ""
    echo -e "${YELLOW}[INFO] Systembibliothek 'libzbar0' wird für QR-Codes benötigt.${NC}"
    read -r -p "       Jetzt automatisch installieren? [J/n] " REPLY
    REPLY="${REPLY:-J}"
    if [[ "$REPLY" =~ ^[JjYy] ]]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update -qq && sudo apt-get install -y libzbar0
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y zbar
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm zbar
        elif command -v zypper &>/dev/null; then
            sudo zypper install -y zbar
        else
            echo -e "${YELLOW}[WARNUNG] Paketmanager nicht erkannt.${NC}"
            echo "Installiere manuell: libzbar0 (oder zbar)"
        fi
    else
        echo -e "${YELLOW}[WARNUNG] QR-Code-Funktion wird ohne libzbar0 nicht funktionieren.${NC}"
    fi
fi

# ----------------------------------------------------------
# 4. Virtuelle Python-Umgebung anlegen (einmalig)
# ----------------------------------------------------------
if [ ! -d ".venv" ]; then
    echo ""
    echo -e "${CYAN}[SETUP] Erstelle Python-Umgebung (einmalig)...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}[OK] Umgebung erstellt.${NC}"
fi

source .venv/bin/activate

# ----------------------------------------------------------
# 5. Python-Pakete installieren (nur wenn nötig)
# ----------------------------------------------------------
NEED_INSTALL=false
python3 -c "import flet" 2>/dev/null       || NEED_INSTALL=true
python3 -c "import cryptography" 2>/dev/null || NEED_INSTALL=true

if [ "$NEED_INSTALL" = true ]; then
    echo ""
    echo -e "${CYAN}[SETUP] Installiere Pakete (dauert ~1-2 Minuten beim ersten Start)...${NC}"
    echo ""
    pip install --upgrade pip --quiet
    pip install flet==0.85.2 flet-desktop==0.85.2 cryptography pyzbar pillow
    echo ""
    echo -e "${GREEN}[OK] Alle Pakete installiert.${NC}"
else
    echo -e "${GREEN}[OK] Alle Pakete vorhanden.${NC}"
fi

# ----------------------------------------------------------
# 6. App starten
# ----------------------------------------------------------
echo ""
echo -e "${GREEN}Starte TEE Encryption V4.2.1...${NC}"
echo ""
python3 TEE_Encryption_V4.2.1_GUI.py
