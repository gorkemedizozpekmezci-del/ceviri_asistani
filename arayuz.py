import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import keyboard  
import threading 

# YENİ: ayarlar.py'den SaydamlikAyari sınıfını içe aktarıyoruz
from ayarlar import SaydamlikAyari

class Arayuz:
    def __init__(self, kontrolcu):
        self.kontrolcu = kontrolcu 
        self.root = tk.Tk()
        
        self.secim_penceresi = None
        self.secim_dikdortgeni = None
        self.baslangic_x = 0
        self.baslangic_y = 0
        
        self.sesli_okuma_var = tk.BooleanVar(value=False)
        
        self.kurulum_yap()

    def _ayar_getir(self, alan_adi, varsayilan):
        """Combobox'ları ilk açılışta kayıtlı config.json değerleriyle doldurmak için
        kullanılan güvenli okuma yardımcısı. ayarlar nesnesi yoksa varsayılanı döner."""
        ayarlar_nesnesi = getattr(self.kontrolcu, "ayarlar", None)
        if ayarlar_nesnesi is None:
            return varsayilan
        return getattr(ayarlar_nesnesi, alan_adi, varsayilan)

    def _ayar_kaydet(self, alan_adi, deger):
        """Combobox değiştiğinde seçimi anında config.json'a kalıcı olarak yazar."""
        ayarlar_nesnesi = getattr(self.kontrolcu, "ayarlar", None)
        if ayarlar_nesnesi is None:
            return
        try:
            setattr(ayarlar_nesnesi, alan_adi, deger)
            ayarlar_nesnesi.kaydet()
        except Exception as e:
            print(f"[Arayüz Ayar Kaydetme Hatası]: {e}")

    def kurulum_yap(self):
        self.root.title("Yapay Zeka Oyun Asistanı")
        self.root.overrideredirect(True) 
        self.root.geometry("620x550")
        self.root.attributes("-topmost", True)
        
        # YENİ: Başlangıç saydamlığını config.json'dan çekiyoruz
        baslangic_saydamlik = 0.95
        if hasattr(self.kontrolcu, "ayarlar") and hasattr(self.kontrolcu.ayarlar, "saydamlik"):
             baslangic_saydamlik = self.kontrolcu.ayarlar.saydamlik / 100.0
             
        self.root.attributes("-alpha", baslangic_saydamlik) 
        
        self.bg_main = "#0F172A"       
        self.bg_panel = "#1E293B"      
        self.bg_topbar = "#020617"     
        self.text_primary = "#F8FAFC"  
        self.text_muted = "#94A3B8"    
        self.accent = "#38BDF8"        
        self.button_bg = "#334155"     
        
        self.root.configure(bg=self.bg_main)
        
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
            
        style.configure("TCombobox", fieldbackground=self.bg_panel, background=self.button_bg,
                        foreground=self.text_primary, arrowcolor=self.accent, bordercolor=self.bg_main)
        
        style.map("TCombobox", fieldbackground=[("readonly", self.bg_panel)],
                  foreground=[("readonly", self.text_primary)], selectbackground=[("readonly", self.accent)],
                  selectforeground=[("readonly", "#0F172A")])
        
        self.ust_bar = tk.Frame(self.root, bg=self.bg_topbar, height=35)
        self.ust_bar.pack(fill=tk.X, side=tk.TOP)
        self.ust_bar.bind("<ButtonPress-1>", self.pencere_suruklemeye_basla)
        self.ust_bar.bind("<B1-Motion>", self.pencere_surukle)
        
        baslik = tk.Label(self.ust_bar, text=" 🌍 G-Translate Asistanı PRO", fg=self.accent, bg=self.bg_topbar, font=("Segoe UI", 10, "bold"))
        baslik.pack(side=tk.LEFT, padx=10)
        baslik.bind("<ButtonPress-1>", self.pencere_suruklemeye_basla)
        baslik.bind("<B1-Motion>", self.pencere_surukle)

        tk.Button(self.ust_bar, text=" ✕ ", bg=self.bg_topbar, fg="#F87171", bd=0, font=("Arial", 12, "bold"), activebackground="#EF4444", activeforeground="white", command=self.kontrolcu.tamamen_kapat).pack(side=tk.RIGHT, padx=5)
        tk.Button(self.ust_bar, text=" ⚙️ Ayarlar ", bg=self.bg_topbar, fg=self.text_primary, bd=0, font=("Segoe UI", 9), activebackground=self.button_bg, command=self.ayarlar_penceresi_ac).pack(side=tk.RIGHT, padx=5)

        panel_frame = tk.Frame(self.root, bg=self.bg_main)
        panel_frame.pack(fill=tk.X, padx=15, pady=15)

        tk.Label(panel_frame, text="Oyun Profili:", bg=self.bg_main, fg=self.text_muted, font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=4)
        self.profil_secimi = ttk.Combobox(panel_frame, values=list(self.kontrolcu.ayarlar.profiller.keys()), state="readonly", width=26)
        self.profil_secimi.set("Manuel Seçim")
        self.profil_secimi.grid(row=0, column=1, padx=10, pady=4, sticky="w")
        self.profil_secimi.bind("<<ComboboxSelected>>", self.kontrolcu.profil_degistir)
        
        tk.Button(panel_frame, text="[+] Kaydet", bg="#2563EB", fg="white", bd=0, font=("Segoe UI", 8, "bold"), padx=8, pady=2, command=self.kontrolcu.profili_kaydet).grid(row=0, column=2, padx=5)

        tk.Label(panel_frame, text="Çeviri Motoru:", bg=self.bg_main, fg=self.text_muted, font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=4)
        self.motor_secimi = ttk.Combobox(panel_frame, values=["Yerel Yapay Zeka (İnternetsiz)", "Gemini AI (Akıllı)", "Standart (Hızlı)"], state="readonly", width=26)
        # DÜZELTME: Önceden burada her zaman sabit "Yerel Yapay Zeka" seçiliyordu;
        # kullanıcının kaydettiği motor tercihi (config.json) hiç yüklenmiyordu.
        self.motor_secimi.set(self._ayar_getir("motor_secimi", "Yerel Yapay Zeka (İnternetsiz)"))
        self.motor_secimi.grid(row=1, column=1, columnspan=2, padx=10, pady=4, sticky="w")
        self.motor_secimi.bind("<<ComboboxSelected>>", lambda e: self._ayar_kaydet("motor_secimi", self.motor_secimi.get()))

        tk.Label(panel_frame, text="Çeviri Yönü:", bg=self.bg_main, fg=self.text_muted, font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", pady=4)
        dil_frame = tk.Frame(panel_frame, bg=self.bg_main)
        dil_frame.grid(row=2, column=1, columnspan=2, padx=10, pady=4, sticky="w")
        
        self.ocr_dili_secimi = ttk.Combobox(dil_frame, values=["İngilizce", "Rusça", "İspanyolca", "Çince"], state="readonly", width=10)
        # DÜZELTME: Kayıtlı OCR dili tercihi (config.json) daha önce hiç okunmuyordu.
        self.ocr_dili_secimi.set(self._ayar_getir("ocr_dili", "İngilizce"))
        self.ocr_dili_secimi.pack(side=tk.LEFT)
        self.ocr_dili_secimi.bind("<<ComboboxSelected>>", self.kontrolcu.ocr_dilini_guncelle)

        tk.Label(dil_frame, text="  ➡️  Hedef: ", bg=self.bg_main, fg=self.text_muted, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        
        self.hedef_dil = ttk.Combobox(dil_frame, values=["Türkçe", "İngilizce", "İspanyolca", "Almanca", "Fransızca", "Rusça", "Çince", "Japonca", "Korece", "Arapça", "İtalyanca", "Portekizce"], state="readonly", width=10)
        # DÜZELTME: Kayıtlı hedef dil tercihi daha önce hiç okunmuyor, her açılışta
        # sabit "Türkçe" seçiliyordu.
        self.hedef_dil.set(self._ayar_getir("hedef_dil", "Türkçe"))
        self.hedef_dil.pack(side=tk.LEFT)
        self.hedef_dil.bind("<<ComboboxSelected>>", lambda e: self._ayar_kaydet("hedef_dil", self.hedef_dil.get()))

        alt_panel = tk.Frame(self.root, bg=self.bg_main)
        alt_panel.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=(0, 15)) 
        
        self.kaynak_dil_alt = ttk.Combobox(alt_panel, values=["Otomatik", "Türkçe", "İngilizce", "İspanyolca", "Almanca", "Fransızca", "Rusça", "Çince", "Japonca", "Korece", "Arapça", "İtalyanca", "Portekizce"], state="readonly", width=10)
        # DÜZELTME: Kayıtlı manuel-çeviri kaynak dili artık hatırlanıyor.
        self.kaynak_dil_alt.set(self._ayar_getir("kaynak_dil", "Otomatik"))
        self.kaynak_dil_alt.pack(side=tk.LEFT, padx=(0, 5))
        self.kaynak_dil_alt.bind("<<ComboboxSelected>>", lambda e: self._ayar_kaydet("kaynak_dil", self.kaynak_dil_alt.get()))
        
        tk.Label(alt_panel, text="➔", bg=self.bg_main, fg=self.text_muted, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=2)
        
        self.hedef_dil_alt = ttk.Combobox(alt_panel, values=["Türkçe", "İngilizce", "İspanyolca", "Almanca", "Fransızca", "Rusça", "Çince", "Japonca", "Korece", "Arapça", "İtalyanca", "Portekizce"], state="readonly", width=10)
        # DÜZELTME: Kayıtlı manuel-çeviri hedef dili artık hatırlanıyor.
        self.hedef_dil_alt.set(self._ayar_getir("hedef_dil_alt", "İngilizce"))
        self.hedef_dil_alt.pack(side=tk.LEFT, padx=(5, 5))
        self.hedef_dil_alt.bind("<<ComboboxSelected>>", lambda e: self._ayar_kaydet("hedef_dil_alt", self.hedef_dil_alt.get()))
        
        self.cevap_kutusu = tk.Entry(alt_panel, bg=self.bg_panel, fg=self.text_muted, font=("Consolas", 10), insertbackground="white", bd=0)
        self.cevap_kutusu.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, ipady=5)
        
        self.placeholder_metni = "Yaz/Yapıştır ve ENTER'a bas..."
        self.cevap_kutusu.insert(0, self.placeholder_metni)
        
        self.cevap_kutusu.bind("<FocusIn>", self.placeholder_temizle)
        self.cevap_kutusu.bind("<FocusOut>", self.placeholder_geri_getir)
        self.cevap_kutusu.bind("<Return>", lambda e: self.kontrolcu.cevabi_cevir(None))

        self.btn_mikrofon = tk.Button(alt_panel, text="🎙️ Konuş", bg="#059669", fg="white", bd=0, font=("Segoe UI", 8, "bold"), padx=8, pady=4, activebackground="#10B981", activeforeground="white", command=self.kontrolcu.mikrofon_dinle_ve_cevir)
        self.btn_mikrofon.pack(side=tk.RIGHT, padx=(5, 0))

        durum_ust_frame = tk.Frame(self.root, bg=self.bg_main)
        durum_ust_frame.pack(side=tk.TOP, fill=tk.X, padx=15, pady=(5, 0))

        self.durum_etiketi = tk.Label(durum_ust_frame, text="Sistem Yükleniyor...", fg="#F87171", bg=self.bg_main, font=("Segoe UI", 9, "bold"))
        self.durum_etiketi.pack(side=tk.LEFT) 
        
        tk.Button(durum_ust_frame, text="📋 Kopyala", bg=self.button_bg, fg=self.text_primary, bd=0, font=("Segoe UI", 8), padx=5, command=self.ceviri_kopyala).pack(side=tk.RIGHT)

        self.ceviri_ekrani = tk.Text(self.root, height=8, font=("Consolas", 11), wrap=tk.WORD, bg=self.bg_panel, fg=self.text_primary, bd=0, insertbackground="white", padx=12, pady=12)
        self.ceviri_ekrani.pack(side=tk.TOP, pady=5, fill=tk.BOTH, expand=True, padx=15)

    def durum_metnini_guncelle(self, durum="Beklemede", renk="#F87171"):
        if hasattr(self.kontrolcu, "kisayollar"):
            ks = self.kontrolcu.kisayollar
        else:
            ks = {"alan_sec": "f8", "oto_cevir": "f9", "tek_cekim": "f10"}
            
        f8 = ks.get("alan_sec", "f8").upper()
        f9 = ks.get("oto_cevir", "f9").upper()
        f10 = ks.get("tek_cekim", "f10").upper()
        
        metin = f"{durum} ({f8}: Alan Seç | {f9}: Oto | {f10}: Alan Çevir)"
        self.durum_etiketi.config(text=metin, fg=renk)

    def placeholder_temizle(self, event):
        if self.cevap_kutusu.get() == self.placeholder_metni:
            self.cevap_kutusu.delete(0, tk.END)
            self.cevap_kutusu.config(fg=self.accent)

    def placeholder_geri_getir(self, event):
        if not self.cevap_kutusu.get().strip():
            self.cevap_kutusu.delete(0, tk.END)
            self.cevap_kutusu.insert(0, self.placeholder_metni)
            self.cevap_kutusu.config(fg=self.text_muted)

    def ceviri_kopyala(self):
        metin = self.ceviri_ekrani.get(1.0, tk.END).strip()
        if metin:
            self.root.clipboard_clear()
            self.root.clipboard_append(metin)

    def pencere_suruklemeye_basla(self, event):
        self._x = event.x_root - self.root.winfo_rootx()
        self._y = event.y_root - self.root.winfo_rooty()

    def pencere_surukle(self, event):
        x = event.x_root - self._x
        y = event.y_root - self._y
        self.root.geometry(f"+{x}+{y}")

    def metin_guncelle(self, metin):
        self.ceviri_ekrani.delete(1.0, tk.END)
        self.ceviri_ekrani.insert(tk.END, metin)
        self.ceviri_ekrani.see(tk.END) 

    def durum_guncelle(self, metin, renk):
        self.durum_metnini_guncelle(durum=metin, renk=renk) 

    def cevap_kutusu_mesaj(self, mesaj):
        self.cevap_kutusu.config(fg=self.accent)
        self.cevap_kutusu.delete(0, tk.END)
        self.cevap_kutusu.insert(0, mesaj)
        
    def isim_sor(self, baslik, soru):
        return simpledialog.askstring(baslik, soru, parent=self.root)
        
    def uyari_goster(self, baslik, mesaj):
        messagebox.showinfo(baslik, mesaj)

    def ayarlar_penceresi_ac(self):
        ayar_win = tk.Toplevel(self.root)
        ayar_win.geometry("340x560")
        ayar_win.configure(bg=self.bg_panel)
        ayar_win.attributes("-topmost", True)
        ayar_win.resizable(False, False)
        ayar_win.overrideredirect(True) 

        ust_bar_ayar = tk.Frame(ayar_win, bg=self.bg_topbar, height=30)
        ust_bar_ayar.pack(fill=tk.X, side=tk.TOP)
        
        baslik = tk.Label(ust_bar_ayar, text=" ⚙️ Arayüz Ayarları", fg=self.text_muted, bg=self.bg_topbar, font=("Segoe UI", 9))
        baslik.pack(side=tk.LEFT, padx=5)
        tk.Button(ust_bar_ayar, text=" ✕ ", bg=self.bg_topbar, fg="#F87171", bd=0, font=("Arial", 10, "bold"), activebackground="#EF4444", activeforeground="white", command=ayar_win.destroy).pack(side=tk.RIGHT, padx=5)

        def basla(event):
            ayar_win._x = event.x
            ayar_win._y = event.y
            
        def surukle(event):
            x = event.x_root - ayar_win._x
            y = event.y_root - ayar_win._y
            ayar_win.geometry(f"+{x}+{y}")
            
        ust_bar_ayar.bind("<ButtonPress-1>", basla)
        ust_bar_ayar.bind("<B1-Motion>", surukle)
        baslik.bind("<ButtonPress-1>", basla)
        baslik.bind("<B1-Motion>", surukle)

        tk.Label(ayar_win, text="GÖRÜNÜM VE SES AYARLARI", fg=self.accent, bg=self.bg_panel, font=("Segoe UI", 10, "bold")).pack(pady=(15, 10))

        chk_ses = tk.Checkbutton(ayar_win, text="🔊 Çevirileri Sesli Oku", variable=self.sesli_okuma_var, bg=self.bg_panel, fg=self.text_primary, selectcolor="#0F172A", activebackground=self.bg_panel, activeforeground=self.accent, font=("Segoe UI", 9, "bold"))
        chk_ses.pack(pady=5)

        tk.Label(ayar_win, text="Pencere Boyutu", fg=self.text_primary, bg=self.bg_panel, font=("Segoe UI", 9)).pack(pady=(10, 0))
        boyut_frame = tk.Frame(ayar_win, bg=self.bg_panel)
        boyut_frame.pack(pady=5)
        
        tk.Button(boyut_frame, text="Küçük", bg=self.button_bg, fg="white", bd=0, width=8, pady=3, command=lambda: self.root.geometry("550x450")).pack(side=tk.LEFT, padx=5)
        tk.Button(boyut_frame, text="Orta", bg=self.button_bg, fg="white", bd=0, width=8, pady=3, command=lambda: self.root.geometry("620x550")).pack(side=tk.LEFT, padx=5)
        tk.Button(boyut_frame, text="Büyük", bg=self.button_bg, fg="white", bd=0, width=8, pady=3, command=lambda: self.root.geometry("800x700")).pack(side=tk.LEFT, padx=5)

        # --- YENİ EKLENEN SAYDAMLIK KONTROLCÜSÜ ---
        # Eski statik butonları kaldırıp yerine yazdığımız dinamik sınıfı koyuyoruz
        self.saydamlik_bileseni = SaydamlikAyari(
            ebeveyn_pencere=ayar_win, 
            ana_uygulama_penceresi=self.root, 
            ayarlar_nesnesi=getattr(self.kontrolcu, "ayarlar", None)
        )
        self.saydamlik_bileseni.pack(fill=tk.X, padx=20, pady=(15, 5))

        # --- YENİ EKLENEN: KULLANICI KENDİ GEMİNİ API ANAHTARINI GİREBİLİR ---
        # Program artık hiçbir API anahtarıyla birlikte dağıtılmıyor. Kullanıcı
        # isterse kendi Gemini anahtarını buraya girip "Gemini AI (Akıllı)"
        # motorunu etkinleştirebilir; hiç girmezse Yerel (NLLB) ve Standart
        # (Google Translate) motorlarıyla sorunsuz çalışmaya devam eder.
        tk.Label(ayar_win, text="🔑 Gemini API Anahtarı (opsiyonel)", fg=self.text_primary, bg=self.bg_panel, font=("Segoe UI", 9, "bold")).pack(pady=(15, 2))
        tk.Label(ayar_win, text="Boş bırakırsan Gemini olmadan (Yerel/Standart) devam edilir.", fg=self.text_muted, bg=self.bg_panel, font=("Segoe UI", 7)).pack()

        api_key_frame = tk.Frame(ayar_win, bg=self.bg_panel)
        api_key_frame.pack(pady=(8, 0))

        mevcut_key = self._ayar_getir("api_key", "")
        api_key_var = tk.StringVar(value=mevcut_key)
        api_key_entry = tk.Entry(api_key_frame, textvariable=api_key_var, width=24, show="•", bg="#0F172A", fg="white", insertbackground="white", relief="flat")
        api_key_entry.pack(side=tk.LEFT, ipady=4, padx=(0, 5))

        def _key_goster_gizle():
            if api_key_entry.cget("show") == "•":
                api_key_entry.config(show="")
                goster_btn.config(text="🙈")
            else:
                api_key_entry.config(show="•")
                goster_btn.config(text="👁️")

        goster_btn = tk.Button(api_key_frame, text="👁️", bg=self.button_bg, fg="white", bd=0, width=3, command=_key_goster_gizle)
        goster_btn.pack(side=tk.LEFT)

        def _key_kaydet():
            yeni_key = api_key_var.get().strip()
            if hasattr(self.kontrolcu, "api_anahtarini_guncelle"):
                self.kontrolcu.api_anahtarini_guncelle(yeni_key)
            else:
                self._ayar_kaydet("api_key", yeni_key)

        tk.Button(ayar_win, text="💾 API Anahtarını Kaydet", bg="#059669", fg="white", bd=0, width=25, font=("Segoe UI", 9, "bold"), activebackground="#10B981", activeforeground="white", command=_key_kaydet).pack(pady=(8, 0), ipady=5)

        tk.Button(ayar_win, text="⌨️ Kısayol Tuşlarını Değiştir", bg="#475569", fg="white", bd=0, width=25, font=("Segoe UI", 9, "bold"), activebackground="#334155", activeforeground="white", command=self.kisayol_ayarlarini_ac).pack(pady=(15, 0), ipady=5)
        tk.Button(ayar_win, text="Değişiklikleri Uygula", bg="#2563EB", fg="white", bd=0, width=25, font=("Segoe UI", 9, "bold"), activebackground="#1D4ED8", activeforeground="white", command=ayar_win.destroy).pack(pady=(15, 10), ipady=6)

    def kisayol_ayarlarini_ac(self):
        win = tk.Toplevel(self.root)
        win.title("Kısayol Ayarları")
        win.geometry("360x320")
        win.configure(bg=self.bg_panel)
        win.attributes("-topmost", True)
        win.resizable(False, False)

        tk.Label(win, text="⌨️ KISAYOL TUŞLARINI BELİRLEYİN", fg=self.accent, bg=self.bg_panel, font=("Segoe UI", 10, "bold")).pack(pady=(15, 10))

        frame = tk.Frame(win, bg=self.bg_panel)
        frame.pack(padx=20, pady=5, fill=tk.X)

        if hasattr(self.kontrolcu, "kisayollar"):
            ks = self.kontrolcu.kisayollar
        else:
            ks = {"alan_sec": "f8", "oto_cevir": "f9", "tek_cekim": "f10", "tam_ekran": "f11"}

        alanlar = [
            ("Alan Seçimi:", "alan_sec", ks.get("alan_sec", "f8")),
            ("Oto Çeviri Başlat/Dur:", "oto_cevir", ks.get("oto_cevir", "f9")),
            ("Tek Seferlik Alan Oku:", "tek_cekim", ks.get("tek_cekim", "f10")),
            ("Tam Ekran Oku:", "tam_ekran", ks.get("tam_ekran", "f11")),
        ]

        self.inputs = {}

        def tus_dinle_ve_yaz(entry_widget):
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, "Tuşa Basın...")
            entry_widget.config(fg=self.accent)

            def dinle():
                try:
                    yeni_tus = keyboard.read_hotkey(suppress=False)
                    def arayuzde_goster():
                        entry_widget.delete(0, tk.END)
                        entry_widget.insert(0, yeni_tus)
                        entry_widget.config(fg="white")
                        win.focus() 
                    win.after(0, arayuzde_goster)
                except Exception:
                    pass

            threading.Thread(target=dinle, daemon=True).start()

        for row, (etiket, anahtar, varsayilan) in enumerate(alanlar):
            tk.Label(frame, text=etiket, fg=self.text_primary, bg=self.bg_panel, font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", pady=6)

            e = tk.Entry(frame, bg=self.bg_main, fg="white", font=("Consolas", 10, "bold"), bd=1, relief="solid", width=12, justify="center")
            e.insert(0, varsayilan)
            e.grid(row=row, column=1, padx=(10, 5), pady=6)
            e.bind("<Button-1>", lambda event, widget=e: tus_dinle_ve_yaz(widget))
            self.inputs[anahtar] = e

        def kaydet():
            yeni_kisayollar = {k: v.get().strip().lower() for k, v in self.inputs.items()}
            
            # 1. Main.py'deki verileri güncelle
            self.kontrolcu.kisayollar = yeni_kisayollar
            if hasattr(self.kontrolcu, "ayarlar"):
                self.kontrolcu.ayarlar.kisayollar = yeni_kisayollar
                self.kontrolcu.ayarlar.kaydet()
            
            # 2. Main.py'ye tuşları yeniden atamasını söyle
            if hasattr(self.kontrolcu, "kisayollari_guncelle"):
                self.kontrolcu.kisayollari_guncelle()
            
            # 3. Arayüzü güncelle ve kapat
            self.durum_metnini_guncelle("Beklemede", "#F87171")
            messagebox.showinfo("Başarılı", "Kısayol tuşları başarıyla güncellendi!")
            win.destroy()

        tk.Button(win, text="💾 Kaydet", bg="#059669", fg="white", bd=0, width=18, font=("Segoe UI", 9, "bold"), activebackground="#10B981", command=kaydet).pack(pady=(15, 10), ipady=5)

    def ekran_secim_penceresi_ac(self):
        if self.secim_penceresi: self.secim_penceresi.destroy()
        self.secim_penceresi = tk.Toplevel(self.root)
        self.secim_penceresi.attributes("-fullscreen", True)
        self.secim_penceresi.attributes("-alpha", 0.3)
        self.secim_penceresi.attributes("-topmost", True)
        self.secim_penceresi.config(cursor="cross")
        
        self.canvas = tk.Canvas(self.secim_penceresi, bg="gray", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.canvas.bind("<ButtonPress-1>", self.secime_basla)
        self.canvas.bind("<B1-Motion>", self.secimi_ciz)
        self.canvas.bind("<ButtonRelease-1>", self.secimi_bitir)

    def secime_basla(self, event):
        self.baslangic_x, self.baslangic_y = event.x, event.y
        self.secim_dikdortgeni = self.canvas.create_rectangle(self.baslangic_x, self.baslangic_y, self.baslangic_x, self.baslangic_y, outline='#00FFAA', width=3, fill="black")

    def secimi_ciz(self, event):
        self.canvas.coords(self.secim_dikdortgeni, self.baslangic_x, self.baslangic_y, event.x, event.y)

    def secimi_bitir(self, event):
        sol = min(self.baslangic_x, event.x)
        ust = min(self.baslangic_y, event.y)
        sag = max(self.baslangic_x, event.x)
        alt = max(self.baslangic_y, event.y)
        
        genislik = sag - sol
        yukseklik = alt - ust
        
        if self.secim_penceresi:
            self.secim_penceresi.destroy()
            self.secim_penceresi = None
            
        if genislik > 10 and yukseklik > 10:
            alan = {"top": ust, "left": sol, "width": genislik, "height": yukseklik}
            self.kontrolcu.alan_secildi(alan)