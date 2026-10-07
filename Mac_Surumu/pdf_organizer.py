import os
import re
import sys
import json
import shutil
import hashlib
import unicodedata
import threading
from pathlib import Path
from tkinter import filedialog, ttk
import tkinter as tk

import customtkinter as ctk
import fitz  # PyMuPDF

# ==============================================================================
# TEMA VE TEMEL AYARLAR
# ==============================================================================
ctk.set_appearance_mode("dark")
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = str(BASE_DIR / "categories.json")

DEFAULT_CATEGORIES = {
    "Yapay_Zeka_ve_Veri": {
        "birincil": [
            "yapay zeka", "artificial intelligence", "machine learning", "makine öğrenmesi",
            "deep learning", "derin öğrenme", "neural network", "sinir ağları",
            "veri bilimi", "data science", "nlp", "computer vision", "llm", "large language model"
        ],
        "ikincil": [
            "algoritma", "model", "veri seti", "dataset", "python", "pytorch",
            "tensorflow", "training", "inference", "tahmin", "classification"
        ]
    },
    "Yazilim_ve_Bilisim": {
        "birincil": [
            "yazılım", "software", "programlama", "programming", "web development",
            "veritabanı", "database", "backend", "frontend", "api", "siber güvenlik",
            "cybersecurity", "devops", "cloud computing", "bulut bilişim"
        ],
        "ikincil": [
            "kod", "code", "sunucu", "server", "linux", "git", "docker",
            "framework", "mimari", "architecture", "güvenlik", "ağ", "network"
        ]
    },
    "Akademik_ve_Arastirma": {
        "birincil": [
            "araştırma", "research", "metodoloji", "methodology", "literatür taraması",
            "literature review", "hipotez", "hypothesis", "kaynakça", "references",
            "doktora tezi", "yüksek lisans", "akademik makale", "bilimsel çalışma"
        ],
        "ikincil": [
            "abstract", "özet", "bulgular", "tartışma", "sonuçlar", "analiz",
            "citation", "deney", "örneklem", "anket", "istatistik"
        ]
    },
    "Is_ve_Finans": {
        "birincil": [
            "finans", "finance", "muhasebe", "accounting", "iş planı", "business plan",
            "pazarlama", "marketing", "ekonomi", "economy", "bütçe", "budget",
            "yatırım", "investment", "fatura", "invoice", "gelir tablosu"
        ],
        "ikincil": [
            "maliyet", "kâr", "zarar", "strateji", "yönetim", "management",
            "rapor", "analiz", "müşteri", "satış", "piyasa", "sektör"
        ]
    },
    "Hukuk_ve_Mevzuat": {
        "birincil": [
            "hukuk", "kanun", "yönetmelik", "mevzuat", "kararname", "mahkeme",
            "dava", "sözleşme", "vekaletname", "içtihat", "resmi gazete"
        ],
        "ikincil": [
            "madde", "hüküm", "taraf", "borçlar", "ceza", "hukuki",
            "tazminat", "yargı", "hakim", "avukat", "itiraz"
        ]
    },
    "Muhendislik_ve_Teknoloji": {
        "birincil": [
            "mühendislik", "engineering", "tasarım", "cad", "üretim", "manufacturing",
            "mekanik", "elektrik", "elektronik", "otomasyon", "robotik", "robotics",
            "dijital ikiz", "digital twin", "endüstri 4.0", "industry 4.0"
        ],
        "ikincil": [
            "sensör", "sensor", "iot", "donanım", "hardware", "ölçüm",
            "kalibrasyon", "sistem", "performans", "simülasyon", "test"
        ]
    }
}

JUNK_TITLES_PATTERN = re.compile(
    r'^(untitled|isimsiz|başlıksız|microsoft\s+word|powerpoint|presentation|slide\s*\d+|'
    r'document\d*|belge\d*|new\s+document|cover\s*page|kapak|sayfa\s*\d+|page\s*\d+|'
    r'table\s+of\s+contents|içindekiler|önsöz|preface|abstract|özet|introduction|giriş|'
    r'ieee\b|springer\b|elsevier\b|arxiv:\S+|doi:\S+|issn\s*\d+|isbn\s*\d+|'
    r't\.?c\.?\s+[a-zçğıöşü\s]+üniversitesi|journal\s+of\b|proceedings\s+of\b|'
    r'author\b|yazar\b|all\s+rights\s+reserved).*$',
    re.IGNORECASE
)


# ==============================================================================
# YARDIMCI VE NORMALİZASYON FONKSİYONLARI
# ==============================================================================
def turkce_kucult(metin: str) -> str:
    """Türkçe karakterleri (I/ı, İ/i) doğru şekilde küçük harfe çevirir."""
    if not metin:
        return ""
    metin = metin.replace("İ", "i").replace("I", "ı")
    return unicodedata.normalize("NFC", metin).lower()


def guvenli_dosya_adi_olustur(baslik_metni: str, max_uzunluk: int = 120) -> str:
    """
    Başlık metninden Windows ve Unix için güvenli, okunaklı, kelime kesilmeyen dosya adı üretir.
    Türkçe karakterleri korur, geçersiz karakterleri temizler.
    """
    if not baslik_metni:
        return ""

    # Unicode normalizasyonu (birleşik aksanları temizle)
    metin = unicodedata.normalize("NFC", baslik_metni.strip())

    # Windows yasaklı karakterleri temizle: < > : " / \ | ? *
    metin = re.sub(r'[<>:"/\\|?*]', ' ', metin)

    # Fazla noktalama ve boşlukları düzenle
    metin = re.sub(r'[\r\n\t]+', ' ', metin)
    metin = re.sub(r'[\s_]+', ' ', metin).strip()

    # Eğer çok uzunsa kelime sınırından kes
    if len(metin) > max_uzunluk:
        kesilmis = metin[:max_uzunluk]
        son_bosluk = kesilmis.rfind(' ')
        if son_bosluk > max_uzunluk // 2:
            metin = kesilmis[:son_bosluk]
        else:
            metin = kesilmis

    # Baş ve sondaki tire ve noktaları temizle
    metin = metin.strip(' .-_')
    return metin


# ==============================================================================
# GELİŞMİŞ BAŞLIK ÇIKARICI (PDF TITLE EXTRACTOR)
# ==============================================================================
class AdvancedPDFTitleExtractor:
    """
    PDF belgelerinden kapak ve ilk sayfaları derinlemesine analiz ederek
    en olası ana başlığı doğru şekilde tespit eder.
    """

    @classmethod
    def is_junk_title(cls, text: str) -> bool:
        if not text:
            return True
        t = text.strip()
        if len(t) < 4 or len(t) > 250:
            return True
        if JUNK_TITLES_PATTERN.match(t):
            return True
        # Yalnızca sayılar veya özel işaretlerden ibaretse
        if re.sub(r'[\d\W_]', '', t) == '':
            return True
        # Dosya yolu veya URL ise
        if t.startswith('http://') or t.startswith('https://') or ':\\' in t or t.endswith('.pdf'):
            return True
        return False

    @classmethod
    def extract_title_from_metadata(cls, doc) -> str:
        try:
            meta = doc.metadata or {}
            title = meta.get("title")
            if title:
                title = title.strip()
                if not cls.is_junk_title(title):
                    # Sayfa metninde de bu başlık veya kelimeleri geçiyor mu?
                    first_page_text = turkce_kucult(doc[0].get_text() if len(doc) > 0 else "")
                    title_words = [w for w in turkce_kucult(title).split() if len(w) > 3]
                    if title_words:
                        matches = sum(1 for w in title_words if w in first_page_text)
                        if matches >= max(1, len(title_words) // 2):
                            return title
        except Exception:
            pass
        return ""

    @classmethod
    def extract_title_from_visual_layout(cls, doc) -> str:
        """
        İlk 3 sayfadaki font büyüklükleri, pozisyonları ve metin bloklarını inceleyerek
        asıl ana başlığı çıkarır.
        """
        max_pages = min(3, len(doc))
        en_iyi_baslik = ""
        en_iyi_skor = 0

        for page_idx in range(max_pages):
            page = doc[page_idx]
            rect = page.rect
            page_h = rect.height
            page_w = rect.width

            # Üst bilgi (header: üst %7) ve alt bilgi (footer: alt %8) hariç tutulur
            min_y = page_h * 0.05
            max_y = page_h * 0.65

            text_page = page.get_text("dict", flags=fitz.TEXTFLAGS_BLOCKS)
            blocks = text_page.get("blocks", [])

            # Sayfadaki span'leri topla
            spans = []
            max_font = 0.0

            for b in blocks:
                if b.get("type") != 0:  # Sadece metin blokları
                    continue
                bbox = b.get("bbox", [0, 0, 0, 0])
                if bbox[1] < min_y or bbox[1] > max_y:
                    continue

                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        txt = span.get("text", "").strip()
                        size = round(span.get("size", 0.0), 1)
                        flags = span.get("flags", 0)  # Kalınlık/İtalik bilgisi
                        y_pos = round(span.get("bbox", [0, 0, 0, 0])[1], 1)
                        x_pos = round(span.get("bbox", [0, 0, 0, 0])[0], 1)

                        if len(txt) > 1 and not cls.is_junk_title(txt):
                            spans.append({
                                "text": txt,
                                "size": size,
                                "flags": flags,
                                "y": y_pos,
                                "x": x_pos
                            })
                            if size > max_font:
                                max_font = size

            if not spans or max_font < 9.0:
                continue

            # En büyük fontun %85'i ve üzerindeki span'leri başlık adayı olarak topla
            esik_font = max_font * 0.86
            baslik_parcalari = [s for s in spans if s["size"] >= esik_font]

            if not baslik_parcalari:
                continue

            # Y koordinatına göre (ardından X'e göre) sırala
            baslik_parcalari.sort(key=lambda s: (s["y"], s["x"]))

            # Satırları birleştir
            birlesik_satirlar = []
            simdiki_satir = []
            son_y = None

            for s in baslik_parcalari:
                if son_y is None or abs(s["y"] - son_y) <= 8.0:
                    simdiki_satir.append(s["text"])
                    son_y = s["y"]
                else:
                    birlesik_satirlar.append(" ".join(simdiki_satir))
                    simdiki_satir = [s["text"]]
                    son_y = s["y"]
            if simdiki_satir:
                birlesik_satirlar.append(" ".join(simdiki_satir))

            tam_aday = " ".join(birlesik_satirlar)
            tam_aday = re.sub(r'\s+', ' ', tam_aday).strip()

            # Tireleme düzeltmesi: "araş- tırma" -> "araştırma"
            tam_aday = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', tam_aday)

            if len(tam_aday) >= 6 and not cls.is_junk_title(tam_aday):
                # Puanlama: Font büyüklüğü ve sayfa önceliği
                sayfa_katsayisi = 1.0 / (page_idx + 1)
                skor = (max_font * 2) + len(tam_aday.split()) * sayfa_katsayisi
                if skor > en_iyi_skor:
                    en_iyi_skor = skor
                    en_iyi_baslik = tam_aday

        return en_iyi_baslik

    @classmethod
    def get_clean_title(cls, doc, fallback_name: str) -> str:
        """
        Önce görsel analiz, ardından meta veri, en son dosya adı fallback'i kullanır.
        """
        # 1. Görsel font analizi (en güvenilir gerçek başlık)
        gorsel_baslik = cls.extract_title_from_visual_layout(doc)
        if gorsel_baslik and len(gorsel_baslik) >= 6:
            return gorsel_baslik

        # 2. Meta veri başlığı
        meta_baslik = cls.extract_title_from_metadata(doc)
        if meta_baslik and len(meta_baslik) >= 6:
            return meta_baslik

        # 3. Fallback dosya adı
        orijinal_ad = Path(fallback_name).stem
        orijinal_ad = re.sub(r'^[_\-\d\s]+', '', orijinal_ad)  # Başındaki saçma numaraları temizle
        return orijinal_ad or "Isimsiz_Belge"


# ==============================================================================
# AKILLI KONU KATEGORİZASYON MOTORU (SMART TOPIC CLASSIFIER)
# ==============================================================================
class SmartPDFClassifier:
    """
    Belgelerin ilk sayfalarına ve başlıklarına yüksek ağırlık vererek,
    kelime sınırları (word boundaries) ile hatasız ve dengeli sınıflandırma yapar.
    """

    def __init__(self, categories_dict: dict):
        self.categories = categories_dict
        self._compiled_regexes = {}
        self._compile_keywords()

    def update_categories(self, new_categories: dict):
        self.categories = new_categories
        self._compile_keywords()

    def _compile_keywords(self):
        """Performans için anahtar kelimeleri regex olarak önceden derler."""
        self._compiled_regexes = {}
        for cat_name, profile in self.categories.items():
            self._compiled_regexes[cat_name] = {
                "birincil": [],
                "ikincil": []
            }
            for kw in profile.get("birincil", []):
                kw_clean = turkce_kucult(kw.strip())
                if kw_clean:
                    pattern = re.compile(r'(?:\b|_)' + re.escape(kw_clean) + r'(?:\b|_)', re.IGNORECASE)
                    self._compiled_regexes[cat_name]["birincil"].append((kw_clean, pattern))

            for kw in profile.get("ikincil", []):
                kw_clean = turkce_kucult(kw.strip())
                if kw_clean:
                    pattern = re.compile(r'(?:\b|_)' + re.escape(kw_clean) + r'(?:\b|_)', re.IGNORECASE)
                    self._compiled_regexes[cat_name]["ikincil"].append((kw_clean, pattern))

    def classify_document(self, doc, detected_title: str) -> tuple[str, float, dict]:
        """
        Belgeyi analiz eder; (en_uygun_kategori, skor, detaylar) döndürür.
        """
        if not self.categories:
            return "Diger", 0.0, {}

        # 1. Başlık metni
        title_lower = turkce_kucult(detected_title)

        # 2. Giriş metni (İlk 2 sayfa - özet ve giriş bölümleri)
        intro_text = ""
        for i in range(min(2, len(doc))):
            intro_text += " " + doc[i].get_text()
        intro_lower = turkce_kucult(intro_text)

        # 3. Gövde metni (İlk 15 sayfa yeterlidir; 500 sayfa taranıp CPU harcanmaz)
        body_text = ""
        for i in range(2, min(15, len(doc))):
            body_text += " " + doc[i].get_text()
        body_lower = turkce_kucult(body_text)

        scores = {}

        for cat_name, patterns in self._compiled_regexes.items():
            cat_score = 0.0

            # Birincil kelimeler
            for _, pat in patterns["birincil"]:
                # Başlıkta geçerse: +15 puan
                if pat.search(title_lower):
                    cat_score += 15.0

                # İlk sayfalarda geçerse: +4 puan (her tekrar +1, max 8)
                intro_matches = len(pat.findall(intro_lower))
                if intro_matches > 0:
                    cat_score += 4.0 + min(intro_matches - 1, 4)

                # Gövdede geçerse: +1 puan (doygunluk: max 5)
                body_matches = len(pat.findall(body_lower))
                if body_matches > 0:
                    cat_score += min(body_matches * 0.8, 5.0)

            # İkincil kelimeler
            for _, pat in patterns["ikincil"]:
                if pat.search(title_lower):
                    cat_score += 5.0

                intro_matches = len(pat.findall(intro_lower))
                if intro_matches > 0:
                    cat_score += 2.0 + min(intro_matches - 1, 2)

                body_matches = len(pat.findall(body_lower))
                if body_matches > 0:
                    cat_score += min(body_matches * 0.4, 3.0)

            if cat_score > 0:
                scores[cat_name] = round(cat_score, 1)

        if not scores:
            return "Diger", 0.0, {}

        en_iyi_kategori = max(scores, key=scores.get)
        en_yuksek_skor = scores[en_iyi_kategori]

        # Minimum güvenilirlik eşiği (3.0 puan: en az 1 anlamlı kelime)
        if en_yuksek_skor < 3.0:
            return "Diger", en_yuksek_skor, scores

        return en_iyi_kategori, en_yuksek_skor, scores


# ==============================================================================
# ANA GRAFİKSEL ARAYÜZ (GUI) UYGULAMASI
# ==============================================================================
class ModernPDFOrganizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Akıllı Arşiv Organizasyonu & PDF Düzenleyici v2.0")
        self.root.geometry("1340x880")
        self.root.minsize(1050, 700)

        self.source_folder = ctk.StringVar()
        self.target_folder = ctk.StringVar()
        self.operation_mode = ctk.StringVar(value="copy")  # 'copy' veya 'move'
        self.naming_format = ctk.StringVar(value="title_only")  # 'title_only', 'cat_title', 'orig_title'

        self.is_processing = False
        self.cancel_requested = False

        self.categories = self.load_categories()
        self.classifier = SmartPDFClassifier(self.categories)

        self.preview_data = []

        self.setup_ui()

    def load_categories(self) -> dict:
        """Kategorileri categories.json dosyasından okur, yoksa varsayılanları kaydeder."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and len(data) > 0:
                        return data
            except Exception as e:
                print(f"Kategori dosyası okunamadı: {e}")

        # Varsayılanları kaydet
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CATEGORIES, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return DEFAULT_CATEGORIES.copy()

    def save_categories(self):
        """Kategorileri dosyaya yazar."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.categories, f, ensure_ascii=False, indent=2)
            self.classifier.update_categories(self.categories)
            self.log("[BİLGİ] Kategoriler başarıyla kaydedildi.")
        except Exception as e:
            self.log(f"[HATA] Kategoriler kaydedilemedi: {e}")

    def setup_ui(self):
        # Üst Başlık Çubuğu
        header_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 8))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="📁 Akıllı Arşiv & PDF Organizatörü",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_lbl.pack(side="left")

        ver_lbl = ctk.CTkLabel(
            header_frame,
            text="v2.0 • Derin Başlık Algılama & Konu Dağıtımı",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="gray"
        )
        ver_lbl.pack(side="left", padx=12, pady=(4, 0))

        # Ana Sekmeler
        self.tabview = ctk.CTkTabview(self.root, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        tab_main = self.tabview.add("Organize Et & Önizleme")
        tab_categories = self.tabview.add("Kategori Yöneticisi")
        tab_log = self.tabview.add("İşlem Günlüğü")
        tab_help = self.tabview.add("Nasıl Çalışır?")

        self.setup_main_tab(tab_main)
        self.setup_categories_tab(tab_categories)
        self.setup_log_tab(tab_log)
        self.setup_help_tab(tab_help)

        # Alt Bilgi
        footer_frame = ctk.CTkFrame(self.root, height=25, fg_color="transparent")
        footer_frame.pack(fill="x", padx=20, pady=(0, 6))
        self.status_bar_lbl = ctk.CTkLabel(
            footer_frame,
            text="Hazır. Kaynak ve hedef klasörleri seçtikten sonra 'Önizle' veya 'Başlat' butonuna tıklayın.",
            font=ctk.CTkFont(size=11),
            anchor="w"
        )
        self.status_bar_lbl.pack(side="left", fill="x", expand=True)

    # --------------------------------------------------------------------------
    # 1. SEKME: ORGANİZE ET & ÖNİZLEME
    # --------------------------------------------------------------------------
    def setup_main_tab(self, tab):
        # Üst Panel: Klasörler ve Ayarlar
        top_panel = ctk.CTkFrame(tab, corner_radius=8)
        top_panel.pack(fill="x", padx=10, pady=10)

        # Klasör Seçimi (Grid)
        top_panel.columnconfigure(1, weight=1)

        # Kaynak
        ctk.CTkLabel(top_panel, text="Kaynak Klasör:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, padx=12, pady=6, sticky="w")
        ctk.CTkEntry(top_panel, textvariable=self.source_folder, placeholder_text="PDF'lerin bulunduğu kaynak klasörü seçin...", height=32).grid(row=0, column=1, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(top_panel, text="Klasör Seç", command=self.browse_source, width=100, height=32).grid(row=0, column=2, padx=12, pady=6)

        # Hedef
        ctk.CTkLabel(top_panel, text="Hedef Klasör:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=1, column=0, padx=12, pady=6, sticky="w")
        ctk.CTkEntry(top_panel, textvariable=self.target_folder, placeholder_text="Düzenlenmiş PDF'lerin kaydedileceği hedef klasörü seçin...", height=32).grid(row=1, column=1, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(top_panel, text="Klasör Seç", command=self.browse_target, width=100, height=32).grid(row=1, column=2, padx=12, pady=6)

        # Seçenekler Çubuğu
        opts_frame = ctk.CTkFrame(top_panel, fg_color="transparent")
        opts_frame.grid(row=2, column=0, columnspan=3, padx=12, pady=(6, 10), sticky="ew")

        # İşlem Modu: Kopyala / Taşı
        ctk.CTkLabel(opts_frame, text="İşlem:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 6))
        ctk.CTkRadioButton(opts_frame, text="Kopyala (Güvenli)", variable=self.operation_mode, value="copy").pack(side="left", padx=6)
        ctk.CTkRadioButton(opts_frame, text="Taşı (Yer Tasarrufu)", variable=self.operation_mode, value="move").pack(side="left", padx=6)

        # İsimlendirme Formatı
        ctk.CTkLabel(opts_frame, text="| İsim Formatı:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(14, 6))
        naming_menu = ctk.CTkOptionMenu(
            opts_frame,
            variable=self.naming_format,
            values=["Sadece Başlık", "Kategori + Başlık", "Orijinal Ad + Başlık"],
            width=160,
            height=28
        )
        naming_menu.pack(side="left", padx=4)
        naming_menu.set("Sadece Başlık")

        # Kontrol Butonları & Progress
        control_frame = ctk.CTkFrame(tab, corner_radius=8)
        control_frame.pack(fill="x", padx=10, pady=(0, 10))

        btn_box = ctk.CTkFrame(control_frame, fg_color="transparent")
        btn_box.pack(fill="x", padx=12, pady=8)

        self.btn_preview = ctk.CTkButton(
            btn_box,
            text="🔍 Önizle & Tara (Dry-Run)",
            command=self.start_preview,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#3B82F6",
            hover_color="#2563EB",
            height=36,
            width=200
        )
        self.btn_preview.pack(side="left", padx=(0, 10))

        self.btn_start = ctk.CTkButton(
            btn_box,
            text="▶ Organizasyonu Başlat",
            command=self.start_organization,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            height=36,
            width=210
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        self.btn_stop = ctk.CTkButton(
            btn_box,
            text="⏹ İptal Et",
            command=self.request_cancel,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#EF4444",
            hover_color="#DC2626",
            state="disabled",
            height=36,
            width=110
        )
        self.btn_stop.pack(side="left")

        # İlerleme Çubuğu ve Sayaç
        prog_box = ctk.CTkFrame(control_frame, fg_color="transparent")
        prog_box.pack(fill="x", padx=12, pady=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(prog_box, height=14, corner_radius=4)
        self.progress_bar.pack(fill="x", side="left", expand=True, padx=(0, 12))
        self.progress_bar.set(0)

        self.lbl_progress_count = ctk.CTkLabel(prog_box, text="0 / 0 (%0)", font=ctk.CTkFont(size=11), width=90)
        self.lbl_progress_count.pack(side="right")

        # Önizleme ve Sonuç Tablosu
        table_frame = ctk.CTkFrame(tab, corner_radius=8)
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        table_header = ctk.CTkFrame(table_frame, fg_color="transparent")
        table_header.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(table_header, text="Analiz ve Önizleme Tablosu", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        self.lbl_table_summary = ctk.CTkLabel(table_header, text="", font=ctk.CTkFont(size=11), text_color="gray")
        self.lbl_table_summary.pack(side="right")

        # Modern Treeview
        tree_container = tk.Frame(table_frame, bg="#1E1E1E")
        tree_container.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        tree_font = ("Helvetica", 10) if sys.platform == "darwin" else ("Segoe UI", 9)
        style.configure(
            "Treeview",
            background="#242424",
            foreground="#E0E0E0",
            fieldbackground="#242424",
            rowheight=26,
            font=tree_font
        )
        style.configure("Treeview.Heading", background="#333333", foreground="#FFFFFF", font=(tree_font[0], tree_font[1], "bold"))
        style.map("Treeview", background=[("selected", "#1D4ED8")])

        columns = ("durum", "orijinal_ad", "bulunan_baslik", "kategori", "skor", "yeni_ad")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("durum", text="Durum")
        self.tree.heading("orijinal_ad", text="Orijinal Dosya Adı")
        self.tree.heading("bulunan_baslik", text="PDF İçinden Bulunan Ana Başlık")
        self.tree.heading("kategori", text="Atanan Kategori")
        self.tree.heading("skor", text="Skor")
        self.tree.heading("yeni_ad", text="Oluşturulacak Yeni Dosya Adı")

        self.tree.column("durum", width=80, anchor="center")
        self.tree.column("orijinal_ad", width=220)
        self.tree.column("bulunan_baslik", width=380)
        self.tree.column("kategori", width=140, anchor="center")
        self.tree.column("skor", width=60, anchor="center")
        self.tree.column("yeni_ad", width=320)

        scrollbar_y = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        tree_container.rowconfigure(0, weight=1)
        tree_container.columnconfigure(0, weight=1)

    # --------------------------------------------------------------------------
    # 2. SEKME: KATEGORİ YÖNETİCİSİ
    # --------------------------------------------------------------------------
    def setup_categories_tab(self, tab):
        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=12, pady=12)

        # Sol Sütun: Yeni Kategori Ekleme Formu
        left_col = ctk.CTkFrame(container, width=420, corner_radius=8)
        left_col.pack(side="left", fill="y", padx=(0, 10), pady=0)
        left_col.pack_propagate(False)

        ctk.CTkLabel(left_col, text="Yeni Kategori Ekle / Düzenle", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=14, pady=(12, 10))

        ctk.CTkLabel(left_col, text="Kategori Adı:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=14, pady=(4, 2))
        self.entry_cat_name = ctk.CTkEntry(left_col, placeholder_text="Örn: Hukuk_ve_Mevzuat")
        self.entry_cat_name.pack(fill="x", padx=14, pady=(0, 8))

        ctk.CTkLabel(left_col, text="Birincil Kelimeler (+15 Başlık, +4 Özet):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=14, pady=(4, 2))
        self.txt_primary = ctk.CTkTextbox(left_col, height=90, font=ctk.CTkFont(size=10))
        self.txt_primary.pack(fill="x", padx=14, pady=(0, 8))
        self.txt_primary.insert("1.0", "virgülle ayırarak girin:\nörnek: yapay zeka, deep learning, sinir ağları")

        ctk.CTkLabel(left_col, text="İkincil Kelimeler (+5 Başlık, +2 Özet):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=14, pady=(4, 2))
        self.txt_secondary = ctk.CTkTextbox(left_col, height=90, font=ctk.CTkFont(size=10))
        self.txt_secondary.pack(fill="x", padx=14, pady=(0, 10))
        self.txt_secondary.insert("1.0", "virgülle ayırarak girin:\nörnek: python, model, veri, algoritma")

        btn_row = ctk.CTkFrame(left_col, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=8)

        ctk.CTkButton(
            btn_row,
            text="Kategoriyi Kaydet / Ekle",
            command=self.ui_add_or_update_category,
            fg_color="#10B981",
            hover_color="#059669",
            height=32
        ).pack(fill="x", pady=3)

        ctk.CTkButton(
            btn_row,
            text="Varsayılanları Geri Yükle",
            command=self.ui_restore_default_categories,
            fg_color="#6B7280",
            hover_color="#4B5563",
            height=28
        ).pack(fill="x", pady=6)

        # Sağ Sütun: Mevcut Kategoriler Listesi
        right_col = ctk.CTkFrame(container, corner_radius=8)
        right_col.pack(side="right", fill="both", expand=True)

        ctk.CTkLabel(right_col, text="Kayıtlı Kategori Profilleri", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=14, pady=(12, 6))

        self.scroll_cat_list = ctk.CTkScrollableFrame(right_col)
        self.scroll_cat_list.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        self.refresh_categories_ui_list()

    def refresh_categories_ui_list(self):
        """Kayıtlı kategorileri ekranda listeler."""
        for widget in self.scroll_cat_list.winfo_children():
            widget.destroy()

        for cat_name, profile in sorted(self.categories.items()):
            card = ctk.CTkFrame(self.scroll_cat_list, corner_radius=6)
            card.pack(fill="x", pady=4, padx=2)

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=8, pady=(6, 2))

            ctk.CTkLabel(top, text=f"📁 {cat_name}", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")

            del_btn = ctk.CTkButton(
                top,
                text="Sil",
                width=50,
                height=22,
                fg_color="#EF4444",
                hover_color="#DC2626",
                command=lambda cn=cat_name: self.ui_delete_category(cn)
            )
            del_btn.pack(side="right")

            prim_str = ", ".join(profile.get("birincil", []))
            sec_str = ", ".join(profile.get("ikincil", []))

            ctk.CTkLabel(
                card,
                text=f"Birincil ({len(profile.get('birincil', []))}): {prim_str[:120]}...",
                font=ctk.CTkFont(size=10),
                anchor="w",
                text_color="#93C5FD"
            ).pack(fill="x", padx=8, pady=1)

            ctk.CTkLabel(
                card,
                text=f"İkincil ({len(profile.get('ikincil', []))}): {sec_str[:120]}...",
                font=ctk.CTkFont(size=10),
                anchor="w",
                text_color="#D1D5DB"
            ).pack(fill="x", padx=8, pady=(0, 6))

    def ui_add_or_update_category(self):
        name = self.entry_cat_name.get().strip()
        prim = self.txt_primary.get("1.0", "end").strip()
        sec = self.txt_secondary.get("1.0", "end").strip()

        if not name:
            self.log("[HATA] Kategori adı boş bırakılamaz.")
            return

        clean_name = guvenli_dosya_adi_olustur(name, max_uzunluk=40)
        clean_name = clean_name.replace(" ", "_")

        prim_list = [k.strip() for k in prim.replace("\n", ",").split(",") if k.strip() and not k.startswith("örnek")]
        sec_list = [k.strip() for k in sec.replace("\n", ",").split(",") if k.strip() and not k.startswith("örnek")]

        if not prim_list:
            self.log("[HATA] En az bir birincil anahtar kelime girmelisiniz.")
            return

        self.categories[clean_name] = {
            "birincil": prim_list,
            "ikincil": sec_list
        }

        self.save_categories()
        self.refresh_categories_ui_list()
        self.entry_cat_name.delete(0, "end")
        self.log(f"[KATEGORİ EKLENDİ] {clean_name}")

    def ui_delete_category(self, cat_name):
        if cat_name in self.categories:
            del self.categories[cat_name]
            self.save_categories()
            self.refresh_categories_ui_list()
            self.log(f"[KATEGORİ SİLİNDİ] {cat_name}")

    def ui_restore_default_categories(self):
        self.categories = DEFAULT_CATEGORIES.copy()
        self.save_categories()
        self.refresh_categories_ui_list()
        self.log("[BİLGİ] Varsayılan kategoriler geri yüklendi.")

    # --------------------------------------------------------------------------
    # 3. SEKME: İŞLEM GÜNLÜĞÜ
    # --------------------------------------------------------------------------
    def setup_log_tab(self, tab):
        container = ctk.CTkFrame(tab, corner_radius=8)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(header, text="Detaylı İşlem ve Hata Günlüğü", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        ctk.CTkButton(header, text="Günlüğü Temizle", command=self.clear_log, width=120, height=26).pack(side="right")

        self.log_textbox = ctk.CTkTextbox(container, wrap="word", font=ctk.CTkFont(family="Consolas", size=10))
        self.log_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 10))

    def log(self, message: str):
        self.root.after(0, self._append_log, message)

    def _append_log(self, message: str):
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")

    def clear_log(self):
        self.log_textbox.delete("1.0", "end")

    # --------------------------------------------------------------------------
    # 4. SEKME: YARDIM VE REHBER
    # --------------------------------------------------------------------------
    def setup_help_tab(self, tab):
        scroll_frame = ctk.CTkScrollableFrame(tab)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=15)

        title = ctk.CTkLabel(scroll_frame, text="Sistem Nasıl Çalışır? & Yeni Özellikler", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(anchor="w", pady=(0, 15))

        rehber_maddeleri = [
            ("1. Derin Görsel Başlık Algılama (Font Hiyerarşisi)",
             "• Eski sistemin aksine sadece üst %35 değil, ilk 3 sayfa taranır.\n"
             "• Sayfadaki en büyük font boyutuna sahip metin blokları tespit edilir.\n"
             "• Üst bilgi (header/dergi adı/ISSN) ve alt bilgi (sayfa no) otomatik elenir.\n"
             "• Çok satırlı başlıklar doğru X-Y koordinat hizalamasıyla düzgünce birleştirilir."),

            ("2. Kelime Sınırı (Word Boundary) ile Hatasız Puanlama",
             "• Eski sistemde 'art' kelimesi 'smart' ve 'article' içinde, 'ai' ise 'main' ve 'email' içinde hatalı puan üretiyordu.\n"
             "• Yeni sistemde regex kelime sınırları (\\b) kullanılarak yalnızca bağımsız kelimeler puanlanır.\n"
             "• Başlıkta geçen kelimeler 15x, özet/giriş bölümündekiler 4x ağırlıkla hesaplanır.\n"
             "• Uzun belgelerin haksız puan toplamasını önleyen doygunluk normalizasyonu uygulanır."),

            ("3. Önizleme & Simülasyon (Dry-Run)",
             "• Dosyalara dokunmadan önce 'Önizle & Tara' butonuna tıklayarak hangi dosyanın hangi başlıkla hangi klasöre gideceğini tabloda görebilirsiniz."),

            ("4. Kopyalama veya Taşıma Seçeneği",
             "• Arşivinizi korumak için 'Kopyala' veya disk alanından tasarruf etmek için 'Taşı' modunu seçebilirsiniz."),

            ("5. İptal ve Durdurma Güvencesi",
             "• İşlem sırasında istediğiniz an 'İptal Et' butonuna basarak süreci güvenle durdurabilirsiniz.")
        ]

        for baslik, icerik in rehber_maddeleri:
            card = ctk.CTkFrame(scroll_frame, corner_radius=8)
            card.pack(fill="x", pady=6, padx=4)
            ctk.CTkLabel(card, text=baslik, font=ctk.CTkFont(size=13, weight="bold"), text_color="#60A5FA").pack(anchor="w", padx=12, pady=(8, 4))
            ctk.CTkLabel(card, text=icerik, font=ctk.CTkFont(size=11), justify="left", anchor="w").pack(anchor="w", padx=12, pady=(0, 8))

    # --------------------------------------------------------------------------
    # DOSYA VE KLASÖR İŞLEMLERİ
    # --------------------------------------------------------------------------
    def browse_source(self):
        path = filedialog.askdirectory(title="Kaynak Klasörü Seçin")
        if path:
            self.source_folder.set(path)

    def browse_target(self):
        path = filedialog.askdirectory(title="Hedef Klasörü Seçin")
        if path:
            self.target_folder.set(path)

    def format_new_filename(self, clean_title: str, category: str, orig_name: str) -> str:
        if not clean_title:
            clean_title = guvenli_dosya_adi_olustur(Path(orig_name).stem) or "Belge"
        fmt = self.naming_format.get()
        if fmt == "Kategori + Başlık":
            return f"[{category}] - {clean_title}.pdf"
        elif fmt == "Orijinal Ad + Başlık":
            stem = Path(orig_name).stem
            return f"{stem} - {clean_title}.pdf"
        else:  # Sadece Başlık
            return f"{clean_title}.pdf"

    def scan_pdf_files(self, source_dir: str) -> list[str]:
        pdf_list = []
        for root_path, _, files in os.walk(source_dir):
            for f in files:
                if f.lower().endswith(".pdf"):
                    pdf_list.append(os.path.join(root_path, f))
        return pdf_list

    # --------------------------------------------------------------------------
    # ÖNİZLEME (DRY-RUN) İŞLEMİ
    # --------------------------------------------------------------------------
    def start_preview(self):
        if self.is_processing:
            return

        source = self.source_folder.get().strip()
        if not source or not os.path.isdir(source):
            self.log("[HATA] Lütfen geçerli bir kaynak klasör seçin!")
            return

        self.set_ui_processing_state(True)
        threading.Thread(target=self._run_preview, daemon=True).start()

    def _run_preview(self):
        self.cancel_requested = False
        source = self.source_folder.get().strip()
        self.log("\n🔍 Önizleme ve Analiz Başlatıldı...")

        pdf_files = self.scan_pdf_files(source)
        total = len(pdf_files)
        self.log(f"Toplam {total} adet PDF bulundu. Analiz ediliyor...")

        # Tabloyu temizle
        self.root.after(0, self._clear_tree)

        seen_hashes = set()
        tekrar_sayisi = 0
        basarili_sayisi = 0

        for idx, pdf_path in enumerate(pdf_files, 1):
            if self.cancel_requested:
                self.log("[BİLGİ] Önizleme kullanıcı tarafından durduruldu.")
                break

            orig_name = os.path.basename(pdf_path)
            file_hash = self.calculate_hash(pdf_path)

            if file_hash and file_hash in seen_hashes:
                tekrar_sayisi += 1
                row = ("Kopya (Atlanacak)", orig_name, "-", "-", "0", "-")
                self.root.after(0, self._add_tree_row, row)
                continue

            if file_hash:
                seen_hashes.add(file_hash)

            try:
                doc = fitz.open(pdf_path)
                bulunan_baslik = AdvancedPDFTitleExtractor.get_clean_title(doc, orig_name)
                guvenli_baslik = guvenli_dosya_adi_olustur(bulunan_baslik)

                kategori, skor, _ = self.classifier.classify_document(doc, bulunan_baslik)
                doc.close()

                yeni_dosya_adi = self.format_new_filename(guvenli_baslik, kategori, orig_name)
                durum = "Hazır"
                basarili_sayisi += 1

                row = (durum, orig_name, bulunan_baslik, kategori, str(skor), yeni_dosya_adi)
                self.root.after(0, self._add_tree_row, row)

            except Exception as e:
                row = ("Hata", orig_name, f"Okunamadı: {e}", "Hata", "0", "-")
                self.root.after(0, self._add_tree_row, row)

            # İlerleme güncelle
            pct = idx / total
            self.root.after(0, self._update_progress_ui, idx, total, pct)

        self.log(f"🔍 Önizleme tamamlandı: {basarili_sayisi} benzersiz dosya analiz edildi, {tekrar_sayisi} kopya tespit edildi.")
        self.root.after(0, lambda: self.lbl_table_summary.configure(
            text=f"Önizleme: {basarili_sayisi} hazır, {tekrar_sayisi} kopya atlanacak (Toplam {total})"
        ))
        self.set_ui_processing_state(False)

    # --------------------------------------------------------------------------
    # GERÇEK ORGANİZASYON İŞLEMİ
    # --------------------------------------------------------------------------
    def start_organization(self):
        if self.is_processing:
            return

        source = self.source_folder.get().strip()
        target = self.target_folder.get().strip()

        if not source or not os.path.isdir(source):
            self.log("[HATA] Lütfen geçerli bir kaynak klasör seçin!")
            return

        if not target or not os.path.isdir(target):
            self.log("[HATA] Lütfen geçerli bir hedef klasör seçin!")
            return

        if os.path.abspath(source) == os.path.abspath(target):
            self.log("[HATA] Kaynak ve hedef klasör aynı olamaz!")
            return

        self.set_ui_processing_state(True)
        threading.Thread(target=self._run_organization, daemon=True).start()

    def _run_organization(self):
        self.cancel_requested = False
        source = self.source_folder.get().strip()
        target = self.target_folder.get().strip()
        mode = self.operation_mode.get()  # 'copy' or 'move'

        self.log("\n" + "=" * 60)
        self.log(f"🚀 ORGANİZASYON BAŞLATILDI ({'Taşıma' if mode == 'move' else 'Kopyalama'} Modu)")
        self.log(f"Kaynak: {source}")
        self.log(f"Hedef:  {target}")
        self.log("=" * 60)

        pdf_files = self.scan_pdf_files(source)
        total = len(pdf_files)
        self.log(f"Toplam {total} PDF dosyası işleniyor...\n")

        self.root.after(0, self._clear_tree)

        seen_hashes = set()
        tekrar_sayisi = 0
        basarili_sayisi = 0
        hata_sayisi = 0
        kategori_sayaclari = {}

        for idx, pdf_path in enumerate(pdf_files, 1):
            if self.cancel_requested:
                self.log("\n[UYARI] İşlem kullanıcı tarafından durduruldu!")
                break

            orig_name = os.path.basename(pdf_path)
            file_hash = self.calculate_hash(pdf_path)

            if file_hash and file_hash in seen_hashes:
                tekrar_sayisi += 1
                self.log(f"[KOPYA ATLANDI] ({idx}/{total}): {orig_name}")
                row = ("Atlandı (Kopya)", orig_name, "-", "-", "0", "-")
                self.root.after(0, self._add_tree_row, row)
                continue

            if file_hash:
                seen_hashes.add(file_hash)

            try:
                doc = fitz.open(pdf_path)
                bulunan_baslik = AdvancedPDFTitleExtractor.get_clean_title(doc, orig_name)
                guvenli_baslik = guvenli_dosya_adi_olustur(bulunan_baslik)

                kategori, skor, _ = self.classifier.classify_document(doc, bulunan_baslik)
                doc.close()

                # Hedef klasörü oluştur
                hedef_kategori_klasoru = os.path.join(target, kategori)
                os.makedirs(hedef_kategori_klasoru, exist_ok=True)

                # Yeni dosya adı ve çakışma kontrolü
                yeni_dosya_adi_tabani = self.format_new_filename(guvenli_baslik, kategori, orig_name)
                dosya_stem = Path(yeni_dosya_adi_tabani).stem
                son_dosya_adi = f"{dosya_stem}.pdf"
                hedef_tam_yol = os.path.join(hedef_kategori_klasoru, son_dosya_adi)

                sayac = 1
                while os.path.exists(hedef_tam_yol):
                    son_dosya_adi = f"{dosya_stem}_{sayac}.pdf"
                    hedef_tam_yol = os.path.join(hedef_kategori_klasoru, son_dosya_adi)
                    sayac += 1

                # Kopyala veya Taşı
                if mode == "move":
                    shutil.move(pdf_path, hedef_tam_yol)
                    islem_adi = "Taşındı"
                else:
                    shutil.copy2(pdf_path, hedef_tam_yol)
                    islem_adi = "Kopyalandı"

                basarili_sayisi += 1
                kategori_sayaclari[kategori] = kategori_sayaclari.get(kategori, 0) + 1

                self.log(f"[{islem_adi.upper()}] ({idx}/{total}) {orig_name} -> {kategori}/{son_dosya_adi} (Skor: {skor})")
                row = (islem_adi, orig_name, bulunan_baslik, kategori, str(skor), son_dosya_adi)
                self.root.after(0, self._add_tree_row, row)

            except Exception as e:
                hata_sayisi += 1
                self.log(f"[HATA] ({idx}/{total}) {orig_name}: {e}")
                row = ("Hata", orig_name, f"{e}", "Hata", "0", "-")
                self.root.after(0, self._add_tree_row, row)

            pct = idx / total
            self.root.after(0, self._update_progress_ui, idx, total, pct)

        # Özet Rapor
        self.log("\n" + "=" * 60)
        self.log("🏁 İŞLEM TAMAMLANDI")
        self.log(f"Toplam Başarılı: {basarili_sayisi}")
        self.log(f"Atlanan Kopya:   {tekrar_sayisi}")
        self.log(f"Hata Sayısı:     {hata_sayisi}")
        self.log("\n📊 Kategori Dağılımı:")
        for cat, cnt in sorted(kategori_sayaclari.items(), key=lambda x: x[1], reverse=True):
            self.log(f"  • {cat}: {cnt} dosya")
        self.log("=" * 60)

        self.root.after(0, lambda: self.lbl_table_summary.configure(
            text=f"Sonuç: {basarili_sayisi} başarılı, {tekrar_sayisi} kopya atlandı, {hata_sayisi} hata."
        ))
        self.set_ui_processing_state(False)

    def request_cancel(self):
        self.cancel_requested = True
        self.btn_stop.configure(state="disabled", text="Durduruluyor...")
        self.log("[BİLGİ] İptal talebi alındı, mevcut dosya tamamlanınca durdurulacak.")

    def calculate_hash(self, file_path: str) -> str:
        md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    md5.update(chunk)
            return md5.hexdigest()
        except Exception:
            return ""

    # --------------------------------------------------------------------------
    # ARAYÜZ YARDIMCILARI
    # --------------------------------------------------------------------------
    def _clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _add_tree_row(self, row_data):
        self.tree.insert("", "end", values=row_data)

    def _update_progress_ui(self, current, total, pct):
        self.progress_bar.set(pct)
        self.lbl_progress_count.configure(text=f"{current} / {total} (%{int(pct * 100)})")

    def set_ui_processing_state(self, processing: bool):
        self.is_processing = processing
        self.root.after(0, self._apply_ui_processing_state, processing)

    def _apply_ui_processing_state(self, processing: bool):
        if processing:
            self.btn_preview.configure(state="disabled")
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal", text="⏹ İptal Et")
            self.status_bar_lbl.configure(text="İşlem yürütülüyor...")
        else:
            self.btn_preview.configure(state="normal")
            self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled", text="⏹ İptal Et")
            self.status_bar_lbl.configure(text="İşlem tamamlandı veya hazır.")


# ==============================================================================
# GİRİŞ NOKTASI
# ==============================================================================
def main():
    root = ctk.CTk()
    app = ModernPDFOrganizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
