@echo off
chcp 65001 > nul
title Akıllı Arşiv Organizatörü v2.0
echo ======================================================
echo    Akıllı Arşiv Organizatörü & PDF Düzenleyici v2.0
echo ======================================================
echo.
python pdf_organizer.py
if %errorlevel% neq 0 (
    echo.
    echo [HATA] Uygulama calisirken bir sorun olustu.
    pause
)
