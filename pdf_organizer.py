import customtkinter as ctk
from tkinter import filedialog
import os
import hashlib
import shutil
import re
from pathlib import Path
import fitz
import threading

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BIRINCIL_PUAN = 5
IKINCIL_PUAN = 1
MIN_SKOR_ESIGI = 10

JUNK_TITLES_FILTER = [
    'untitled', 'isimsiz', 'abstract', 'introduction', 
    'microsoft word', '.doc', '.pdf', 'document', 'belge',
    'cover page', 'author', 'contents', 'new document', 'başlıksız'
]


def guvenli_dosya_adi_olustur(baslik_metni):
    if not baslik_metni:
        return None
    isim = baslik_metni.lower()
    isim = re.sub(r'[^\w\s-]', '', isim).strip()
    isim = re.sub(r'[\s-]+', '_', isim)
    isim = isim[:150]
    isim = isim.strip('_')
    return isim if isim else None


def super_akilli_baslik_bulucu(doc):
    try:
        meta = doc.metadata
        baslik = meta.get('title', None)
        if baslik:
            baslik = baslik.strip()
            if len(baslik) > 5:
                baslik_lower = baslik.lower()
                is_junk = False
                for junk in JUNK_TITLES_FILTER:
                    if junk in baslik_lower:
                        is_junk = True
                        break
                if not is_junk:
                    return baslik
    except Exception:
        pass

    for sayfa_no in range(min(3, doc.page_count)):
        try:
            page = doc[sayfa_no]
            page_height = page.rect.height
            ust_sinir_y_koordinati = page_height * 0.35
            max_font_size = 0
            potansiyel_basliklar = []
            blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_BLOCKS)["blocks"]
            for block in blocks:
                if block["bbox"][1] > ust_sinir_y_koordinati:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        font_size = round(span["size"], 2)
                        y_pos = round(span["bbox"][1], 2)
                        text = span["text"].strip()
                        if text and len(text) > 3:
                            potansiyel_basliklar.append((font_size, y_pos, text))
                            if font_size > max_font_size:
                                max_font_size = font_size
            if not potansiyel_basliklar:
                continue
            tolerans_esigi = max_font_size * 0.95
            bulunan_baslik_parcalari = []
            for (font_size, y_pos, text) in potansiyel_basliklar:
                if font_size >= tolerans_esigi:
                    bulunan_baslik_parcalari.append((y_pos, text))
            if not bulunan_baslik_parcalari:
                continue
            bulunan_baslik_parcalari.sort(key=lambda x: x[0])
            tam_baslik = " ".join([text for y_pos, text in bulunan_baslik_parcalari])
            tam_baslik = re.sub(r'\s+', ' ', tam_baslik).strip()
            if len(tam_baslik) >= 5 and tam_baslik.lower() not in JUNK_TITLES_FILTER:
                return tam_baslik
        except Exception:
            continue
    return None


class PDFOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Arşiv Organizasyonu")
        self.root.geometry("1300x900")
        self.source_folder = ctk.StringVar()
        self.target_folder = ctk.StringVar()
        self.processing = False
        self.gecerli_kategori_profilleri = {}
        self.setup_ui()
    
    def setup_ui(self):
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))
        
        title_label = ctk.CTkLabel(header_frame, text="Arşiv Organizasyonu", 
                                   font=ctk.CTkFont(size=26, weight="bold"))
        title_label.pack(side="left")
        
        subtitle_label = ctk.CTkLabel(header_frame, text="Akıllı PDF Organizasyon Sistemi", 
                                      font=ctk.CTkFont(size=11))
        subtitle_label.pack(side="left", padx=(12, 0))
        
        tabview = ctk.CTkTabview(main_frame, height=780, corner_radius=8)
        tabview.pack(fill="both", expand=True, padx=3, pady=3)
        
        tab1 = tabview.add("Organize Et")
        tab2 = tabview.add("Nasıl Kullanılır?")
        
        self.setup_main_tab(tab1)
        self.setup_help_tab(tab2)
        
        footer_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        footer_frame.pack(fill="x", pady=(5, 0))
        footer_label = ctk.CTkLabel(footer_frame, text="S.Kaan Ciftci - 2025", 
                                    font=ctk.CTkFont(size=10))
        footer_label.pack()
    
    def setup_main_tab(self, tab):
        left_column = ctk.CTkFrame(tab, fg_color="transparent")
        left_column.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)
        
        right_column = ctk.CTkFrame(tab, fg_color="transparent")
        right_column.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)
        
        folder_section = ctk.CTkFrame(left_column, corner_radius=8)
        folder_section.pack(fill="x", pady=5)
        
        section_title = ctk.CTkLabel(folder_section, text="Klasör Seçimi", 
                                     font=ctk.CTkFont(size=14, weight="bold"))
        section_title.pack(anchor="w", padx=12, pady=(10, 8))
        
        source_frame = ctk.CTkFrame(folder_section, fg_color="transparent")
        source_frame.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(source_frame, text="Kaynak:", width=80, 
                    font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 8))
        source_entry = ctk.CTkEntry(source_frame, textvariable=self.source_folder, 
                                    height=32, font=ctk.CTkFont(size=11))
        source_entry.pack(side="left", padx=3, fill="x", expand=True)
        ctk.CTkButton(source_frame, text="Gözat", command=self.browse_source, 
                     width=90, height=32, font=ctk.CTkFont(size=11)).pack(side="left", padx=(8, 0))
        
        target_frame = ctk.CTkFrame(folder_section, fg_color="transparent")
        target_frame.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(target_frame, text="Hedef:", width=80, 
                    font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 8))
        target_entry = ctk.CTkEntry(target_frame, textvariable=self.target_folder, 
                                    height=32, font=ctk.CTkFont(size=11))
        target_entry.pack(side="left", padx=3, fill="x", expand=True)
        ctk.CTkButton(target_frame, text="Gözat", command=self.browse_target, 
                     width=90, height=32, font=ctk.CTkFont(size=11)).pack(side="left", padx=(8, 0))
        
        category_section = ctk.CTkFrame(left_column, corner_radius=8)
        category_section.pack(fill="both", expand=True, pady=5)
        
        category_title = ctk.CTkLabel(category_section, text="Kategori Yöneticisi", 
                                      font=ctk.CTkFont(size=14, weight="bold"))
        category_title.pack(anchor="w", padx=12, pady=(10, 8))
        
        category_mgmt_frame = ctk.CTkFrame(category_section, fg_color="transparent")
        category_mgmt_frame.pack(fill="x", padx=12, pady=3)
        
        ctk.CTkLabel(category_mgmt_frame, text="Kategori Adı:", width=120, 
                    font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=8, pady=4, sticky="w")
        self.kategori_adi_entry = ctk.CTkEntry(category_mgmt_frame, height=30,
                                               font=ctk.CTkFont(size=11))
        self.kategori_adi_entry.grid(row=0, column=1, padx=8, pady=4, sticky="ew")
        category_mgmt_frame.columnconfigure(1, weight=1)
        
        ctk.CTkLabel(category_mgmt_frame, text="Birincil Kelimeler:", width=120, 
                    font=ctk.CTkFont(size=11)).grid(row=1, column=0, padx=8, pady=4, sticky="w")
        self.birincil_kelimeler_entry = ctk.CTkEntry(category_mgmt_frame, height=30,
                                                      placeholder_text="digital twin, nvidia omniverse, ...",
                                                      font=ctk.CTkFont(size=11))
        self.birincil_kelimeler_entry.grid(row=1, column=1, padx=8, pady=4, sticky="ew")
        
        ctk.CTkLabel(category_mgmt_frame, text="İkincil Kelimeler:", width=120, 
                    font=ctk.CTkFont(size=11)).grid(row=2, column=0, padx=8, pady=4, sticky="w")
        self.ikincil_kelimeler_entry = ctk.CTkEntry(category_mgmt_frame, height=30,
                                                     placeholder_text="iot, industry 4.0, monitoring, ...",
                                                     font=ctk.CTkFont(size=11))
        self.ikincil_kelimeler_entry.grid(row=2, column=1, padx=8, pady=4, sticky="ew")
        
        add_button_frame = ctk.CTkFrame(category_mgmt_frame, fg_color="transparent")
        add_button_frame.grid(row=3, column=0, columnspan=2, pady=8)
        ctk.CTkButton(add_button_frame, text="Kategoriyi Ekle", 
                     command=self.kategori_ekle, width=160, height=32,
                     font=ctk.CTkFont(size=11, weight="bold")).pack()
        
        profiles_label = ctk.CTkLabel(category_section, text="Oluşturulan Kategoriler:", 
                                      font=ctk.CTkFont(size=12, weight="bold"))
        profiles_label.pack(anchor="w", padx=12, pady=(5, 5))
        
        self.kategori_profilleri_textbox = ctk.CTkTextbox(category_section, height=80, 
                                                          wrap="word", state="disabled",
                                                          font=ctk.CTkFont(size=10))
        self.kategori_profilleri_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        
        self.kategori_profilleri_textbox.configure(state="normal")
        self.kategori_profilleri_textbox.insert("1.0", "Henüz kategori eklenmedi. Yukarıdaki formu doldurup 'Kategoriyi Ekle' butonuna tıklayın.\n")
        self.kategori_profilleri_textbox.configure(state="disabled")
        
        action_section = ctk.CTkFrame(right_column, corner_radius=8)
        action_section.pack(fill="x", pady=5)
        
        action_title = ctk.CTkLabel(action_section, text="İşlem Kontrolü", 
                                   font=ctk.CTkFont(size=14, weight="bold"))
        action_title.pack(anchor="w", padx=12, pady=(10, 8))
        
        button_frame = ctk.CTkFrame(action_section, fg_color="transparent")
        button_frame.pack(fill="x", padx=12, pady=(0, 10))
        
        self.start_button = ctk.CTkButton(button_frame, text="Organizasyonu Başlat", 
                                          command=self.start_organization, 
                                          font=ctk.CTkFont(size=13, weight="bold"),
                                          height=40, width=220, corner_radius=6)
        self.start_button.pack(pady=6)
        
        self.progress_bar = ctk.CTkProgressBar(button_frame, mode="indeterminate", 
                                              height=18, corner_radius=8)
        self.progress_bar.pack(fill="x", padx=15, pady=4)
        self.progress_bar.set(0)
        
        log_section = ctk.CTkFrame(right_column, corner_radius=8)
        log_section.pack(fill="both", expand=True, pady=5)
        
        log_title = ctk.CTkLabel(log_section, text="Durum Logu", 
                                font=ctk.CTkFont(size=14, weight="bold"))
        log_title.pack(anchor="w", padx=12, pady=(10, 8))
        
        log_frame = ctk.CTkFrame(log_section, fg_color="transparent")
        log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        
        self.log_text = ctk.CTkTextbox(log_frame, wrap="word", 
                                      state="disabled", font=ctk.CTkFont(size=10))
        self.log_text.pack(fill="both", expand=True)
    
    def setup_help_tab(self, tab):
        help_frame = ctk.CTkScrollableFrame(tab)
        help_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(help_frame, text="Kullanım Kılavuzu", 
                            font=ctk.CTkFont(size=22, weight="bold"))
        title.pack(pady=(0, 20))
        
        steps = [
            ("1", "KAYNAK KLASÖR SEÇİMİ", 
             "Organize edilecek PDF dosyalarının bulunduğu klasörü seçin.\n" +
             "• 'Gözat' butonuna tıklayın\n" +
             "• Klasörü seçin ve onaylayın\n" +
             "• Alt klasörlerdeki PDF'ler de otomatik olarak taranır"),
            
            ("2", "HEDEF KLASÖR SEÇİMİ", 
             "Organize edilmiş dosyaların kopyalanacağı klasörü seçin.\n" +
             "• 'Gözat' butonuna tıklayın\n" +
             "• Hedef klasörü seçin veya yeni bir klasör oluşturun\n" +
             "• Dosyalar bu klasör içinde kategorilere ayrılacak"),
            
            ("3", "KATEGORİ OLUŞTURMA", 
             "PDF'leri kategorize etmek için kategori profilleri oluşturun.\n\n" +
             "Kategori Adı:\n" +
             "• Eklemek istediğiniz kategori adını girin (örn: 'Dijital İkiz')\n\n" +
             "Birincil Kelimeler:\n" +
             "• Yüksek öncelikli anahtar kelimeleri virgülle ayırarak girin\n" +
             "• Örnek: 'digital twin, nvidia omniverse, digital shadow'\n" +
             "• Her bulunduğunda +5 puan kazanır\n\n" +
             "İkincil Kelimeler:\n" +
             "• Düşük öncelikli anahtar kelimeleri virgülle ayırarak girin\n" +
             "• Örnek: 'iot, industry 4.0, monitoring, real-time'\n" +
             "• Her bulunduğunda +1 puan kazanır\n\n" +
             "• 'Kategoriyi Ekle' butonuna tıklayın\n" +
             "• İstediğiniz kadar kategori ekleyebilirsiniz"),
            
            ("4", "ORGANİZASYON İŞLEMİ", 
             "Tüm ayarlar yapıldıktan sonra organizasyonu başlatın.\n\n" +
             "İşlem Adımları:\n" +
             "• PDF dosyaları taranır (alt klasörler dahil)\n" +
             "• Tekrar eden dosyalar tespit edilir ve atlanır\n" +
             "• Her PDF'in başlığı bulunur ve dosya yeniden adlandırılır\n" +
             "• PDF içeriği analiz edilir ve kategorilere ayrılır\n" +
             "• Dosyalar ilgili klasörlere kopyalanır\n\n" +
             "• İşlem sırasında progress bar animasyon gösterir\n" +
             "• Durum logu penceresinde detaylı bilgi görüntülenir"),
            
            ("5", "PUANLAMA SİSTEMİ", 
             "Akıllı kategorizasyon için ağırlıklı puanlama sistemi kullanılır.\n\n" +
             "Puanlama:\n" +
             "• Birincil kelimeler: Her bulunduğunda +5 puan\n" +
             "• İkincil kelimeler: Her bulunduğunda +1 puan\n" +
             "• Minimum 10 puan eşiği: Bu eşiğin altında kalan dosyalar 'Diger' klasörüne gider\n\n" +
             "Kategori Seçimi:\n" +
             "• En yüksek skoru alan kategori seçilir\n" +
             "• Eğer hiçbir kategori 10 puan alamazsa 'Diger' klasörüne atanır"),
            
            ("6", "BAŞLIK BULMA SİSTEMİ", 
             "PDF dosyalarının başlıkları 2 aşamalı sistemle bulunur.\n\n" +
             "Aşama 1 - Meta Veri Kontrolü:\n" +
             "• PDF'in meta verisinden başlık aranır\n" +
             "• Geçerli ve temiz başlık bulunursa kullanılır\n\n" +
             "Aşama 2 - Sayfa Analizi:\n" +
             "• Meta veri yoksa veya geçersizse sayfa analizi yapılır\n" +
             "• İlk 3 sayfanın üst kısmı (%35) taranır\n" +
             "• En büyük font boyutuna sahip metin başlık olarak kabul edilir\n" +
             "• Sırayla 1., 2. ve 3. sayfaya bakılır"),
            
            ("7", "ÖNEMLİ NOTLAR", 
             "• Dosyalar kopyalanır, taşınmaz (güvenlik için)\n" +
             "• Tekrar eden dosyalar otomatik olarak atlanır\n" +
             "• Aynı isimde dosya varsa otomatik olarak sayaç eklenir (örn: dosya_1.pdf)\n" +
             "• İşlem sırasında GUI donmaz (threading kullanılır)\n" +
             "• Tüm işlemler durum logu penceresinde görüntülenir\n" +
             "• İşlem sonunda kategori dağılımı özeti gösterilir")
        ]
        
        for num, heading, content in steps:
            step_frame = ctk.CTkFrame(help_frame, corner_radius=10)
            step_frame.pack(fill="x", pady=10, padx=8)
            
            header_frame = ctk.CTkFrame(step_frame, fg_color="transparent")
            header_frame.pack(fill="x", padx=18, pady=(12, 8))
            
            num_label = ctk.CTkLabel(header_frame, text=num, 
                                    font=ctk.CTkFont(size=16, weight="bold"),
                                    width=30)
            num_label.pack(side="left", padx=(0, 10))
            
            header = ctk.CTkLabel(header_frame, text=heading, 
                                 font=ctk.CTkFont(size=16, weight="bold"))
            header.pack(side="left")
            
            content_label = ctk.CTkLabel(step_frame, text=content, 
                                        font=ctk.CTkFont(size=11),
                                        justify="left", anchor="w")
            content_label.pack(anchor="w", padx=18, pady=(0, 12))
    
    def browse_source(self):
        folder = filedialog.askdirectory(title="Kaynak Klasörü Seçin")
        if folder:
            self.source_folder.set(folder)
    
    def browse_target(self):
        folder = filedialog.askdirectory(title="Hedef Klasörü Seçin")
        if folder:
            self.target_folder.set(folder)
    
    def kategori_ekle(self):
        kategori_adi = self.kategori_adi_entry.get().strip()
        birincil_str = self.birincil_kelimeler_entry.get().strip()
        ikincil_str = self.ikincil_kelimeler_entry.get().strip()
        
        if not kategori_adi or not birincil_str:
            self.log_message("[HATA] Kategori adı ve Birincil kelimeler zorunludur.")
            return
        
        temiz_kategori_adi = guvenli_dosya_adi_olustur(kategori_adi)
        if not temiz_kategori_adi:
            self.log_message("[HATA] Geçersiz kategori adı. Lütfen geçerli karakterler kullanın.")
            return
        
        birincil_liste = []
        for kelime in birincil_str.split(','):
            kelime_temiz = kelime.strip().lower()
            if kelime_temiz:
                birincil_liste.append(kelime_temiz)
        
        if not birincil_liste:
            self.log_message("[HATA] En az bir birincil kelime girmelisiniz.")
            return
        
        ikincil_liste = []
        for kelime in ikincil_str.split(','):
            kelime_temiz = kelime.strip().lower()
            if kelime_temiz:
                ikincil_liste.append(kelime_temiz)
        
        self.gecerli_kategori_profilleri[temiz_kategori_adi] = {
            "birincil": birincil_liste,
            "ikincil": ikincil_liste
        }
        
        self.kategori_adi_entry.delete(0, 'end')
        self.birincil_kelimeler_entry.delete(0, 'end')
        self.ikincil_kelimeler_entry.delete(0, 'end')
        
        self.kategori_profilleri_textbox.configure(state="normal")
        if "Henüz kategori eklenmedi" in self.kategori_profilleri_textbox.get("1.0", "end"):
            self.kategori_profilleri_textbox.delete("1.0", "end")
        
        mesaj = f"[EKLENDİ] {temiz_kategori_adi} (Birincil: {len(birincil_liste)}, İkincil: {len(ikincil_liste)})\n"
        self.kategori_profilleri_textbox.insert("end", mesaj)
        self.kategori_profilleri_textbox.see("end")
        self.kategori_profilleri_textbox.configure(state="disabled")
        
        self.log_message(f"[KATEGORİ EKLENDİ] {temiz_kategori_adi} - Birincil: {len(birincil_liste)} kelime, İkincil: {len(ikincil_liste)} kelime")
    
    def log_message(self, message):
        self.root.after(0, self._log_message, message)
    
    def _log_message(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
    
    def calculate_file_hash(self, file_path):
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.log_message(f"[HATA] Hash hesaplanamadı: {os.path.basename(file_path)} - {str(e)}")
            return None
    
    def get_pdf_full_text(self, doc):
        text = ""
        try:
            for page_num in range(len(doc)):
                text += doc[page_num].get_text()
        except Exception as e:
            self.log_message(f"[UYARI] Sayfa {page_num + 1} okunamadı: {str(e)}")
        return text.lower()
    
    def akilli_kategorize_et(self, doc, kategori_profilleri):
        metin = self.get_pdf_full_text(doc)
        if not metin:
            return "Diger", 0
        if not kategori_profilleri:
            return "Diger", 0
        
        kategori_skorlari = {}
        for kategori_adi, profil in kategori_profilleri.items():
            toplam_skor = 0
            for kelime in profil.get("birincil", []):
                kelime_lower = kelime.lower()
                count = metin.count(kelime_lower)
                toplam_skor += count * BIRINCIL_PUAN
            for kelime in profil.get("ikincil", []):
                kelime_lower = kelime.lower()
                count = metin.count(kelime_lower)
                toplam_skor += count * IKINCIL_PUAN
            if toplam_skor > 0:
                kategori_skorlari[kategori_adi] = toplam_skor
        
        if not kategori_skorlari:
            return "Diger", 0
        
        en_iyi_kategori = max(kategori_skorlari, key=kategori_skorlari.get)
        en_yuksek_skor = kategori_skorlari[en_iyi_kategori]
        
        if en_yuksek_skor < MIN_SKOR_ESIGI:
            return "Diger", en_yuksek_skor
        
        return en_iyi_kategori, en_yuksek_skor
    
    def start_organization(self):
        if self.processing:
            return
        self.start_button.configure(state="disabled", text="İşleniyor...")
        self.progress_bar.start()
        self.processing = True
        thread = threading.Thread(target=self.organize_files, daemon=True)
        thread.start()
    
    def organize_files(self):
        source = self.source_folder.get().strip()
        target = self.target_folder.get().strip()
        
        if not source or not os.path.isdir(source):
            self.log_message("[HATA] Geçerli bir kaynak klasör seçin!")
            self._finish_processing()
            return
        
        if not target or not os.path.isdir(target):
            self.log_message("[HATA] Geçerli bir hedef klasör seçin!")
            self._finish_processing()
            return
        
        if not self.gecerli_kategori_profilleri:
            self.log_message("[HATA] Lütfen en az bir kategori ekleyin!")
            self._finish_processing()
            return
        
        categories = list(self.gecerli_kategori_profilleri.keys()) + ["Diger"]
        
        self.log_message("=== Organizasyon Başlatıldı ===")
        self.log_message(f"Kaynak: {source}")
        self.log_message(f"Hedef: {target}")
        self.log_message(f"Puanlama: Birincil={BIRINCIL_PUAN}, İkincil={IKINCIL_PUAN}, Min Eşik={MIN_SKOR_ESIGI}")
        self.log_message(f"Kategoriler: {', '.join(categories)}")
        self.log_message(f"Toplam Kategori Sayısı: {len(self.gecerli_kategori_profilleri)}\n")
        
        for category in categories:
            folder_path = os.path.join(target, category)
            os.makedirs(folder_path, exist_ok=True)
        
        seen_hashes = set()
        processed_count = 0
        tekrar_count = 0
        categorized_count = 0
        category_stats = {cat: 0 for cat in categories}
        
        self.log_message("Dosyalar taranıyor...\n")
        
        pdf_files = []
        for root_dir, dirs, files in os.walk(source):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root_dir, file))
        
        self.log_message(f"Toplam {len(pdf_files)} PDF dosyası bulundu.\n")
        
        for idx, pdf_path in enumerate(pdf_files, 1):
            file_hash = self.calculate_file_hash(pdf_path)
            if not file_hash:
                continue
            
            if file_hash in seen_hashes:
                tekrar_count += 1
                self.log_message(f"[TEKRAR] Atlandı ({idx}/{len(pdf_files)}): {os.path.basename(pdf_path)}")
                continue
            
            seen_hashes.add(file_hash)
            
            try:
                doc = fitz.open(pdf_path)
                
                bulunan_baslik = super_akilli_baslik_bulucu(doc)
                
                yeni_dosya_adi_tabani = ""
                if bulunan_baslik:
                    yeni_dosya_adi_tabani = guvenli_dosya_adi_olustur(bulunan_baslik)
                
                if not yeni_dosya_adi_tabani:
                    orijinal_ad_uzantisiz = Path(pdf_path).stem
                    yeni_dosya_adi_tabani = guvenli_dosya_adi_olustur(orijinal_ad_uzantisiz)
                    if not yeni_dosya_adi_tabani:
                        yeni_dosya_adi_tabani = f"dosya_{idx}"
                
                category, skor = self.akilli_kategorize_et(doc, self.gecerli_kategori_profilleri)
                
                doc.close()
                
                hedef_kategori_klasoru = os.path.join(target, category)
                
                yeni_dosya_adi = f"{yeni_dosya_adi_tabani}.pdf"
                hedef_yol = os.path.join(hedef_kategori_klasoru, yeni_dosya_adi)
                
                sayac = 1
                while os.path.exists(hedef_yol):
                    yeni_dosya_adi = f"{yeni_dosya_adi_tabani}_{sayac}.pdf"
                    hedef_yol = os.path.join(hedef_kategori_klasoru, yeni_dosya_adi)
                    sayac += 1
                
                shutil.copy2(pdf_path, hedef_yol)
                
                processed_count += 1
                categorized_count += 1
                category_stats[category] = category_stats.get(category, 0) + 1
                
                original_name_display = os.path.basename(pdf_path)
                skor_bilgisi = f" (Skor: {skor})" if skor > 0 else ""
                baslik_bilgisi = f" [{bulunan_baslik[:50]}...]" if bulunan_baslik else ""
                self.log_message(f"[BAŞARILI] ({idx}/{len(pdf_files)}) {original_name_display}{baslik_bilgisi} -> {category}/{yeni_dosya_adi}{skor_bilgisi}")
                
            except Exception as e:
                try:
                    if 'doc' in locals():
                        doc.close()
                except:
                    pass
                self.log_message(f"[HATA] İşlenemedi: {os.path.basename(pdf_path)} - {str(e)}")
        
        self.log_message("\n" + "="*60)
        self.log_message("=== İŞLEM TAMAMLANDI ===")
        self.log_message(f"Toplam İşlenen Benzersiz PDF: {processed_count}")
        self.log_message(f"Atlanan Tekrar PDF Sayısı: {tekrar_count}")
        self.log_message(f"Kategorize Edilen: {categorized_count}")
        self.log_message("\nKategori Dağılımı:")
        for cat, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                self.log_message(f"  - {cat}: {count} dosya")
        self.log_message("="*60)
        
        self._finish_processing()
    
    def _finish_processing(self):
        self.processing = False
        self.root.after(0, self._finish_processing_ui)
    
    def _finish_processing_ui(self):
        self.start_button.configure(state="normal", text="Organizasyonu Başlat")
        self.progress_bar.stop()
        self.progress_bar.set(0)


def main():
    root = ctk.CTk()
    app = PDFOrganizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
