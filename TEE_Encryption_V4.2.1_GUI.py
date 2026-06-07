#!/usr/bin/env python3
"""
TEE Encryption Tool V4.2.1 - Flet Edition
Modern cross-platform GUI using Flet (Flutter for Python)
Works on Windows, Linux, macOS
"""

import flet as ft
import os
import sys
import base64
import time
import struct
import json
import secrets
import string
import hashlib
import io
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Cryptography Libraries
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Optional: QR Code
try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

# Optional: QR Code Reader (pyzbar + PIL)
try:
    from pyzbar.pyzbar import decode as decode_qr
    from PIL import Image
    HAS_QR_READER = True
except ImportError:
    HAS_QR_READER = False

# ---------------------------------------------------------
# CONFIGURATION & CONSTANTS
# ---------------------------------------------------------
APP_TITLE = "TEE Encryption V4.2.1"
PACKAGE_VERSION = 1
SALT_SIZE = 16
IV_SIZE = 12
ITERATIONS_DEFAULT = 200_000
INTERNAL_MARKER = b'TEE-EXT'

def get_app_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def resource_path(rel):
    """Pfad zu einer gebuendelten Ressource - funktioniert auch in der PyInstaller-EXE.
    Bei onefile-Builds liegen gebuendelte Dateien in sys._MEIPASS."""
    base = getattr(sys, '_MEIPASS', None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, rel)

CONFIG_FILE = os.path.join(get_app_path(), "config.json")

# ---------------------------------------------------------
# THEME DEFINITIONS
# ---------------------------------------------------------
THEME = {
    "light": {
        "bg": "#F0F2F5",
        "card": "#FFFFFF",
        "text": "#1F1F1F",
        "text_sub": "#555555",
        "primary": "#0069C0",
        "primary_hover": "#005cb2",
        "accent": "#E3F2FD",
        "danger": "#D32F2F",
        "success": "#2E7D32",
        "border": "#E0E0E0",
    },
    "dark": {
        "bg": "#121212",
        "card": "#1E1E1E",
        "text": "#E0E0E0",
        "text_sub": "#AAAAAA",
        "primary": "#64B5F6",
        "primary_hover": "#42A5F5",
        "accent": "#263238",
        "danger": "#EF5350",
        "success": "#66BB6A",
        "border": "#333333",
    }
}

# ---------------------------------------------------------
# TRANSLATIONS
# ---------------------------------------------------------
TEXT = {
    "en": {
        "welcome": APP_TITLE,
        "input_label": "Input Content",
        "input_hint": "Enter text here...",
        "file_hint": "No file selected...",
        "password": "Password",
        "confirm_password": "Confirm",
        "show_password": "Show",
        "gen_btn": "Gen",
        "iterations": "Iter.",
        "output_label": "Output Content",
        "encrypt_btn": "🔒 Encrypt",
        "decrypt_btn": "🔓 Decrypt",
        "copy_btn": "Copy",
        "save_btn": "Save",
        "import_btn": "Import",
        "swap_btn": "Swap",
        "clear_btn": "Clear",
        "file_btn": "File",
        "hash_btn": "Hash",
        "no_input": "Please provide input data or select a file.",
        "error": "Error: {0}",
        "weak_password": "⚠️ Weak password",
        "keyfile_error": "Keyfile could not be read – operation cancelled.\n\nA keyfile is set, but it is missing or unreadable. To encrypt/decrypt WITHOUT the keyfile, remove it first (Keyfile button).",
        "pass_mismatch": "Mismatch!",
        "decrypt_failed": "Decryption failed. Check password/data.",
        "decrypt_failed_title": "Decryption Failed",
        "decrypt_failed_msg": "Could not decrypt the message.\n\nPossible reasons:\n• Wrong password\n• Missing or wrong keyfile\n• Data is corrupted\n• Data was modified",
        "decrypt_file_failed_msg": "Could not decrypt the file.\n\nPossible reasons:\n• Wrong password\n• Missing or wrong keyfile\n• File is corrupted\n• File was modified",
        "decrypt_wrong_password": "Wrong password!\n\nThe decryption failed. Please check:\n• Is the password correct?\n• Did you use a keyfile when encrypting?\n• Is the encrypted text complete and unmodified?",
        "decrypt_invalid_input": "The input is not valid encrypted data.\n\nMake sure you copied the complete encrypted text (Base64 format).",
        "decrypt_invalid_format": "The data format is invalid or corrupted.\n\nThis doesn't look like data encrypted with TEE Encryption.",
        "decrypt_file_wrong_password": "Wrong password!\n\nThe file could not be decrypted. Please check:\n• Is the password correct?\n• Did you use a keyfile when encrypting?\n• Is the file complete and unmodified?",
        "copied": "✓ Copied",
        "file_encrypted": "✓ File encrypted: {0}",
        "file_decrypted": "✓ File decrypted: {0}",
        "saved": "✓ Saved",
        "dark_mode": "Dark",
        "light_mode": "Light",
        "keyfile_btn": "Keyfile",
        "keyfile_active": "Keyfile: ON",
        "keyfile_removed": "Keyfile removed",
        "gen_title": "Password Generator",
        "gen_length": "Length: {0}",
        "gen_lower": "a-z",
        "gen_upper": "A-Z", 
        "gen_digits": "0-9",
        "gen_symbols": "!@#$%",
        "gen_apply": "Apply",
        "gen_cancel": "Cancel",
        "opacity": "Opacity",
        "pin_btn": "📌 Pin",
        "unpin_btn": "📌 Unpin",
        "exit_btn": "Exit",
        "confirm_check": "Confirm",
        "qr_btn": "Show QR",
        "save_txt_btn": "Save .txt",
        "import_txt_btn": "Import .txt",
        "languages": ["en", "de", "es", "fr", "tr", "ru", "ar", "ja", "zh"],
    },
    "de": {
        "welcome": APP_TITLE,
        "input_label": "Eingabe Inhalt",
        "input_hint": "Text hier eingeben...",
        "file_hint": "Keine Datei ausgewählt...",
        "password": "Passwort",
        "confirm_password": "Bestätigen",
        "show_password": "Zeigen",
        "gen_btn": "Gen",
        "iterations": "Iter.",
        "output_label": "Ausgabe Inhalt",
        "encrypt_btn": "🔒 Verschlüsseln",
        "decrypt_btn": "🔓 Entschlüsseln",
        "copy_btn": "Kopieren",
        "save_btn": "Speichern",
        "import_btn": "Import",
        "swap_btn": "Tausch",
        "clear_btn": "Leeren",
        "file_btn": "Datei",
        "hash_btn": "Hash",
        "no_input": "Bitte Eingabe oder Datei angeben.",
        "error": "Fehler: {0}",
        "weak_password": "⚠️ Schwaches PW",
        "keyfile_error": "Keyfile konnte nicht gelesen werden – Vorgang abgebrochen.\n\nEs ist ein Keyfile gesetzt, aber es fehlt oder ist nicht lesbar. Wenn du OHNE Keyfile ver-/entschlüsseln möchtest, entferne es zuerst (Keyfile-Knopf).",
        "pass_mismatch": "Passwörter ungleich!",
        "decrypt_failed": "Entschlüsselung fehlgeschlagen.",
        "decrypt_failed_title": "Entschlüsselung fehlgeschlagen",
        "decrypt_failed_msg": "Die Nachricht konnte nicht entschlüsselt werden.\n\nMögliche Gründe:\n• Falsches Passwort\n• Fehlendes oder falsches Keyfile\n• Daten sind beschädigt\n• Daten wurden verändert",
        "decrypt_file_failed_msg": "Die Datei konnte nicht entschlüsselt werden.\n\nMögliche Gründe:\n• Falsches Passwort\n• Fehlendes oder falsches Keyfile\n• Datei ist beschädigt\n• Datei wurde verändert",
        "decrypt_wrong_password": "Falsches Passwort!\n\nDie Entschlüsselung ist fehlgeschlagen. Bitte prüfe:\n• Ist das Passwort korrekt?\n• Wurde beim Verschlüsseln ein Keyfile verwendet?\n• Ist der verschlüsselte Text vollständig und unverändert?",
        "decrypt_invalid_input": "Die Eingabe ist keine gültig verschlüsselten Daten.\n\nStelle sicher, dass du den kompletten verschlüsselten Text kopiert hast (Base64-Format).",
        "decrypt_invalid_format": "Das Datenformat ist ungültig oder beschädigt.\n\nDas sieht nicht nach Daten aus, die mit TEE Encryption verschlüsselt wurden.",
        "decrypt_file_wrong_password": "Falsches Passwort!\n\nDie Datei konnte nicht entschlüsselt werden. Bitte prüfe:\n• Ist das Passwort korrekt?\n• Wurde beim Verschlüsseln ein Keyfile verwendet?\n• Ist die Datei vollständig und unverändert?",
        "copied": "✓ Kopiert",
        "file_encrypted": "✓ Datei verschlüsselt: {0}",
        "file_decrypted": "✓ Datei entschlüsselt: {0}",
        "saved": "✓ Gespeichert",
        "dark_mode": "Dunkel",
        "light_mode": "Hell",
        "keyfile_btn": "Keyfile",
        "keyfile_active": "Keyfile: AN",
        "keyfile_removed": "Keyfile entfernt",
        "gen_title": "Passwort-Generator",
        "gen_length": "Länge: {0}",
        "gen_lower": "a-z",
        "gen_upper": "A-Z",
        "gen_digits": "0-9",
        "gen_symbols": "!@#$%",
        "gen_apply": "Übernehmen",
        "gen_cancel": "Abbruch",
        "opacity": "Transparenz",
        "pin_btn": "📌 Anheften",
        "unpin_btn": "📌 Lösen",
        "exit_btn": "Beenden",
        "confirm_check": "Bestätigen",
        "qr_btn": "QR zeigen",
        "save_txt_btn": "Speichern .txt",
        "import_txt_btn": "Import .txt",
        "languages": ["en", "de", "es", "fr", "tr", "ru", "ar", "ja", "zh"],
    },
    "es": {
        "welcome": APP_TITLE,
        "input_label": "Entrada",
        "input_hint": "Ingrese texto aquí...",
        "file_hint": "Ningún archivo seleccionado...",
        "password": "Contraseña",
        "confirm_password": "Confirmar",
        "show_password": "Ver",
        "gen_btn": "Gen",
        "iterations": "Iter.",
        "output_label": "Salida",
        "encrypt_btn": "🔒 Cifrar",
        "decrypt_btn": "🔓 Descifrar",
        "copy_btn": "Copiar",
        "save_btn": "Guardar",
        "import_btn": "Importar",
        "swap_btn": "Cambiar",
        "clear_btn": "Limpiar",
        "file_btn": "Archivo",
        "hash_btn": "Hash",
        "no_input": "Proporcione datos o seleccione archivo.",
        "error": "Error: {0}",
        "weak_password": "⚠️ Contraseña débil",
        "pass_mismatch": "¡No coinciden!",
        "decrypt_failed": "Fallo al descifrar.",
        "decrypt_failed_title": "Error de descifrado",
        "decrypt_failed_msg": "No se pudo descifrar el mensaje.\n\nPosibles razones:\n• Contraseña incorrecta\n• Archivo clave faltante o incorrecto\n• Datos corruptos\n• Datos modificados",
        "decrypt_file_failed_msg": "No se pudo descifrar el archivo.\n\nPosibles razones:\n• Contraseña incorrecta\n• Archivo clave faltante o incorrecto\n• Archivo corrupto\n• Archivo modificado",
        "decrypt_wrong_password": "¡Contraseña incorrecta!\n\nEl descifrado falló. Por favor verifica:\n• ¿Es correcta la contraseña?\n• ¿Usaste un archivo clave al cifrar?\n• ¿Está completo y sin modificar el texto cifrado?",
        "decrypt_invalid_input": "La entrada no son datos cifrados válidos.\n\nAsegúrate de haber copiado el texto cifrado completo (formato Base64).",
        "decrypt_invalid_format": "El formato de datos es inválido o está corrupto.\n\nEsto no parece ser datos cifrados con TEE Encryption.",
        "decrypt_file_wrong_password": "¡Contraseña incorrecta!\n\nNo se pudo descifrar el archivo. Por favor verifica:\n• ¿Es correcta la contraseña?\n• ¿Usaste un archivo clave al cifrar?\n• ¿Está el archivo completo y sin modificar?",
        "copied": "✓ Copiado",
        "file_encrypted": "✓ Cifrado: {0}",
        "file_decrypted": "✓ Descifrado: {0}",
        "saved": "✓ Guardado",
        "dark_mode": "Oscuro",
        "light_mode": "Claro",
        "keyfile_btn": "Clave",
        "keyfile_active": "Clave: ON",
        "keyfile_removed": "Clave eliminada",
        "gen_title": "Generador",
        "gen_length": "Longitud: {0}",
        "gen_lower": "a-z",
        "gen_upper": "A-Z",
        "gen_digits": "0-9",
        "gen_symbols": "!@#$%",
        "gen_apply": "Usar",
        "gen_cancel": "Cancelar",
        "opacity": "Opacidad",
        "pin_btn": "📌 Fijar",
        "unpin_btn": "📌 Soltar",
        "exit_btn": "Salir",
        "confirm_check": "Confirmar",
        "qr_btn": "Mostrar QR",
        "save_txt_btn": "Guardar .txt",
        "import_txt_btn": "Importar .txt",
        "languages": ["en", "de", "es", "fr", "tr", "ru", "ar", "ja", "zh"],
    },
    "fr": {
        "welcome": APP_TITLE,
        "input_label": "Entrée",
        "input_hint": "Entrez le texte ici...",
        "file_hint": "Aucun fichier sélectionné...",
        "password": "Mot de passe",
        "confirm_password": "Confirmer",
        "show_password": "Voir",
        "gen_btn": "Gén",
        "iterations": "Itér.",
        "output_label": "Sortie",
        "encrypt_btn": "🔒 Chiffrer",
        "decrypt_btn": "🔓 Déchiffrer",
        "copy_btn": "Copier",
        "save_btn": "Sauver",
        "import_btn": "Importer",
        "swap_btn": "Échanger",
        "clear_btn": "Effacer",
        "file_btn": "Fichier",
        "hash_btn": "Hash",
        "no_input": "Fournir des données ou un fichier.",
        "error": "Erreur: {0}",
        "weak_password": "⚠️ Faible",
        "pass_mismatch": "Ne correspondent pas!",
        "decrypt_failed": "Échec déchiffrement.",
        "decrypt_failed_title": "Échec du déchiffrement",
        "decrypt_failed_msg": "Impossible de déchiffrer le message.\n\nRaisons possibles:\n• Mot de passe incorrect\n• Fichier clé manquant ou incorrect\n• Données corrompues\n• Données modifiées",
        "decrypt_file_failed_msg": "Impossible de déchiffrer le fichier.\n\nRaisons possibles:\n• Mot de passe incorrect\n• Fichier clé manquant ou incorrect\n• Fichier corrompu\n• Fichier modifié",
        "decrypt_wrong_password": "Mot de passe incorrect!\n\nLe déchiffrement a échoué. Veuillez vérifier:\n• Le mot de passe est-il correct?\n• Avez-vous utilisé un fichier clé lors du chiffrement?\n• Le texte chiffré est-il complet et non modifié?",
        "decrypt_invalid_input": "L'entrée n'est pas des données chiffrées valides.\n\nAssurez-vous d'avoir copié le texte chiffré complet (format Base64).",
        "decrypt_invalid_format": "Le format des données est invalide ou corrompu.\n\nCela ne ressemble pas à des données chiffrées avec TEE Encryption.",
        "decrypt_file_wrong_password": "Mot de passe incorrect!\n\nLe fichier n'a pas pu être déchiffré. Veuillez vérifier:\n• Le mot de passe est-il correct?\n• Avez-vous utilisé un fichier clé lors du chiffrement?\n• Le fichier est-il complet et non modifié?",
        "copied": "✓ Copié",
        "file_encrypted": "✓ Chiffré: {0}",
        "file_decrypted": "✓ Déchiffré: {0}",
        "saved": "✓ Sauvegardé",
        "dark_mode": "Sombre",
        "light_mode": "Clair",
        "keyfile_btn": "Clé",
        "keyfile_active": "Clé: ON",
        "keyfile_removed": "Clé supprimée",
        "gen_title": "Générateur",
        "gen_length": "Longueur: {0}",
        "gen_lower": "a-z",
        "gen_upper": "A-Z",
        "gen_digits": "0-9",
        "gen_symbols": "!@#$%",
        "gen_apply": "Utiliser",
        "gen_cancel": "Annuler",
        "opacity": "Opacité",
        "pin_btn": "📌 Épingler",
        "unpin_btn": "📌 Détacher",
        "exit_btn": "Quitter",
        "confirm_check": "Confirmer",
        "qr_btn": "Afficher QR",
        "save_txt_btn": "Sauver .txt",
        "import_txt_btn": "Importer .txt",
        "languages": ["en", "de", "es", "fr", "tr", "ru", "ar", "ja", "zh"],
    },
    "tr": {
        "welcome": APP_TITLE,
        "input_label": "Giriş İçeriği",
        "input_hint": "Metni buraya girin...",
        "file_hint": "Dosya seçilmedi...",
        "password": "Şifre",
        "confirm_password": "Onayla",
        "show_password": "Göster",
        "gen_btn": "Oluştur",
        "iterations": "Tekrar",
        "output_label": "Çıkış İçeriği",
        "encrypt_btn": "🔒 Şifrele",
        "decrypt_btn": "🔓 Çöz",
        "copy_btn": "Kopyala",
        "save_btn": "Kaydet",
        "import_btn": "İçe Aktar",
        "swap_btn": "Değiştir",
        "clear_btn": "Temizle",
        "file_btn": "Dosya",
        "hash_btn": "Hash",
        "no_input": "Lütfen veri girin veya dosya seçin.",
        "error": "Hata: {0}",
        "weak_password": "⚠️ Zayıf şifre",
        "pass_mismatch": "Eşleşmiyor!",
        "decrypt_failed": "Şifre çözme başarısız.",
        "decrypt_failed_title": "Şifre Çözme Hatası",
        "decrypt_failed_msg": "Mesaj çözülemedi.\n\nOlası nedenler:\n• Yanlış şifre\n• Eksik veya yanlış anahtar dosyası\n• Bozuk veri\n• Değiştirilmiş veri",
        "decrypt_file_failed_msg": "Dosya çözülemedi.\n\nOlası nedenler:\n• Yanlış şifre\n• Eksik veya yanlış anahtar dosyası\n• Bozuk dosya\n• Değiştirilmiş dosya",
        "decrypt_wrong_password": "Yanlış şifre!\n\nŞifre çözme başarısız. Kontrol edin:\n• Şifre doğru mu?\n• Şifrelerken anahtar dosyası kullandınız mı?\n• Şifreli metin tam ve değiştirilmemiş mi?",
        "decrypt_invalid_input": "Giriş geçerli şifreli veri değil.\n\nTam şifreli metni kopyaladığınızdan emin olun (Base64 formatı).",
        "decrypt_invalid_format": "Veri formatı geçersiz veya bozuk.\n\nBu TEE Encryption ile şifrelenmiş veriye benzemiyor.",
        "decrypt_file_wrong_password": "Yanlış şifre!\n\nDosya çözülemedi. Kontrol edin:\n• Şifre doğru mu?\n• Şifrelerken anahtar dosyası kullandınız mı?\n• Dosya tam ve değiştirilmemiş mi?",
        "copied": "✓ Kopyalandı",
        "file_encrypted": "✓ Dosya şifrelendi: {0}",
        "file_decrypted": "✓ Dosya çözüldü: {0}",
        "saved": "✓ Kaydedildi",
        "dark_mode": "Karanlık",
        "light_mode": "Aydınlık",
        "keyfile_btn": "Anahtar",
        "keyfile_active": "Anahtar: AÇIK",
        "keyfile_removed": "Anahtar kaldırıldı",
        "gen_title": "Şifre Oluşturucu",
        "gen_length": "Uzunluk: {0}",
        "gen_lower": "a-z",
        "gen_upper": "A-Z",
        "gen_digits": "0-9",
        "gen_symbols": "!@#$%",
        "gen_apply": "Uygula",
        "gen_cancel": "İptal",
        "opacity": "Saydamlık",
        "pin_btn": "📌 Sabitle",
        "unpin_btn": "📌 Kaldır",
        "exit_btn": "Çıkış",
        "confirm_check": "Onayla",
        "qr_btn": "QR Göster",
        "save_txt_btn": "Kaydet .txt",
        "import_txt_btn": "İçe Aktar .txt",
        "languages": ["en", "de", "es", "fr", "tr", "ru", "ar", "ja", "zh"],
    },
    "ru": {
        "welcome": APP_TITLE,
        "input_label": "Входные данные",
        "input_hint": "Введите текст здесь...",
        "file_hint": "Файл не выбран...",
        "password": "Пароль",
        "confirm_password": "Подтвердить",
        "show_password": "Показать",
        "gen_btn": "Генер.",
        "iterations": "Итер.",
        "output_label": "Выходные данные",
        "encrypt_btn": "🔒 Шифровать",
        "decrypt_btn": "🔓 Расшифровать",
        "copy_btn": "Копировать",
        "save_btn": "Сохранить",
        "import_btn": "Импорт",
        "swap_btn": "Поменять",
        "clear_btn": "Очистить",
        "file_btn": "Файл",
        "hash_btn": "Хэш",
        "no_input": "Введите данные или выберите файл.",
        "error": "Ошибка: {0}",
        "weak_password": "⚠️ Слабый пароль",
        "pass_mismatch": "Не совпадают!",
        "decrypt_failed": "Расшифровка не удалась.",
        "decrypt_failed_title": "Ошибка расшифровки",
        "decrypt_failed_msg": "Не удалось расшифровать сообщение.\n\nВозможные причины:\n• Неверный пароль\n• Отсутствует или неверный ключевой файл\n• Данные повреждены\n• Данные изменены",
        "decrypt_file_failed_msg": "Не удалось расшифровать файл.\n\nВозможные причины:\n• Неверный пароль\n• Отсутствует или неверный ключевой файл\n• Файл поврежден\n• Файл изменен",
        "decrypt_wrong_password": "Неверный пароль!\n\nРасшифровка не удалась. Проверьте:\n• Правильный ли пароль?\n• Использовали ли вы ключевой файл при шифровании?\n• Полный ли и неизмененный зашифрованный текст?",
        "decrypt_invalid_input": "Ввод не является зашифрованными данными.\n\nУбедитесь, что вы скопировали полный зашифрованный текст (формат Base64).",
        "decrypt_invalid_format": "Формат данных недействителен или поврежден.\n\nЭто не похоже на данные, зашифрованные TEE Encryption.",
        "decrypt_file_wrong_password": "Неверный пароль!\n\nФайл не может быть расшифрован. Проверьте:\n• Правильный ли пароль?\n• Использовали ли вы ключевой файл при шифровании?\n• Полный ли и неизмененный файл?",
        "copied": "✓ Скопировано",
        "file_encrypted": "✓ Файл зашифрован: {0}",
        "file_decrypted": "✓ Файл расшифрован: {0}",
        "saved": "✓ Сохранено",
        "dark_mode": "Тёмная",
        "light_mode": "Светлая",
        "keyfile_btn": "Ключ",
        "keyfile_active": "Ключ: ВКЛ",
        "keyfile_removed": "Ключ удален",
        "gen_title": "Генератор паролей",
        "gen_length": "Длина: {0}",
        "gen_lower": "a-z",
        "gen_upper": "A-Z",
        "gen_digits": "0-9",
        "gen_symbols": "!@#$%",
        "gen_apply": "Применить",
        "gen_cancel": "Отмена",
        "opacity": "Прозрачность",
        "pin_btn": "📌 Закрепить",
        "unpin_btn": "📌 Открепить",
        "exit_btn": "Выход",
        "confirm_check": "Подтвердить",
        "qr_btn": "Показать QR",
        "save_txt_btn": "Сохранить .txt",
        "import_txt_btn": "Импорт .txt",
        "languages": ["en", "de", "es", "fr", "tr", "ru", "ar", "ja", "zh"],
    },
    "ar": {
        "welcome": APP_TITLE,
        "input_label": "محتوى الإدخال",
        "input_hint": "أدخل النص هنا...",
        "file_hint": "لم يتم اختيار ملف...",
        "password": "كلمة المرور",
        "confirm_password": "تأكيد",
        "show_password": "إظهار",
        "gen_btn": "توليد",
        "iterations": "تكرار",
        "output_label": "محتوى الإخراج",
        "encrypt_btn": "🔒 تشفير",
        "decrypt_btn": "🔓 فك التشفير",
        "copy_btn": "نسخ",
        "save_btn": "حفظ",
        "import_btn": "استيراد",
        "swap_btn": "تبديل",
        "clear_btn": "مسح",
        "file_btn": "ملف",
        "hash_btn": "تجزئة",
        "no_input": "يرجى إدخال بيانات أو اختيار ملف.",
        "error": "خطأ: {0}",
        "weak_password": "⚠️ كلمة مرور ضعيفة",
        "pass_mismatch": "غير متطابق!",
        "decrypt_failed": "فشل فك التشفير.",
        "decrypt_failed_title": "فشل فك التشفير",
        "decrypt_failed_msg": "تعذر فك تشفير الرسالة.\n\nالأسباب المحتملة:\n• كلمة مرور خاطئة\n• ملف مفتاح مفقود أو خاطئ\n• البيانات تالفة\n• البيانات معدلة",
        "decrypt_file_failed_msg": "تعذر فك تشفير الملف.\n\nالأسباب المحتملة:\n• كلمة مرور خاطئة\n• ملف مفتاح مفقود أو خاطئ\n• الملف تالف\n• الملف معدل",
        "decrypt_wrong_password": "كلمة مرور خاطئة!\n\nفشل فك التشفير. تحقق من:\n• هل كلمة المرور صحيحة؟\n• هل استخدمت ملف مفتاح عند التشفير؟\n• هل النص المشفر كامل وغير معدل؟",
        "decrypt_invalid_input": "الإدخال ليس بيانات مشفرة صالحة.\n\nتأكد من نسخ النص المشفر الكامل (تنسيق Base64).",
        "decrypt_invalid_format": "تنسيق البيانات غير صالح أو تالف.\n\nهذا لا يبدو كبيانات مشفرة بـ TEE Encryption.",
        "decrypt_file_wrong_password": "كلمة مرور خاطئة!\n\nتعذر فك تشفير الملف. تحقق من:\n• هل كلمة المرور صحيحة؟\n• هل استخدمت ملف مفتاح عند التشفير؟\n• هل الملف كامل وغير معدل؟",
        "copied": "✓ تم النسخ",
        "file_encrypted": "✓ تم تشفير الملف: {0}",
        "file_decrypted": "✓ تم فك تشفير الملف: {0}",
        "saved": "✓ تم الحفظ",
        "dark_mode": "داكن",
        "light_mode": "فاتح",
        "keyfile_btn": "مفتاح",
        "keyfile_active": "مفتاح: مفعل",
        "keyfile_removed": "تم إزالة المفتاح",
        "gen_title": "مولد كلمات المرور",
        "gen_length": "الطول: {0}",
        "gen_lower": "a-z",
        "gen_upper": "A-Z",
        "gen_digits": "0-9",
        "gen_symbols": "!@#$%",
        "gen_apply": "تطبيق",
        "gen_cancel": "إلغاء",
        "opacity": "الشفافية",
        "pin_btn": "📌 تثبيت",
        "unpin_btn": "📌 إلغاء التثبيت",
        "exit_btn": "خروج",
        "confirm_check": "تأكيد",
        "qr_btn": "عرض QR",
        "save_txt_btn": "حفظ .txt",
        "import_txt_btn": "استيراد .txt",
        "languages": ["en", "de", "es", "fr", "tr", "ru", "ar", "ja", "zh"],
    },
    "ja": {
        "welcome": APP_TITLE,
        "input_label": "入力内容",
        "input_hint": "ここにテキストを入力...",
        "file_hint": "ファイル未選択...",
        "password": "パスワード",
        "confirm_password": "確認",
        "show_password": "表示",
        "gen_btn": "生成",
        "iterations": "反復",
        "output_label": "出力内容",
        "encrypt_btn": "🔒 暗号化",
        "decrypt_btn": "🔓 復号化",
        "copy_btn": "コピー",
        "save_btn": "保存",
        "import_btn": "インポート",
        "swap_btn": "入替",
        "clear_btn": "クリア",
        "file_btn": "ファイル",
        "hash_btn": "ハッシュ",
        "no_input": "データを入力するかファイルを選択してください。",
        "error": "エラー: {0}",
        "weak_password": "⚠️ 弱いパスワード",
        "pass_mismatch": "不一致!",
        "decrypt_failed": "復号化に失敗しました。",
        "decrypt_failed_title": "復号化エラー",
        "decrypt_failed_msg": "メッセージを復号化できませんでした。\n\n考えられる原因:\n• パスワードが間違っている\n• キーファイルが見つからないか間違っている\n• データが破損している\n• データが変更された",
        "decrypt_file_failed_msg": "ファイルを復号化できませんでした。\n\n考えられる原因:\n• パスワードが間違っている\n• キーファイルが見つからないか間違っている\n• ファイルが破損している\n• ファイルが変更された",
        "decrypt_wrong_password": "パスワードが間違っています!\n\n復号化に失敗しました。確認してください:\n• パスワードは正しいですか?\n• 暗号化時にキーファイルを使用しましたか?\n• 暗号化されたテキストは完全で未変更ですか?",
        "decrypt_invalid_input": "入力は有効な暗号化データではありません。\n\n完全な暗号化テキスト(Base64形式)をコピーしたことを確認してください。",
        "decrypt_invalid_format": "データ形式が無効または破損しています。\n\nこれはTEE Encryptionで暗号化されたデータではないようです。",
        "decrypt_file_wrong_password": "パスワードが間違っています!\n\nファイルを復号化できませんでした。確認してください:\n• パスワードは正しいですか?\n• 暗号化時にキーファイルを使用しましたか?\n• ファイルは完全で未変更ですか?",
        "copied": "✓ コピーしました",
        "file_encrypted": "✓ ファイルを暗号化: {0}",
        "file_decrypted": "✓ ファイルを復号化: {0}",
        "saved": "✓ 保存しました",
        "dark_mode": "ダーク",
        "light_mode": "ライト",
        "keyfile_btn": "キーファイル",
        "keyfile_active": "キー: ON",
        "keyfile_removed": "キーファイルを削除",
        "gen_title": "パスワード生成",
        "gen_length": "長さ: {0}",
        "gen_lower": "a-z",
        "gen_upper": "A-Z",
        "gen_digits": "0-9",
        "gen_symbols": "!@#$%",
        "gen_apply": "適用",
        "gen_cancel": "キャンセル",
        "opacity": "不透明度",
        "pin_btn": "📌 固定",
        "unpin_btn": "📌 解除",
        "exit_btn": "終了",
        "confirm_check": "確認",
        "qr_btn": "QR表示",
        "save_txt_btn": "保存 .txt",
        "import_txt_btn": "インポート .txt",
        "languages": ["en", "de", "es", "fr", "tr", "ru", "ar", "ja", "zh"],
    },
    "zh": {
        "welcome": APP_TITLE,
        "input_label": "输入内容",
        "input_hint": "在此输入文本...",
        "file_hint": "未选择文件...",
        "password": "密码",
        "confirm_password": "确认",
        "show_password": "显示",
        "gen_btn": "生成",
        "iterations": "迭代",
        "output_label": "输出内容",
        "encrypt_btn": "🔒 加密",
        "decrypt_btn": "🔓 解密",
        "copy_btn": "复制",
        "save_btn": "保存",
        "import_btn": "导入",
        "swap_btn": "交换",
        "clear_btn": "清除",
        "file_btn": "文件",
        "hash_btn": "哈希",
        "no_input": "请输入数据或选择文件。",
        "error": "错误: {0}",
        "weak_password": "⚠️ 弱密码",
        "pass_mismatch": "不匹配!",
        "decrypt_failed": "解密失败。",
        "decrypt_failed_title": "解密失败",
        "decrypt_failed_msg": "无法解密消息。\n\n可能的原因:\n• 密码错误\n• 密钥文件缺失或错误\n• 数据已损坏\n• 数据已被修改",
        "decrypt_file_failed_msg": "无法解密文件。\n\n可能的原因:\n• 密码错误\n• 密钥文件缺失或错误\n• 文件已损坏\n• 文件已被修改",
        "decrypt_wrong_password": "密码错误!\n\n解密失败。请检查:\n• 密码是否正确?\n• 加密时是否使用了密钥文件?\n• 加密文本是否完整且未修改?",
        "decrypt_invalid_input": "输入不是有效的加密数据。\n\n请确保复制了完整的加密文本(Base64格式)。",
        "decrypt_invalid_format": "数据格式无效或已损坏。\n\n这看起来不像是TEE Encryption加密的数据。",
        "decrypt_file_wrong_password": "密码错误!\n\n无法解密文件。请检查:\n• 密码是否正确?\n• 加密时是否使用了密钥文件?\n• 文件是否完整且未修改?",
        "copied": "✓ 已复制",
        "file_encrypted": "✓ 文件已加密: {0}",
        "file_decrypted": "✓ 文件已解密: {0}",
        "saved": "✓ 已保存",
        "dark_mode": "深色",
        "light_mode": "浅色",
        "keyfile_btn": "密钥文件",
        "keyfile_active": "密钥: 开",
        "keyfile_removed": "密钥文件已移除",
        "gen_title": "密码生成器",
        "gen_length": "长度: {0}",
        "gen_lower": "a-z",
        "gen_upper": "A-Z",
        "gen_digits": "0-9",
        "gen_symbols": "!@#$%",
        "gen_apply": "应用",
        "gen_cancel": "取消",
        "opacity": "不透明度",
        "pin_btn": "📌 固定",
        "unpin_btn": "📌 取消固定",
        "exit_btn": "退出",
        "confirm_check": "确认",
        "qr_btn": "显示二维码",
        "save_txt_btn": "保存 .txt",
        "import_txt_btn": "导入 .txt",
        "languages": ["en", "de", "es", "fr", "tr", "ru", "ar", "ja", "zh"],
    }
}

# ---------------------------------------------------------
# CRYPTO FUNCTIONS
# ---------------------------------------------------------
CHUNK_SIZE = 64 * 1024  # 64 KB chunks (wie in der alten Version)

def derive_key(password: bytes, salt: bytes, iterations: int) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    return kdf.derive(password)

def encrypt_bytes(data: bytes, password: bytes, iterations: int) -> bytes:
    salt = secrets.token_bytes(SALT_SIZE)
    iv = secrets.token_bytes(IV_SIZE)
    key = derive_key(password, salt, iterations)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(iv, data, None)
    return bytes([PACKAGE_VERSION]) + struct.pack(">I", iterations) + salt + iv + ct

def decrypt_bytes(package: bytes, password: bytes, default_iterations: int) -> bytes:
    if len(package) < 1 + 4 + SALT_SIZE + IV_SIZE + 16:
        raise ValueError("Invalid package")
    ver = package[0]
    if ver == PACKAGE_VERSION:
        iterations = struct.unpack(">I", package[1:5])[0]
        salt = package[5:5+SALT_SIZE]
        iv = package[5+SALT_SIZE:5+SALT_SIZE+IV_SIZE]
        ct = package[5+SALT_SIZE+IV_SIZE:]
    else:
        iterations = default_iterations
        salt = package[:SALT_SIZE]
        iv = package[SALT_SIZE:SALT_SIZE+IV_SIZE]
        ct = package[SALT_SIZE+IV_SIZE:]
    key = derive_key(password, salt, iterations)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(iv, ct, None)

def try_base64_decode(text: str):
    try:
        return base64.b64decode(text, validate=True)
    except:
        return None

def read_file_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()

def write_file_bytes(path: str, data: bytes):
    with open(path, "wb") as f:
        f.write(data)

def encrypt_file_stream_to(in_path: str, out_path: str, password: bytes, iterations: int, progress_data: dict = None):
    """Streaming-Verschlüsselung für große Dateien - kompatibel mit Android App."""
    salt = secrets.token_bytes(SALT_SIZE)
    key = derive_key(password, salt, iterations)
    iv = secrets.token_bytes(IV_SIZE)
    encryptor = Cipher(algorithms.AES(key), modes.GCM(iv)).encryptor()
    
    _, ext = os.path.splitext(in_path)
    ext_bytes = ext.encode("utf-8")
    header_block = INTERNAL_MARKER + bytes([len(ext_bytes)]) + ext_bytes
    
    # Dateigröße für Progress
    file_size = os.path.getsize(in_path)
    bytes_processed = 0
    
    if progress_data is not None:
        progress_data['total'] = file_size
        progress_data['processed'] = 0
    
    with open(in_path, "rb") as fin, open(out_path, "wb") as fout:
        # Header schreiben: Version + Iterations + Salt + IV
        fout.write(struct.pack(">B I", PACKAGE_VERSION, iterations))
        fout.write(salt)
        fout.write(iv)
        
        # Header-Block verschlüsseln und schreiben
        enc_header = encryptor.update(header_block)
        fout.write(enc_header)
        
        # Datei chunk-weise verschlüsseln
        while True:
            chunk = fin.read(CHUNK_SIZE)
            if not chunk:
                break
            ct_chunk = encryptor.update(chunk)
            fout.write(ct_chunk)
            
            # Progress aktualisieren
            bytes_processed += len(chunk)
            if progress_data is not None:
                progress_data['processed'] = bytes_processed
        
        # Finalisieren und Auth-Tag schreiben
        encryptor.finalize()
        tag = encryptor.tag
        fout.write(tag)

def decrypt_file_stream_to(in_path: str, out_path_base: str, password: bytes, default_iterations: int, progress_data: dict = None):
    """Streaming-Entschlüsselung für große Dateien - kompatibel mit Android App."""
    from cryptography.exceptions import InvalidTag
    
    with open(in_path, "rb") as fin:
        # Header lesen
        first = fin.read(1)
        if not first:
            raise ValueError("Empty file")
        ver = first[0]
        if ver != PACKAGE_VERSION:
            raise ValueError("Version mismatch in stream")
        
        fin.seek(0)
        header_all = fin.read(1 + 4)
        iterations = struct.unpack(">I", header_all[1:5])[0]
        salt = fin.read(SALT_SIZE)
        iv = fin.read(IV_SIZE)
        
        # Dateigröße und Tag-Position berechnen
        fin_pos = fin.tell()
        fin.seek(0, os.SEEK_END)
        total_size = fin.tell()
        ct_size = total_size - fin_pos
        if ct_size < 16:
            raise ValueError("Corrupt file")
        
        # Auth-Tag vom Ende lesen
        fin.seek(-16, os.SEEK_END)
        tag = fin.read(16)
        
        payload_bytes = ct_size - 16
        fin.seek(fin_pos)
        
        # Progress initialisieren
        bytes_processed = 0
        if progress_data is not None:
            progress_data['total'] = payload_bytes
            progress_data['processed'] = 0
        
        # Entschlüsseler initialisieren
        key = derive_key(password, salt, iterations)
        decryptor = Cipher(algorithms.AES(key), modes.GCM(iv, tag)).decryptor()
        
        # Temporäre Datei für Entschlüsselung (wird nur bei Erfolg umbenannt)
        temp_path = out_path_base + ".tmp_decrypt"
        
        try:
            # Ersten Chunk lesen um Extension zu extrahieren
            first_chunk_size = min(CHUNK_SIZE, payload_bytes)
            chunk = fin.read(first_chunk_size)
            remaining = payload_bytes - len(chunk)
            bytes_processed += len(chunk)
            
            if progress_data is not None:
                progress_data['processed'] = bytes_processed
            
            plain_first_chunk = decryptor.update(chunk)
            
            final_ext = ""
            write_data = plain_first_chunk
            
            # Extension aus Header extrahieren
            if plain_first_chunk.startswith(INTERNAL_MARKER):
                offset = len(INTERNAL_MARKER)
                if offset < len(plain_first_chunk):
                    ext_len = plain_first_chunk[offset]
                    ext_start = offset + 1
                    ext_end = ext_start + ext_len
                    
                    if ext_end <= len(plain_first_chunk):
                        final_ext = plain_first_chunk[ext_start:ext_end].decode("utf-8")
                        write_data = plain_first_chunk[ext_end:]
            
            # Entschlüsselte Daten in temporäre Datei schreiben
            with open(temp_path, "wb") as fout:
                fout.write(write_data)
                
                while remaining > 0:
                    read_len = min(CHUNK_SIZE, remaining)
                    chunk = fin.read(read_len)
                    remaining -= len(chunk)
                    bytes_processed += len(chunk)
                    
                    if progress_data is not None:
                        progress_data['processed'] = bytes_processed
                    
                    plain_chunk = decryptor.update(chunk)
                    fout.write(plain_chunk)
                
                # WICHTIG: finalize() prüft den Auth-Tag!
                # Bei falschem Passwort wird hier InvalidTag geworfen
                decryptor.finalize()
            
            # Nur wenn finalize() erfolgreich war, Datei umbenennen
            final_path = out_path_base
            if final_ext and not final_path.endswith(final_ext):
                final_path += final_ext
            
            # Temporäre Datei zur finalen Datei umbenennen
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(temp_path, final_path)
            
            return final_path
            
        except InvalidTag:
            # Falsches Passwort oder beschädigte Datei!
            # Temporäre Datei löschen falls vorhanden
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise ValueError("Decryption failed: Wrong password, missing keyfile, or corrupted file")
        
        except Exception as e:
            # Bei anderen Fehlern auch aufräumen
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

def encrypt_file_to(in_path: str, out_path: str, password: bytes, iterations: int, progress_data: dict = None):
    """Verschlüsselt Dateien - verwendet immer Streaming für Kompatibilität."""
    encrypt_file_stream_to(in_path, out_path, password, iterations, progress_data)

def decrypt_file_to(in_path: str, out_path: str, password: bytes, default_iterations: int, progress_data: dict = None) -> str:
    """Entschlüsselt Dateien - verwendet immer Streaming für Kompatibilität."""
    return decrypt_file_stream_to(in_path, out_path, password, default_iterations, progress_data)

# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------
def load_settings():
    data = {"language": "en", "dark_mode": False, "opacity": 1.0, "pinned": False, "show_confirm": True}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data.update(json.load(f))
        except:
            pass
    return data

def save_settings(settings):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(settings, f)
    except:
        pass

# ---------------------------------------------------------
# MAIN APP
# ---------------------------------------------------------
def main(page: ft.Page):
    # Load settings
    settings = load_settings()
    
    # WICHTIG: State als Dictionary damit Closures den aktuellen Wert sehen!
    state = {
        "lang_code": settings.get("language", "en"),
        "is_dark": settings.get("dark_mode", False),
        "opacity_val": settings.get("opacity", 1.0),
        "is_pinned": settings.get("pinned", False),
        "keyfile_path": None,
        "selected_file": None,
        "show_confirm_field": settings.get("show_confirm", True),
        "passwords_visible": False,
        # Gespeicherte Eingabewerte für rebuild
        "input_value": "",
        "output_value": "",
        "pass_value": "",
        "pass2_value": "",
        "iter_value": str(ITERATIONS_DEFAULT),
        "file_value": "",
    }
    
    def get_lang():
        return TEXT.get(state["lang_code"], TEXT["en"])
    
    def get_theme():
        return THEME["dark"] if state["is_dark"] else THEME["light"]
    
    # Page setup
    page.title = APP_TITLE
    # Fenster-/Taskleisten-Icon setzen (sonst zeigt die Flutter-Engine ihr eigenes
    # Standard-Logo). Wird als app_icon.ico mit der EXE gebuendelt (--add-data im Build).
    try:
        _win_icon = resource_path("app_icon.ico")
        if os.path.exists(_win_icon):
            page.window.icon = _win_icon
    except Exception:
        pass
    page.window.width = 1100
    page.window.height = 700
    page.window.min_width = 800
    page.window.min_height = 550
    page.padding = 0
    page.spacing = 0
    page.window.always_on_top = state["is_pinned"]
    page.window.opacity = state["opacity_val"]
    
    def apply_theme():
        t = get_theme()
        page.bgcolor = t["bg"]
        page.theme_mode = ft.ThemeMode.DARK if state["is_dark"] else ft.ThemeMode.LIGHT
        page.update()
    
    apply_theme()
    
    # ----- UI Components -----
    
    def show_snackbar(msg: str, color: str = None):
        t = get_theme()
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color=ft.Colors.WHITE),
            bgcolor=color or t["primary"],
            duration=2000
        )
        page.snack_bar.open = True
        page.update()
    
    def show_error(msg: str):
        show_snackbar(msg, get_theme()["danger"])
    
    def show_error_dialog(title: str, message: str):
        """Zeigt einen schönen Fehler-Dialog mit OK-Button an."""
        def close_dialog(e):
            error_dialog.open = False
            page.update()
        
        error_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.ERROR_OUTLINE, color=get_theme()["danger"], size=28),
                ft.Text(title, weight="bold"),
            ], spacing=10),
            content=ft.Text(message, size=14),
            actions=[
                ft.FilledButton(
                    "OK",
                    on_click=close_dialog,
                    style=ft.ButtonStyle(
                        bgcolor=get_theme()["primary"],
                        color=ft.Colors.WHITE,
                    ),
                ),
            ],
            actions_alignment="center",
        )
        
        page.overlay.append(error_dialog)
        error_dialog.open = True
        page.update()
    
    # Input area
    txt_input = ft.TextField(
        multiline=True,
        min_lines=12,
        border_radius=12,
        filled=True,
        hint_text="Enter text here...",
        expand=True,
        text_align=ft.TextAlign.LEFT,
    )
    
    # File display
    txt_file = ft.TextField(
        read_only=True,
        border_radius=12,
        filled=True,
        hint_text="No file selected...",
        expand=True,
        height=38,
        content_padding=8,
        text_size=11,
    )
    
    # Password fields
    txt_pass = ft.TextField(
        password=True,
        border_radius=12,
        filled=True,
        hint_text="Password",
        expand=True,
        height=42,
        content_padding=10,
    )
    
    txt_pass2 = ft.TextField(
        password=True,
        border_radius=12,
        filled=True,
        hint_text="Confirm",
        expand=True,
        height=42,
        content_padding=10,
        visible=state["show_confirm_field"],  # Aus Settings laden
    )
    
    # Iterations
    txt_iter = ft.TextField(
        value=str(ITERATIONS_DEFAULT),
        width=100,
        border_radius=12,
        filled=True,
        text_align=ft.TextAlign.CENTER,
        height=42,
        content_padding=10,
        text_size=12,
    )
    
    # Output area
    txt_output = ft.TextField(
        multiline=True,
        min_lines=12,
        read_only=True,
        border_radius=12,
        filled=True,
        expand=True,
    )
    
    # Keyfile button
    btn_keyfile = ft.FilledButton(
        content=ft.Text(get_lang()["keyfile_btn"], size=12),
        icon=ft.Icons.KEY,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding(12, 0, 12, 0),
        ),
        height=42,
    )
    
    # Confirm Checkbox - Wert aus Settings laden
    chk_confirm = ft.Checkbox(
        label=get_lang()["confirm_check"],
        value=state["show_confirm_field"],
    )
    
    # Opacity Slider
    opacity_slider = ft.Slider(
        min=0.3,
        max=1.0,
        value=state["opacity_val"],
        width=100,
        divisions=14,
    )
    
    # ----- File Picker (Flet 0.70+ - müssen in page.services sein!) -----
    file_picker = ft.FilePicker()
    save_picker = ft.FilePicker()
    import_picker = ft.FilePicker()
    keyfile_picker = ft.FilePicker()
    qr_save_picker = ft.FilePicker()
    qr_import_picker = ft.FilePicker()  # Für QR-Code Import
    qr_image_data = [None]  # Liste als Container für die QR-Bilddaten (mutable)
    
    # Flet 0.70+: FilePicker werden über page.services hinzugefügt!
    page.services.append(file_picker)
    page.services.append(save_picker)
    page.services.append(import_picker)
    page.services.append(keyfile_picker)
    page.services.append(qr_save_picker)
    page.services.append(qr_import_picker)
    
    # Note: In Flet 0.70+ werden die Ergebnisse direkt von await zurückgegeben,
    # daher sind on_result Callbacks nicht mehr nötig für die meisten Operationen
    
    # ----- Password Generator Dialog -----
    def show_generator_dialog(e):
        lang = get_lang()
        gen_length = 32
        
        length_text = ft.Text(lang["gen_length"].format(gen_length))
        
        def on_slider_change(e):
            nonlocal gen_length
            gen_length = int(e.control.value)
            length_text.value = lang["gen_length"].format(gen_length)
            page.update()
        
        chk_lower = ft.Checkbox(label=lang["gen_lower"], value=True)
        chk_upper = ft.Checkbox(label=lang["gen_upper"], value=True)
        chk_digits = ft.Checkbox(label=lang["gen_digits"], value=True)
        chk_symbols = ft.Checkbox(label=lang["gen_symbols"], value=True)
        
        def generate_and_apply(e):
            chars = ""
            if chk_lower.value: chars += string.ascii_lowercase
            if chk_upper.value: chars += string.ascii_uppercase
            if chk_digits.value: chars += string.digits
            if chk_symbols.value: chars += "!@#$%^&*()-_=+"
            
            if chars:
                pwd = ''.join(secrets.choice(chars) for _ in range(gen_length))
                txt_pass.value = pwd
                txt_pass2.value = pwd
                dialog.open = False
                page.update()
                show_snackbar("Password generated!")
        
        def close_dialog(e):
            dialog.open = False
            page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(lang["gen_title"]),
            content=ft.Container(
                width=350,
                content=ft.Column([
                    length_text,
                    ft.Slider(min=8, max=64, value=32, divisions=56, on_change=on_slider_change),
                    ft.Divider(height=10),
                    chk_lower,
                    chk_upper,
                    chk_digits,
                    chk_symbols,
                ], tight=True, spacing=5)
            ),
            actions=[
                ft.TextButton(content=ft.Text(lang["gen_cancel"]), on_click=close_dialog),
                ft.FilledButton(content=ft.Text(lang["gen_apply"]), on_click=generate_and_apply),
            ],
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
    
    # ----- Core Functions -----
    
    def get_password_bytes():
        pw = txt_pass.value.encode("utf-8")
        if state["keyfile_path"]:
            # Keyfile ist gesetzt -> Lesefehler NICHT verschlucken. Sonst wuerde
            # still nur mit dem Passwort ver-/entschluesselt (schwaecherer Schutz
            # als gedacht). Lieber hart abbrechen und den Nutzer informieren.
            if not os.path.exists(state["keyfile_path"]):
                raise ValueError("Keyfile not found: " + str(state["keyfile_path"]))
            kf_data = read_file_bytes(state["keyfile_path"])
            kf_hash = hashlib.sha256(kf_data).digest()
            return pw + kf_hash
        return pw
    
    def get_iterations():
        try:
            return max(int(txt_iter.value), 1)
        except:
            return ITERATIONS_DEFAULT
    
    async def on_encrypt(e):
        # state dict used
        lang = get_lang()
        pw = txt_pass.value
        if not pw:
            show_error(lang["no_input"])
            return
        
        # Nur prüfen wenn Confirm-Feld sichtbar/aktiviert ist
        if state["show_confirm_field"] and txt_pass2.value != pw:
            show_error_dialog("Password Mismatch", lang["pass_mismatch"])
            return
        
        if len(pw) < 8:
            show_snackbar(lang["weak_password"], get_theme()["danger"])

        try:
            pw_bytes = get_password_bytes()
        except Exception:
            show_error_dialog(
                lang.get("decrypt_failed_title", "Error"),
                lang.get("keyfile_error", "Keyfile could not be read – operation cancelled.")
            )
            return
        iterations = get_iterations()
        
        if state["selected_file"] and os.path.exists(state["selected_file"]):
            # In Flet 0.70+ gibt save_file() direkt den Pfad zurück
            result = await save_picker.save_file(
                dialog_title="Save encrypted file",
                file_name=f"encrypted_{int(time.time())}.bin"
            )
            
            if result:
                # Dateigröße für Anzeige
                file_size = os.path.getsize(state["selected_file"])
                file_size_mb = file_size / (1024 * 1024)
                
                # Progress-Tracking Dictionary
                progress_data = {'total': file_size, 'processed': 0}
                
                # Fortschritts-Dialog erstellen
                progress_text = ft.Text(f"0% - 0.00 MB / {file_size_mb:.2f} MB", size=12)
                progress_bar = ft.ProgressBar(width=300, value=0)
                
                progress_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Encrypting..."),
                    content=ft.Column([
                        ft.ProgressRing(),
                        progress_bar,
                        progress_text,
                    ], horizontal_alignment="center", tight=True, spacing=15),
                )
                page.overlay.append(progress_dialog)
                progress_dialog.open = True
                page.update()
                
                try:
                    # Fortschritt in separatem Task aktualisieren
                    async def update_progress():
                        while progress_data['processed'] < progress_data['total']:
                            total = progress_data['total']
                            processed = progress_data['processed']
                            percent = (processed / total) * 100 if total > 0 else 0
                            mb_processed = processed / (1024 * 1024)
                            total_mb = total / (1024 * 1024)
                            progress_bar.value = percent / 100
                            progress_text.value = f"{percent:.1f}% - {mb_processed:.2f} MB / {total_mb:.2f} MB"
                            page.update()
                            await asyncio.sleep(0.1)
                    
                    # Führe Verschlüsselung im Thread aus
                    loop = asyncio.get_event_loop()
                    progress_task = asyncio.create_task(update_progress())
                    
                    await loop.run_in_executor(
                        None,
                        lambda: encrypt_file_to(state["selected_file"], result, pw_bytes, iterations, progress_data)
                    )
                    
                    progress_task.cancel()
                    
                    # Schließe Ladeindikator
                    progress_dialog.open = False
                    page.update()
                    
                    txt_output.value = lang["file_encrypted"].format(result)
                    page.update()
                except Exception as err:
                    # Schließe Ladeindikator bei Fehler
                    progress_dialog.open = False
                    page.update()
                    show_error(str(err))
            return
        
        text = txt_input.value.strip()
        if text:
            try:
                enc = encrypt_bytes(text.encode("utf-8"), pw_bytes, iterations)
                txt_output.value = base64.b64encode(enc).decode("ascii")
                page.update()
            except Exception as err:
                show_error(str(err))
        else:
            show_error(lang["no_input"])
    
    async def on_decrypt(e):
        # state dict used
        lang = get_lang()
        pw = txt_pass.value
        if not pw:
            show_error(lang["no_input"])
            return

        try:
            pw_bytes = get_password_bytes()
        except Exception:
            show_error_dialog(
                lang.get("decrypt_failed_title", "Error"),
                lang.get("keyfile_error", "Keyfile could not be read – operation cancelled.")
            )
            return
        iterations = get_iterations()
        
        if state["selected_file"] and os.path.exists(state["selected_file"]):
            # In Flet 0.70+ gibt save_file() direkt den Pfad zurück
            result = await save_picker.save_file(
                dialog_title="Save decrypted file",
                file_name=f"decrypted_{int(time.time())}"
            )
            
            if result:
                # Dateigröße für Anzeige
                file_size = os.path.getsize(state["selected_file"])
                file_size_mb = file_size / (1024 * 1024)
                
                # Progress-Tracking Dictionary
                progress_data = {'total': file_size, 'processed': 0}
                
                # Fortschritts-Dialog erstellen
                progress_text = ft.Text(f"0% - 0.00 MB / {file_size_mb:.2f} MB", size=12)
                progress_bar = ft.ProgressBar(width=300, value=0)
                
                progress_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Decrypting..."),
                    content=ft.Column([
                        ft.ProgressRing(),
                        progress_bar,
                        progress_text,
                    ], horizontal_alignment="center", tight=True, spacing=15),
                )
                page.overlay.append(progress_dialog)
                progress_dialog.open = True
                page.update()
                
                try:
                    # Fortschritt in separatem Task aktualisieren
                    async def update_progress():
                        while progress_data['processed'] < progress_data['total']:
                            total = progress_data['total']
                            processed = progress_data['processed']
                            percent = (processed / total) * 100 if total > 0 else 0
                            mb_processed = processed / (1024 * 1024)
                            total_mb = total / (1024 * 1024)
                            progress_bar.value = percent / 100
                            progress_text.value = f"{percent:.1f}% - {mb_processed:.2f} MB / {total_mb:.2f} MB"
                            page.update()
                            await asyncio.sleep(0.1)
                    
                    # Führe Entschlüsselung im Thread aus
                    loop = asyncio.get_event_loop()
                    progress_task = asyncio.create_task(update_progress())
                    
                    final_path = await loop.run_in_executor(
                        None,
                        lambda: decrypt_file_to(state["selected_file"], result, pw_bytes, iterations, progress_data)
                    )
                    
                    progress_task.cancel()
                    
                    # Schließe Ladeindikator
                    progress_dialog.open = False
                    page.update()
                    
                    txt_output.value = lang["file_decrypted"].format(final_path)
                    page.update()
                except Exception as err:
                    # Schließe Ladeindikator bei Fehler
                    progress_task.cancel()
                    progress_dialog.open = False
                    page.update()
                    
                    # Zeige detaillierte Fehlermeldung
                    error_msg = str(err)
                    if "Wrong password" in error_msg or "InvalidTag" in error_msg or "InvalidTag" in type(err).__name__:
                        show_error_dialog(
                            lang.get("decrypt_failed_title", "Decryption Failed"), 
                            lang.get("decrypt_file_wrong_password", "Wrong password!\n\nThe file could not be decrypted. Please check:\n• Is the password correct?\n• Did you use a keyfile when encrypting?\n• Is the file complete and unmodified?")
                        )
                    else:
                        show_error_dialog(lang.get("decrypt_failed_title", "Decryption Failed"), f"{lang.get('error', 'Error: {0}').format(error_msg)}")
            return
        
        text = txt_input.value.strip()
        if text:
            try:
                mb = try_base64_decode(text)
                if mb is None:
                    # Text ist kein gültiges Base64
                    show_error_dialog(
                        lang.get("decrypt_failed_title", "Decryption Failed"),
                        lang.get("decrypt_invalid_input", "The input is not valid encrypted data.\n\nMake sure you copied the complete encrypted text (Base64 format).")
                    )
                    return
                
                inp = mb
                dec = decrypt_bytes(inp, pw_bytes, iterations)
                try:
                    txt_output.value = dec.decode("utf-8")
                except:
                    txt_output.value = base64.b64encode(dec).decode("ascii")
                page.update()
            except ValueError as err:
                # Ungültiges Paket-Format
                error_msg = str(err)
                if "Invalid package" in error_msg:
                    show_error_dialog(
                        lang.get("decrypt_failed_title", "Decryption Failed"),
                        lang.get("decrypt_invalid_format", "The data format is invalid or corrupted.\n\nThis doesn't look like data encrypted with TEE Encryption.")
                    )
                else:
                    show_error_dialog(lang.get("decrypt_failed_title", "Decryption Failed"), f"{lang.get('error', 'Error: {0}').format(error_msg)}")
            except Exception as err:
                # Zeige detaillierte Fehlermeldung auch für Nachrichten
                error_msg = str(err)
                if "InvalidTag" in error_msg or "tag" in error_msg.lower() or "InvalidTag" in type(err).__name__:
                    show_error_dialog(
                        lang.get("decrypt_failed_title", "Decryption Failed"), 
                        lang.get("decrypt_wrong_password", "Wrong password!\n\nThe decryption failed. Please check:\n• Is the password correct?\n• Did you use a keyfile when encrypting?\n• Is the encrypted text complete and unmodified?")
                    )
                else:
                    show_error_dialog(lang.get("decrypt_failed_title", "Decryption Failed"), f"{lang.get('error', 'Error: {0}').format(error_msg)}")
        else:
            show_error(lang["no_input"])
    
    def on_copy(e):
        if txt_output.value:
            try:
                # Windows clipboard via subprocess
                import subprocess
                process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
                process.communicate(txt_output.value.encode('utf-8'))
                show_snackbar(get_lang()["copied"])
            except Exception:
                # Fallback: Try pyperclip
                try:
                    import pyperclip
                    pyperclip.copy(txt_output.value)
                    show_snackbar(get_lang()["copied"])
                except ImportError:
                    page.set_clipboard(txt_output.value)
                    show_snackbar(get_lang()["copied"])
    
    def on_swap(e):
        txt_input.value = txt_output.value
        txt_output.value = ""
        # state dict used
        state["selected_file"] = None
        txt_file.value = ""
        page.update()
    
    def on_clear(e):
        # state dict used
        txt_input.value = ""
        txt_output.value = ""
        txt_pass.value = ""
        txt_pass2.value = ""
        txt_file.value = ""
        state["selected_file"] = None
        page.update()
    
    async def on_save_output(e):
        if not txt_output.value:
            return
        
        # In Flet 0.70+ gibt save_file() direkt den Pfad zurück
        result = await save_picker.save_file(
            file_name=f"output_{int(time.time())}.txt"
        )
        
        if result:
            try:
                with open(result, "w", encoding="utf-8") as f:
                    f.write(txt_output.value)
                show_snackbar(get_lang()["saved"])
            except Exception as err:
                show_error(str(err))
    
    def toggle_theme(e):
        state["is_dark"] = not state["is_dark"]
        settings["dark_mode"] = state["is_dark"]
        save_settings(settings)
        apply_theme()
        rebuild_ui()
    
    def change_language_to(new_lang):
        """Ändert die Sprache zum angegebenen Code"""
        if new_lang and new_lang != state["lang_code"]:
            state["lang_code"] = new_lang
            settings["language"] = new_lang
            save_settings(settings)
            rebuild_ui()
            # Bestätigung anzeigen
            lang_names = {"en": "English", "de": "Deutsch", "es": "Español", "fr": "Français"}
            show_snackbar(f"✓ {lang_names.get(new_lang, new_lang)}")
    
    async def toggle_keyfile(e):
        if state["keyfile_path"]:
            state["keyfile_path"] = None
            btn_keyfile.content.value = get_lang()["keyfile_btn"]
            btn_keyfile.bgcolor = None
            show_snackbar(get_lang()["keyfile_removed"])
            page.update()
        else:
            # In Flet 0.70+ gibt pick_files() direkt die Liste der Dateien zurück
            result = await keyfile_picker.pick_files(dialog_title="Select Keyfile")
            if result:
                state["keyfile_path"] = result[0].path
                btn_keyfile.content.value = get_lang()["keyfile_active"]
                btn_keyfile.style.bgcolor = get_theme()["success"]
                show_snackbar("Keyfile loaded")
                page.update()
    
    btn_keyfile.on_click = toggle_keyfile
    
    # Toggle confirm password field visibility
    def toggle_confirm(e):
        state["show_confirm_field"] = chk_confirm.value
        txt_pass2.visible = state["show_confirm_field"]
        # Wenn deaktiviert, Feld leeren um alte Werte zu entfernen
        if not state["show_confirm_field"]:
            txt_pass2.value = ""
        # In Settings speichern
        settings["show_confirm"] = state["show_confirm_field"]
        save_settings(settings)
        page.update()
    
    chk_confirm.on_change = toggle_confirm
    
    # Single eye toggle for both password fields
    def toggle_password_visibility(e):
        state["passwords_visible"] = not state["passwords_visible"]
        txt_pass.password = not state["passwords_visible"]
        txt_pass2.password = not state["passwords_visible"]
        # Rebuild UI um das Icon zu aktualisieren
        rebuild_ui()
    
    # Hash checkbox handler
    def show_hash_dialog(subtitle: str, hash_hex: str, extra: str = ""):
        """Zeigt einen SHA-256-Hash in einem Pop-up mit Kopieren-Knopf."""
        body = (extra + "\n\n" if extra else "") + hash_hex
        hash_field = ft.TextField(
            value=body, read_only=True, multiline=True, min_lines=2, max_lines=5,
            border_radius=10, filled=True, text_size=12,
        )
        def copy_hash(e):
            try:
                import subprocess
                proc = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
                proc.communicate(hash_hex.encode('utf-8'))
                show_snackbar(get_lang()["copied"])
            except Exception:
                pass
        def close_dlg(e):
            dlg.open = False
            page.update()
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.TAG, color=get_theme()["primary"], size=24),
                ft.Text("SHA-256 - " + subtitle, weight="bold"),
            ], spacing=10),
            content=ft.Container(width=540, content=ft.Column([hash_field], tight=True)),
            actions=[
                ft.TextButton(content=ft.Text(get_lang()["copy_btn"]), on_click=copy_hash),
                ft.FilledButton("OK", on_click=close_dlg),
            ],
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    async def on_hash_input(e):
        lang = get_lang()
        # Datei hat Vorrang, wenn eine ausgewaehlt ist; sonst Text-Eingabe
        if state["selected_file"] and os.path.exists(state["selected_file"]):
            file_size = os.path.getsize(state["selected_file"])
            file_size_mb = file_size / (1024 * 1024)
            progress_text = ft.Text("0% - 0.00 MB / {:.2f} MB".format(file_size_mb), size=12)
            progress_bar = ft.ProgressBar(width=300, value=0)
            progress_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Calculating Hash..."),
                content=ft.Column([
                    ft.ProgressRing(), progress_bar, progress_text,
                ], horizontal_alignment="center", tight=True, spacing=15),
            )
            page.overlay.append(progress_dialog)
            progress_dialog.open = True
            page.update()

            sha = hashlib.sha256()
            bytes_read = 0
            chunk_size = 1024 * 1024

            def calculate_hash():
                nonlocal bytes_read
                with open(state["selected_file"], "rb") as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        sha.update(chunk)
                        bytes_read += len(chunk)

            loop = asyncio.get_event_loop()
            async def update_progress():
                while bytes_read < file_size:
                    percent = (bytes_read / file_size) * 100 if file_size > 0 else 0
                    mb_read = bytes_read / (1024 * 1024)
                    progress_bar.value = percent / 100
                    progress_text.value = f"{percent:.1f}% - {mb_read:.2f} MB / {file_size_mb:.2f} MB"
                    page.update()
                    await asyncio.sleep(0.1)

            progress_task = asyncio.create_task(update_progress())
            await loop.run_in_executor(None, calculate_hash)
            progress_task.cancel()
            progress_dialog.open = False
            page.update()

            fname = os.path.basename(state["selected_file"])
            extra = "FILE: {}  ({:.2f} MB)".format(fname, file_size_mb)
            show_hash_dialog("Input (Datei)", sha.hexdigest(), extra)
        elif txt_input.value:
            h = hashlib.sha256(txt_input.value.encode("utf-8")).hexdigest()
            show_hash_dialog("Input", h)
        else:
            show_error(lang["no_input"])

    def on_hash_output(e):
        lang = get_lang()
        if txt_output.value:
            h = hashlib.sha256(txt_output.value.encode("utf-8")).hexdigest()
            show_hash_dialog("Output", h)
        else:
            show_error(lang["no_input"])
    
    # Opacity slider handler
    def on_opacity_change(e):
        state["opacity_val"] = e.control.value
        page.window.opacity = state["opacity_val"]
        settings["opacity"] = state["opacity_val"]
        save_settings(settings)
    
    opacity_slider.on_change = on_opacity_change
    
    # Pin/Unpin window handler
    def toggle_pin(e):
        state["is_pinned"] = not state["is_pinned"]
        page.window.always_on_top = state["is_pinned"]
        settings["pinned"] = state["is_pinned"]
        save_settings(settings)
        rebuild_ui()
    
    # Exit button handler
    async def on_exit(e):
        await page.window.close()
    
    # QR button handler - shows QR code in a BottomSheet with Save option
    def on_qr(e):
        output_text = txt_output.value
        
        if not output_text:
            show_snackbar("No output to generate QR code from!")
            return
        
        if len(output_text) > 2000:
            show_snackbar("Data too long for QR code (max ~2000 chars)")
            return
        
        if not HAS_QRCODE:
            show_snackbar("QR library not installed. Run: pip install qrcode[pil]")
            return
        
        try:
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(output_text)
            qr.make(fit=True)
            
            # Create PIL Image
            img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
            
            # Convert to bytes for saving
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            qr_image_data[0] = buffer.getvalue()  # Speichere in der Liste
            
            # Convert to base64 for display
            img_base64 = base64.b64encode(qr_image_data[0]).decode('utf-8')
            
            # Close function
            def close_dialog(ev):
                qr_dialog.open = False
                page.update()
            
            # Save function - async für Flet 0.70+
            async def save_qr(ev):
                result = await qr_save_picker.save_file(
                    dialog_title="Save QR Code",
                    file_name="qrcode.png",
                    allowed_extensions=["png"]
                )
                if result and qr_image_data[0]:
                    try:
                        with open(result, "wb") as f:
                            f.write(qr_image_data[0])
                        show_snackbar(f"QR Code saved: {result}")
                    except Exception as err:
                        show_snackbar(f"Save error: {err}")
            
            # Create centered AlertDialog with X button
            qr_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    controls=[
                        ft.Text("QR Code", size=18, weight="bold", expand=True),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_size=20,
                            on_click=close_dialog,
                            tooltip="Close",
                        ),
                    ],
                    alignment="spaceBetween",
                ),
                content=ft.Container(
                    width=320,
                    content=ft.Column(
                        horizontal_alignment="center",
                        controls=[
                            ft.Container(
                                bgcolor="#FFFFFF",
                                padding=10,
                                border_radius=10,
                                content=ft.Image(
                                    src=f"data:image/png;base64,{img_base64}",
                                    width=250,
                                    height=250,
                                ),
                            ),
                            ft.Container(height=15),
                            ft.Button(
                                "💾 Save PNG",
                                on_click=save_qr,
                            ),
                        ],
                        tight=True,
                    ),
                ),
            )
            
            # Open dialog
            page.overlay.append(qr_dialog)
            qr_dialog.open = True
            page.update()
            
        except Exception as err:
            import traceback
            traceback.print_exc()
            show_snackbar(f"QR Error: {str(err)}")
    
    # Import .txt handler
    async def on_import_txt(e):
        # In Flet 0.70+ gibt pick_files() direkt die Liste der Dateien zurück
        result = await import_picker.pick_files(allowed_extensions=["txt"])
        if result and len(result) > 0:
            try:
                with open(result[0].path, "r", encoding="utf-8") as f:
                    txt_input.value = f.read()
                page.update()
            except Exception as err:
                show_error(str(err))
    
    # File button handler
    async def on_file_btn_click(e):
        # state dict used
        # In Flet 0.70+ gibt pick_files() direkt die Liste der Dateien zurück
        result = await file_picker.pick_files()
        if result and len(result) > 0:
            state["selected_file"] = result[0].path
            txt_file.value = state["selected_file"]
            txt_input.value = ""
            page.update()
    
    # Clear file button handler - löscht sowohl Anzeige ALS AUCH selected_file
    def on_clear_file(e):
        # state dict used
        state["selected_file"] = None
        txt_file.value = ""
        page.update()
    
    # QR-Code Import Handler - liest QR-Code aus Bilddatei
    async def on_import_qr(e):
        if not HAS_QR_READER:
            show_error_dialog("Missing Library", "QR Reader not installed.\nRun: pip install pyzbar pillow")
            return
        
        # Bilddatei auswählen
        result = await qr_import_picker.pick_files(
            allowed_extensions=["png", "jpg", "jpeg", "gif", "bmp", "webp"]
        )
        
        if result and len(result) > 0:
            try:
                # Bild öffnen und QR-Code dekodieren
                img = Image.open(result[0].path)
                decoded = decode_qr(img)
                
                if decoded:
                    # QR-Code gefunden - Text ins Eingabefeld einfügen
                    qr_text = decoded[0].data.decode('utf-8')
                    txt_input.value = qr_text
                    page.update()
                    show_snackbar("✓ QR Code imported successfully")
                else:
                    show_error_dialog("No QR Code Found", "Could not find a QR code in the selected image.")
            except Exception as err:
                show_error_dialog("Import Error", f"Failed to read QR code:\n{str(err)}")
    
    # ----- Build UI -----
    
    def build_ui():
        lang = get_lang()
        t = get_theme()
        
        # Sprach-Auswahl als PopupMenuButton (zuverlässiger als Dropdown!)
        lang_names_short = {
            "en": "EN", "de": "DE", "es": "ES", "fr": "FR",
            "tr": "TR", "ru": "RU", "ar": "AR", "ja": "JA", "zh": "ZH"
        }
        current_lang_short = lang_names_short.get(state["lang_code"], "EN")
        
        lang_menu = ft.PopupMenuButton(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Text(current_lang_short, size=14, weight=ft.FontWeight.BOLD),
                        ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=18),
                    ],
                    spacing=2,
                    tight=True,
                ),
                padding=ft.Padding(left=10, right=10, top=6, bottom=6),
                border_radius=10,
                border=ft.Border(
                    left=ft.BorderSide(1, t["border"]),
                    right=ft.BorderSide(1, t["border"]),
                    top=ft.BorderSide(1, t["border"]),
                    bottom=ft.BorderSide(1, t["border"]),
                ),
            ),
            items=[
                ft.PopupMenuItem(content=ft.Text("English"), on_click=lambda e: change_language_to("en")),
                ft.PopupMenuItem(content=ft.Text("Deutsch"), on_click=lambda e: change_language_to("de")),
                ft.PopupMenuItem(content=ft.Text("Español"), on_click=lambda e: change_language_to("es")),
                ft.PopupMenuItem(content=ft.Text("Français"), on_click=lambda e: change_language_to("fr")),
                ft.PopupMenuItem(content=ft.Text("Türkçe"), on_click=lambda e: change_language_to("tr")),
                ft.PopupMenuItem(content=ft.Text("Русский"), on_click=lambda e: change_language_to("ru")),
                ft.PopupMenuItem(content=ft.Text("العربية"), on_click=lambda e: change_language_to("ar")),
                ft.PopupMenuItem(content=ft.Text("日本語"), on_click=lambda e: change_language_to("ja")),
                ft.PopupMenuItem(content=ft.Text("中文"), on_click=lambda e: change_language_to("zh")),
            ],
        )
        
        # Pin Button - rounded, replaced Elevated with Filled for modern look
        btn_pin = ft.FilledButton(
            content=ft.Text(lang["unpin_btn"] if state["is_pinned"] else lang["pin_btn"], size=11),
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=10),
            height=36,
            on_click=toggle_pin,
        )
        
        # Exit Button (Red) - rounded
        btn_exit = ft.FilledButton(
            content=ft.Text(lang["exit_btn"], size=11),
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                bgcolor=t["danger"],
                color=ft.Colors.WHITE,
                padding=10,
            ),
            height=36,
            on_click=on_exit,
        )

        # ===== HEADER =====
        header = ft.Container(
            padding=ft.Padding(left=20, top=12, right=20, bottom=12),
            bgcolor=t["card"],
            border=ft.Border(bottom=ft.BorderSide(1, t["border"])),
            content=ft.Row([
                # Left: Logo & Title
                ft.Row([
                    ft.Icon(ft.Icons.LOCK_OUTLINE, size=28, color=t["primary"]),
                    ft.Text(APP_TITLE, size=20, weight=ft.FontWeight.BOLD, color=t["text"]),
                ], spacing=12),
                # Right: Controls
                ft.Row([
                    ft.Text(lang["opacity"], size=11, color=t["text_sub"]),
                    opacity_slider,
                    ft.VerticalDivider(width=15),
                    lang_menu,
                    ft.IconButton(
                        icon=ft.Icons.DARK_MODE if not state["is_dark"] else ft.Icons.LIGHT_MODE,
                        tooltip=lang["dark_mode"] if not state["is_dark"] else lang["light_mode"],
                        on_click=toggle_theme,
                        icon_size=20,
                    ),
                    btn_pin,
                    btn_exit,
                ], spacing=10),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        )
        
        # ===== INPUT SECTION (Top ~50%) - Rounded card =====
        input_container = ft.Container(
            padding=15,
            bgcolor=t["card"],
            border_radius=16,
            expand=True,
            content=ft.Column([
                # Label row with file selector and QR import
                ft.Row([
                    ft.Text(lang["input_label"], size=13, weight=ft.FontWeight.BOLD, color=t["text_sub"]),
                    ft.FilledButton(
                        content=ft.Row([
                            ft.Text("Import", size=11),
                            ft.Icon(ft.Icons.QR_CODE_SCANNER, size=16),
                        ], spacing=5, tight=True),
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=10),
                        height=38,
                        on_click=on_import_qr,
                        tooltip="Import QR Code from image",
                    ),
                    ft.FilledButton(
                        content=ft.Row([
                            ft.Text(lang["hash_btn"], size=11),
                            ft.Icon(ft.Icons.TAG, size=16),
                        ], spacing=5, tight=True),
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=10),
                        height=38,
                        on_click=on_hash_input,
                        tooltip="SHA-256 vom Input (Text oder Datei)",
                    ),
                    ft.Container(expand=True),
                    txt_file,
                    ft.FilledButton(
                        content=ft.Text(lang["file_btn"], size=11),
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=10),
                        height=38,
                        on_click=on_file_btn_click,
                    ),
                    ft.IconButton(icon=ft.Icons.CLEAR, icon_size=18, tooltip="Clear file", 
                                  on_click=on_clear_file),
                ], spacing=10),
                # Input TextField (expands to fill)
                txt_input
            ], spacing=10, expand=True),
        )
        
        # ===== CONTROLS SECTION (Middle - Fixed Height) - Rounded card =====
        controls_container = ft.Container(
            padding=15,
            bgcolor=t["card"],
            border_radius=16,
            content=ft.Column([
                # Password Row
                ft.Row([
                    txt_pass,
                    txt_pass2,
                    # Single Eye Button for both fields
                    ft.IconButton(
                        icon=ft.Icons.VISIBILITY_OFF if not state["passwords_visible"] else ft.Icons.VISIBILITY,
                        icon_size=22,
                        tooltip="Toggle visibility",
                        on_click=toggle_password_visibility,
                    ),
                    chk_confirm,
                    ft.VerticalDivider(width=10),
                    btn_keyfile,
                    ft.FilledButton(
                        content=ft.Text(lang["gen_btn"], size=11),
                        icon=ft.Icons.AUTO_AWESOME,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=10),
                        height=42,
                        on_click=show_generator_dialog,
                    ),
                    ft.VerticalDivider(width=10),
                    ft.Text(lang["iterations"], size=11, color=t["text_sub"]),
                    txt_iter,
                ], spacing=10),
                
                # Action Buttons Row - with Icons
                ft.Row([
                    ft.FilledButton(
                        content=ft.Text(lang["encrypt_btn"], size=13, weight=ft.FontWeight.BOLD),
                        style=ft.ButtonStyle(
                            bgcolor=t["primary"], 
                            color=ft.Colors.WHITE,
                            shape=ft.RoundedRectangleBorder(radius=12), 
                            padding=18
                        ),
                        height=48,
                        expand=True,
                        on_click=on_encrypt,
                    ),
                    ft.FilledButton(
                        content=ft.Text(lang["decrypt_btn"], size=13, weight=ft.FontWeight.BOLD),
                        style=ft.ButtonStyle(
                            bgcolor=t["primary"],
                            color=ft.Colors.WHITE,
                            shape=ft.RoundedRectangleBorder(radius=12), 
                            padding=18
                        ),
                        height=48,
                        expand=True,
                        on_click=on_decrypt,
                    ),
                    ft.VerticalDivider(width=20),
                    # Icon Buttons like first version
                    ft.IconButton(icon=ft.Icons.CONTENT_COPY, icon_size=22, tooltip=lang["copy_btn"], on_click=on_copy),
                    ft.IconButton(icon=ft.Icons.FILE_OPEN, icon_size=22, tooltip=lang.get("import_txt_btn", "Import"), on_click=on_import_txt),
                    ft.IconButton(icon=ft.Icons.SAVE_ALT, icon_size=22, tooltip=lang.get("save_txt_btn", "Save"), on_click=on_save_output),
                    ft.IconButton(icon=ft.Icons.SWAP_VERT, icon_size=22, tooltip=lang["swap_btn"], on_click=on_swap),
                    ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_size=22, tooltip=lang["clear_btn"], on_click=on_clear, icon_color=t["danger"]),
                ], spacing=10),
            ], spacing=12),
        )
        
        # ===== OUTPUT SECTION (Bottom ~50%) - Rounded card =====
        output_container = ft.Container(
            padding=15,
            bgcolor=t["card"],
            border_radius=16,
            expand=True,
            content=ft.Column([
                # Label row with QR & Hash
                ft.Row([
                    ft.Text(lang["output_label"], size=13, weight=ft.FontWeight.BOLD, color=t["text_sub"]),
                    ft.Container(expand=True),
                    ft.FilledButton(
                        content=ft.Text(lang["qr_btn"], size=11),
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=8),
                        height=32,
                        on_click=on_qr,
                    ),
                    ft.FilledButton(
                        content=ft.Row([
                            ft.Text(lang["hash_btn"], size=11),
                            ft.Icon(ft.Icons.TAG, size=16),
                        ], spacing=5, tight=True),
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), padding=8),
                        height=32,
                        on_click=on_hash_output,
                        tooltip="SHA-256 vom Output",
                    ),
                ], spacing=12),
                # Output area (expands to fill)
                ft.Row([
                    txt_output,
                ], spacing=12, expand=True),
            ], spacing=10, expand=True),
        )
        
        # ===== MAIN LAYOUT =====
        return ft.Column([
            header,
            ft.Container(
                expand=True,
                padding=15,
                content=ft.Column([
                    input_container,
                    controls_container,
                    output_container,
                ], spacing=12, expand=True),
            ),
        ], spacing=0, expand=True)
    
    def rebuild_ui():
        # Aktualisiere alle sprachabhängigen Texte
        lang = get_lang()
        
        # Textfeld Hints aktualisieren
        txt_input.hint_text = lang.get("input_hint", "Enter text here...")
        txt_file.hint_text = lang.get("file_hint", "No file selected...")
        txt_pass.hint_text = lang.get("password", "Password")
        txt_pass2.hint_text = lang.get("confirm_password", "Confirm")
        
        # Keyfile Button Text aktualisieren
        if state["keyfile_path"]:
            btn_keyfile.content.value = lang["keyfile_active"]
        else:
            btn_keyfile.content.value = lang["keyfile_btn"]
        
        # Checkbox Labels aktualisieren
        chk_confirm.label = lang["confirm_check"]
        
        # Speichere aktuelle Eingabewerte
        state["input_value"] = txt_input.value or ""
        state["output_value"] = txt_output.value or ""
        state["pass_value"] = txt_pass.value or ""
        state["pass2_value"] = txt_pass2.value or ""
        state["iter_value"] = txt_iter.value or str(ITERATIONS_DEFAULT)
        state["file_value"] = txt_file.value or ""
        
        # UI neu aufbauen
        page.controls.clear()
        page.add(build_ui())
        
        # Eingabewerte wiederherstellen
        txt_input.value = state["input_value"]
        txt_output.value = state["output_value"]
        txt_pass.value = state["pass_value"]
        txt_pass2.value = state["pass2_value"]
        txt_iter.value = state["iter_value"]
        txt_file.value = state["file_value"]
        
        page.update()
    
    # Initial build
    rebuild_ui()

# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------
if __name__ == "__main__":
    ft.run(main)