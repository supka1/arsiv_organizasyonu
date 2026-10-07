# Akıllı Arşiv Organizatörü & PDF Düzenleyici (v2.0 Modernize)

PDF belgelerini derinlemesine analiz eden, gerçek ana başlığı tespit ederek dosyaları yeniden adlandıran ve kelime sınırları ile hatasız konu sınıflandırması yapan modern Python masaüstü uygulaması.

---

## 🚀 Yapılan İyileştirmeler ve Eski Sistemin Düzeltilen Hataları

### 1. 🔍 Derin Görsel Başlık Algılama (Eski Sistemin Metadata Hatası Çözüldü)
* **Eski Sorun:** Sistem sadece PDF metadata'sına (`doc.metadata['title']`) ve sayfanın sadece en üst %35'ine bakıyordu. Sonuç olarak `"Microsoft Word - Belge1"`, `"Untitled"`, `"Ara Rapor"`, dergi üst bilgisi veya boş isimler dosya adı oluyordu.
* **Yeni Çözüm:** 
  - İlk 3 sayfa taranır; metin blokları, font boyutları ve font ağırlıkları analiz edilir.
  - Sayfadaki en büyük fonta sahip ana başlık tespit edilir.
  - Üst bilgi (header/dergi adı/ISSN) ve alt bilgi (sayfa numaraları) filtrelenir.
  - Çok satırlı başlıklar doğru X-Y koordinat hizalaması ve tireleme düzeltmesiyle birleştirilir.
  - Dosya adı oluşturulurken Türkçe karakterler (ç, ğ, ı, ö, ş, ü) korunur, Windows yasaklı karakterleri temizlenir.

### 2. 🎯 Kelime Sınırı (Word Boundary) ile Hatasız Konu Sınıflandırması
* **Eski Sorun:** `metin.count(kelime)` kullanıldığı için alt dize (substring) hataları oluyordu. Örneğin `"art"` kelimesi `"smart"` ve `"article"` içinde, `"ai"` kelimesi ise `"email"` ve `"main"` içinde binlerce sahte puan toplayıp belgeleri yanlış klasörlere atıyordu.
* **Yeni Çözüm:**
  - Regex kelime sınırları (`\b...\b`) ve Türkçe duyarlı normalizasyon kullanılır.
  - **Katmanlı Ağırlık:** Başlıkta geçen anahtar kelimelere **15 puan**, özet/giriş bölümlerine **4 puan**, gövde metnine **1 puan** verilir.
  - Uzun kitap ve tezlerin haksız puan toplamasını önleyen doygunluk sınırı uygulanır.

### 3. 🖥️ Önizleme & Simülasyon (Dry-Run Tablosu)
* **Eski Sorun:** Kullanıcı işlem başlamadan önce ne olacağını göremiyordu.
* **Yeni Çözüm:** `🔍 Önizle & Tara (Dry-Run)` butonu ile dosyalar kopyalanmadan önce taranır; orijinal ad, bulunan başlık, atanan kategori ve üretilecek yeni dosya adı tabloda listelenir.

### 4. 📁 Kategori Yöneticisi & Kalıcı JSON Yapısı
* **Eski Sorun:** Program her açıldığında kategori listesi bomboş geliyordu ya da kodun içine gömülüydü.
* **Yeni Çözüm:** 
  - Hazır 6 kapsamlı profil ile açılır (`Yapay Zeka & Veri`, `Yazılım & Bilişim`, `Akademik & Araştırma`, `İş & Finans`, `Hukuk & Mevzuat`, `Mühendislik & Teknoloji`).
  - Arayüzden kategori ekleme, silme ve düzenleme yapılabilir.
  - Kategoriler `categories.json` dosyasına otomatik kaydedilir.

### 5. ⚙️ Esnek Seçenekler & Kontroller
* **Kopyala veya Taşı:** İsteğe bağlı dosya kopyalama veya disk tasarrufu için taşıma modu.
* **İsimlendirme Şablonu:** `Sadece Başlık`, `Kategori + Başlık` veya `Orijinal Ad + Başlık`.
* **Gerçek İlerleme Çubuğu:** Yüzdelik ve sayısal ilerleme takibi (`24 / 100 - %24`).
* **İptal Desteği:** İşlemi dilediğiniz zaman durdurabilme (`⏹ İptal Et`).

---

## 🛠️ Kurulum ve Çalıştırma

### Gereksinimler
* Python 3.8 veya üzeri (Python 3.10 - 3.14 desteklenir)

```bash
pip install -r requirements.txt
```

### Başlatma
* **Masaüstünden Tek Tıkla:** `Baslat.bat` dosyasına çift tıklayabilirsiniz.
* **Terminalden:**
```bash
python pdf_organizer.py
```
