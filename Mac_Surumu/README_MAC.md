# 🍏 MacBook (macOS) Kullanım Kılavuzu

Bu klasör, **Akıllı Arşiv Organizatörü v2.0** uygulamasının macOS (Apple Silicon M1/M2/M3/M4 ve Intel) cihazlarda doğrudan çalıştırılması için hazırlanmıştır.

---

## 🚀 Çift Tıklayarak Çalıştırma

Klasör içerisinde 2 adet başlatıcı seçeneği bulunmaktadır:

1. **Önerilen Yöntem:** `Baslat_Mac.command` dosyasına çift tıklayın.
2. **Alternatif Yöntem:** `Arsiv_Organizasyonu.app` uygulamasına çift tıklayın.

> **İlk Çalıştırmada Ne Olur?**  
> Başlatıcı sisteminizdeki Python 3'ü otomatik algılar, bağımsız bir sanal ortam (`venv`) oluşturur, gerekli kütüphaneleri (`PyMuPDF`, `customtkinter`) kurar ve uygulamayı açar. Sonraki çalıştırmalarda anında açılır.

---

## ⚠️ macOS İzinleri & Güvenlik Uyarıları

### 1. Dosya İzinleri (Gerekirse):
Eğer dosya izinleri nedeniyle çift tıklamada açılmazsa, Terminal'i açıp şu komutu vermeniz yeterlidir:
```bash
chmod +x Baslat_Mac.command
```

### 2. "Geliştirici Doğrulanamadı" Uyarısı (Gatekeeper):
İnternetten veya harici diskten aktarılan dosyalarda macOS güvenlik uyarısı verirse:
* Dosyaya **sağ tıklayın** (veya iki parmakla dokunun),
* **"Aç" (Open)** seçeneğine tıklayın,
* Gelen onay kutusunda tekrar **"Aç"** butonunu seçin.  
*(Bu işlem macOS tarafından yalnızca ilk seferde bir defaya mahsus sorulur).*

---

## 📦 Gereksinimler
* macOS 10.14 veya üzeri (macOS Monterey, Ventura, Sonoma, Sequoia test edilmiştir).
* Python 3.8+ (Eğer sisteminizde yoksa [python.org](https://www.python.org/downloads/) veya Homebrew ile yükleyebilirsiniz).
