#!/bin/bash
# ==============================================================================
# Akıllı Arşiv Organizatörü v2.0 - macOS Başlatıcı
# Finder üzerinden çift tıklayarak çalıştırma için optimize edilmiştir.
# ==============================================================================

# Betiğin bulunduğu dizine geç
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "======================================================"
echo "    Akıllı Arşiv Organizatörü v2.0 (macOS)"
echo "======================================================"
echo ""

# Python 3 tespit mekanizması
PYTHON_BIN=""
if command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif [ -f "/opt/homebrew/bin/python3" ]; then
    PYTHON_BIN="/opt/homebrew/bin/python3"
elif [ -f "/usr/local/bin/python3" ]; then
    PYTHON_BIN="/usr/local/bin/python3"
elif [ -f "/Library/Frameworks/Python.framework/Versions/Current/bin/python3" ]; then
    PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/Current/bin/python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "[HATA] Sisteminizde Python 3 bulunamadı!"
    echo "Lütfen https://www.python.org/downloads/ adresinden macOS için Python 3 yükleyin."
    osascript -e 'display alert "Python 3 Bulunamadı" message "Lütfen https://www.python.org adresinden Python 3 yükleyin."' 2>/dev/null
    echo ""
    read -p "Çıkmak için Enter tuşuna basın..."
    exit 1
fi

echo "Kullanılan Python: $($PYTHON_BIN --version) ($PYTHON_BIN)"

# Sanal ortam (venv) kontrolü ve otomatik ilk kurulum
if [ ! -d "venv" ]; then
    echo ""
    echo "[İLK KURULUM] Gerekli sanal ortam (venv) oluşturuluyor..."
    $PYTHON_BIN -m venv venv
    if [ $? -ne 0 ]; then
        echo "[UYARI] venv oluşturulamadı. Sistem Python ortamına kuruluyor..."
        VENV_PYTHON="$PYTHON_BIN"
        $PYTHON_BIN -m pip install -r requirements.txt
    else
        VENV_PYTHON="./venv/bin/python"
        ./venv/bin/pip install --upgrade pip
        ./venv/bin/pip install -r requirements.txt
    fi
else
    VENV_PYTHON="./venv/bin/python"
fi

echo ""
echo "Arşiv Organizatörü başlatılıyor..."
$VENV_PYTHON pdf_organizer.py

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "[HATA] Uygulama sonlandı (Çıkış Kodu: $EXIT_CODE)."
    read -p "Pencereyi kapatmak için Enter tuşuna basın..."
fi
