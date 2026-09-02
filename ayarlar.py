import json
import os
import tkinter as tk
from tkinter import ttk


class Ayarlar:
    """
    Uygulamanın tüm kalıcı ayarlarını (kısayollar, saydamlık, diller,
    API anahtarı, oyun profilleri) yönetir.

    NOT: main.py bu sınıfı `from ayarlar import Ayarlar` şeklinde import
    eder; bu yüzden sınıf adı burada bilerek "Ayarlar" olarak tutulmuştur
    (önceki isim "AyarlarYoneticisi" main.py ile uyuşmuyordu).
    """

    def __init__(self, dosya_yolu="config.json"):
        self.dosya_yolu = dosya_yolu

        # Kısayollar: arayuz.py ve main.py'nin aradığı isimlerle birebir eşleşiyor
        self.kisayollar = {
            "alan_sec": "f8",
            "oto_cevir": "f9",
            "tek_cekim": "f10",
            "tam_ekran": "f11"
        }

        # Varsayılan Diğer Ayarlar
        self.saydamlik = 90
        self.hedef_dil = "Türkçe"          # OCR akışının hedef dili (üst panel)
        self.kaynak_dil = "Otomatik"       # Manuel çeviri kutusunun kaynak dili (alt panel)
        self.ocr_dili = "İngilizce"        # EasyOCR'ın okuyacağı dil
        # DÜZELTME: Eski varsayılan "Google Çeviri" idi; ancak arayuz.py'deki
        # Combobox seçenekleri "Yerel Yapay Zeka (İnternetsiz)", "Gemini AI (Akıllı)",
        # "Standart (Hızlı)" isimleriyle geliyor. Eşleşmeyen bir varsayılan değer,
        # arayüzde hiçbir zaman seçili görünmüyordu.
        self.motor_secimi = "Standart (Hızlı)"
        self.hedef_dil_alt = "İngilizce"   # Manuel çeviri kutusunun hedef dili (alt panel)

        # main.py'nin doğrudan kullandığı ama önceki sürümde eksik olan alanlar:
        self.api_key = ""          # CeviriMotoru(self.ayarlar.api_key) için
        self.profiller = {}        # Oyun profilleri (isim -> {"exe":..., "alan":...})

        # Başlangıçta kayıtlı ayarları yükle
        self.yukle()

    def yukle(self):
        """Ayarları config.json dosyasından okur, yoksa varsayılanları bırakır."""
        if os.path.exists(self.dosya_yolu):
            try:
                with open(self.dosya_yolu, "r", encoding="utf-8") as f:
                    kayitli_ayarlar = json.load(f)

                    # Sadece bilinen kısayol anahtarlarını birleştir (config.json'daki
                    # eski/artık kullanılmayan anahtarlarla kirlenmeyi önler)
                    if "kisayollar" in kayitli_ayarlar:
                        for anahtar in self.kisayollar.keys():
                            if anahtar in kayitli_ayarlar["kisayollar"]:
                                self.kisayollar[anahtar] = kayitli_ayarlar["kisayollar"][anahtar]

                    self.saydamlik = kayitli_ayarlar.get("saydamlik", self.saydamlik)
                    self.hedef_dil = kayitli_ayarlar.get("hedef_dil", self.hedef_dil)
                    self.kaynak_dil = kayitli_ayarlar.get("kaynak_dil", self.kaynak_dil)
                    self.ocr_dili = kayitli_ayarlar.get("ocr_dili", self.ocr_dili)
                    self.motor_secimi = kayitli_ayarlar.get("motor_secimi", self.motor_secimi)
                    self.hedef_dil_alt = kayitli_ayarlar.get("hedef_dil_alt", self.hedef_dil_alt)
                    self.api_key = kayitli_ayarlar.get("api_key", self.api_key)
                    self.profiller = kayitli_ayarlar.get("profiller", self.profiller)
            except Exception as e:
                print(f"[Ayarlar Yöneticisi Hatası]: Dosya okunamadı - {e}")

    def kaydet(self):
        """Mevcut ayarları config.json dosyasına yazar."""
        ayarlar_dict = {
            "api_key": self.api_key,
            "kisayollar": self.kisayollar,
            "saydamlik": self.saydamlik,
            "hedef_dil": self.hedef_dil,
            "kaynak_dil": self.kaynak_dil,
            "ocr_dili": self.ocr_dili,
            "motor_secimi": self.motor_secimi,
            "hedef_dil_alt": self.hedef_dil_alt,
            "profiller": self.profiller
        }
        try:
            with open(self.dosya_yolu, "w", encoding="utf-8") as f:
                json.dump(ayarlar_dict, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[Ayarlar Yöneticisi Hatası]: Dosya kaydedilemedi - {e}")


class SaydamlikAyari(tk.Frame):
    """
    Pencere saydamlığını canlı değiştiren slider bileşeni.

    NOT: Parametre isimleri arayuz.py'deki çağrıyla (ebeveyn_pencere=,
    ana_uygulama_penceresi=, ayarlar_nesnesi=) birebir eşleşecek şekilde
    ayarlanmıştır. Önceki sürümde isimler farklıydı (parent, ana_pencere,
    ayarlar_yoneticisi) ve bu bir TypeError'a sebep oluyordu.
    """

    def __init__(self, ebeveyn_pencere, ana_uygulama_penceresi, ayarlar_nesnesi, *args, **kwargs):
        kwargs["bg"] = "#2c2f33"
        super().__init__(ebeveyn_pencere, *args, **kwargs)

        self.ana_pencere = ana_uygulama_penceresi
        self.ayarlar = ayarlar_nesnesi

        baslangic_deger = self.ayarlar.saydamlik if self.ayarlar else 90
        self.saydamlik_var = tk.DoubleVar(value=baslangic_deger)

        # Etiket
        self.lbl_baslik = tk.Label(self, text="Pencere Saydamlığı:", bg="#2c2f33", fg="white", font=("Arial", 10))
        self.lbl_baslik.pack(side=tk.LEFT, padx=(0, 10))

        # Değer Gösterici Etiket
        self.lbl_deger = tk.Label(self, text=f"%{int(baslangic_deger)}", bg="#2c2f33", fg="#00e676", font=("Arial", 10, "bold"))
        self.lbl_deger.pack(side=tk.RIGHT, padx=(10, 0))

        # Slider
        self.slider = ttk.Scale(
            self,
            from_=20,
            to_=100,
            orient=tk.HORIZONTAL,
            variable=self.saydamlik_var,
            command=self._saydamligi_uygula
        )
        self.slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # PERFORMANS (LAG) ÇÖZÜMÜ: Diske yazma işlemini sadece mouse tuşu bırakıldığında yap!
        self.slider.bind("<ButtonRelease-1>", self._saydamligi_kaydet)

    def _saydamligi_uygula(self, deger):
        """Slider kaydırıldıkça pencere şeffaflığını anlık değiştirir ancak diske (JSON) yazmaz."""
        yuzde = float(deger)
        self.lbl_deger.config(text=f"%{int(yuzde)}")

        alfa_degeri = yuzde / 100.0
        self.ana_pencere.attributes("-alpha", alfa_degeri)

    def _saydamligi_kaydet(self, event=None):
        """Sadece fare tuşu bırakıldığında JSON dosyasına kayıt yapar."""
        if self.ayarlar:
            self.ayarlar.saydamlik = self.saydamlik_var.get()
            self.ayarlar.kaydet()
            print(f"[Ayarlar Yöneticisi]: Saydamlık %{int(self.ayarlar.saydamlik)} olarak diske kaydedildi.")