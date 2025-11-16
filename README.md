# Arşiv Organizatörü - Akıllı Kategorizasyon

PDF dosyalarını organize etmek için geliştirilmiş modern bir Python masaüstü uygulaması.

## 🎯 Özellikler

### v2.0 Yeni Özellikler
- **🎨 Dark Mode Arayüz**: CustomTkinter ile geliştirilmiş estetik ve modern GUI
- **🧠 Akıllı Ağırlıklı Kategorizasyon**: Basit anahtar kelime araması yerine istatistiksel puanlama sistemi
  - Birincil kelimeler: +5 puan (ör: "digital twin", "genetic algorithm")
  - İkincil kelimeler: +1 puan (ör: "data", "optimization")
  - Minimum skor eşiği: 10 puan (kategorize edilmek için)
- **📊 Tüm Sayfa Analizi**: PDF'in sadece ilk sayfaları değil, TÜM sayfaları analiz edilir
- **📈 İşlem Takibi**: Belirsiz (indeterminate) progress bar ile görsel geri bildirim

### Genel Özellikler
- **Tekrar Tespit**: PDF dosyalarının içerik hash'ine göre aynı dosyaları tespit eder
- **Otomatik Yeniden Adlandırma**: PDF meta verilerinden başlık bilgisi alarak dosyaları yeniden adlandırır
- **Kategori Bazlı Organizasyon**: Ağırlıklı puanlama sistemi ile dosyaları ilgili klasörlere kategorize eder
- **Threading**: Uzun işlemler sırasında GUI donmasını önler

## Kurulum

1. Python 3.x'in yüklü olduğundan emin olun (3.8+ önerilir)
2. Gerekli kütüphaneleri yükleyin:

```bash
pip install -r requirements.txt
```

veya doğrudan:

```bash
pip install PyMuPDF customtkinter
```

## Kullanım

1. Uygulamayı çalıştırın:

```bash
python pdf_organizer.py
```

2. **Kaynak Klasör**: Organize edilecek PDF dosyalarının bulunduğu klasörü seçin
3. **Hedef Klasör**: Dosyaların kopyalanacağı hedef klasörü seçin
4. **Kategori Profilleri**: v2.0'da kategori profilleri kod içinde tanımlıdır (birincil/ikincil kelimeler ile). 
   Kategori profillerini değiştirmek için `pdf_organizer.py` dosyasındaki `KATEGORI_PROFILERI` sözlüğünü düzenleyin.
5. **Organizasyonu Başlat** butonuna tıklayın (Progress bar işlem sırasında animasyon gösterecektir)

## İşleyiş

1. Kaynak klasördeki tüm PDF dosyaları recursive olarak taranır
2. Her dosya için MD5 hash hesaplanır ve duplike kontrolü yapılır
3. PDF meta verilerinden başlık bilgisi çıkarılır ve dosya adı olarak kullanılır
4. **PDF'in TÜM sayfalarından metin çıkarılır** 
5. **Akıllı Ağırlıklı Kategorizasyon** yapılır:
   - Birincil kelimeler her bulunduğunda +5 puan
   - İkincil kelimeler her bulunduğunda +1 puan
   - En yüksek skoru alan kategori seçilir
   - Minimum 10 puan eşiği altındaki PDF'ler "Diger" kategorisine atanır
6. Dosyalar ilgili klasörlere kopyalanır (orijinal dosyalar korunur)
7. İşlem özeti (kategori dağılımı dahil) log penceresinde gösterilir

## Notlar

- Dosyalar **kopyalanır**, taşınmaz (güvenlik için)
- Hiçbir kategoriye uymayan (10 puan eşiğinin altında kalan) dosyalar `Diger` klasörüne kopyalanır
- Aynı isimde dosya varsa, otomatik olarak sayaç eklenir (örn: `dosya_1.pdf`)
- Kategori profilleri kod içinde tanımlıdır ve `KATEGORI_PROFILERI` sözlüğünden düzenlenebilir
- Puanlama ayarları (BIRINCIL_PUAN, IKINCIL_PUAN, MIN_SKOR_ESIGI) kod başında sabit olarak tanımlıdır

