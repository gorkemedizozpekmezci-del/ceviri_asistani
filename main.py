import threading
import time
import ctypes
import difflib
import sys
import psutil
import keyboard
import tkinter as tk
from tkinter import ttk
import cv2
import numpy as np
import mss

# --- KENDİ YAZDIĞIMIZ MODÜLLER ---
from ayarlar import Ayarlar
from motor_ceviri import CeviriMotoru
from motor_ocr import OcrMotoru
from ses_motoru import SesMotoru
from arayuz import Arayuz

# Windows'ta bulanık görünümü (DPI scaling) ve koordinat kaymalarını engeller
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per-Monitor DPI Aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

class OyunAsistaniPro:
    # Global Ortak Dil Kod Haritası
    DIL_KODLARI = {
        "Otomatik": "auto", "Türkçe": "tr", "İngilizce": "en", "İspanyolca": "es",
        "Almanca": "de", "Fransızca": "fr", "Rusça": "ru", "Çince": "zh-CN",
        "Japonca": "ja", "Korece": "ko", "Arapça": "ar", "İtalyanca": "it", "Portekizce": "pt"
    }

    def __init__(self):
        # 1. Modülleri Başlat
        self.ayarlar = Ayarlar()
        self.ceviri_motoru = CeviriMotoru(self.ayarlar.api_key)
        self.ocr_motoru = OcrMotoru()
        self.ses_motoru = SesMotoru()
        
        # Kısayol Tuşlarını Ayarlardan Çek veya Varsayılanları Ata
        self.kisayollar = getattr(self.ayarlar, "kisayollar", {
            "alan_sec": "f8",
            "oto_cevir": "f9",
            "tek_cekim": "f10",
            "tam_ekran": "f11"
        })
        
        # 2. Değişkenleri Ayarla
        self.calisiyor = False
        self.uygulama_acik = True
        self.okuma_alani = {"top": 200, "left": 200, "width": 600, "height": 400} 
        self.aktif_oyun = "Manuel Seçim"

        # 3. Arayüzü Başlat
        self.arayuz = Arayuz(self)
        self.arayuz.metin_guncelle("Sistem yükleniyor, lütfen bekleyin... (Yapay Zeka başlatılıyor)")
        
        # 4. Arka Plan İşlemlerini Başlat (Arayüzü dondurmamak için)
        threading.Thread(target=self.modelleri_yukle, daemon=True).start()
        threading.Thread(target=self.klavye_dinle, daemon=True).start()
        threading.Thread(target=self.oyun_dedektifi, daemon=True).start()
        
        # Ana Döngüyü Başlat
        self.arayuz.root.mainloop()

    def dil_kodu_al(self, dil_adi, varsayilan="tr"):
        """Arayüzdeki dil isimlerini ISO koduna (tr, en, es) dönüştürür."""
        return self.DIL_KODLARI.get(dil_adi, varsayilan)

    # --- KISAYOL VE AYAR FONKSİYONLARI ---
    def kisayollari_guncelle(self):
        """Mevcut tuş dinlemelerini iptal edip yeni tuşları güvenli şekilde kaydeder."""
        try:
            keyboard.unhook_all()
        except Exception:
            pass

        islem_haritasi = {
            "alan_sec": self.alan_secimini_tetikle,
            "oto_cevir": self.durumu_degistir,
            "tek_cekim": self.tek_cekim_yap,
            "tam_ekran": self.tam_ekran_cekim_yap
        }

        for anahtar, fank in islem_haritasi.items():
            tus = self.kisayollar.get(anahtar, "").strip().lower()
            if tus:
                try:
                    keyboard.add_hotkey(tus, fank)
                except Exception as e:
                    print(f"[Kısayol Hatası]: '{tus}' tuşu atanamadı - {e}")

    # NOT: Kısayol ayarları penceresi artık arayuz.py -> Arayuz.kisayol_ayarlarini_ac()
    # içinde tanımlı ve yönetiliyor (canlı tuş dinleme özelliğiyle). Burada
    # kullanılmayan/ulaşılamayan eski bir kopyası olduğu için kaldırıldı.

    # --- SES YARDIMCI FONKSİYONLARI ---
    def sesle_oku(self, metin, dil="tr"):
        """Arayüzde sesli okuma açıksa metni seslendirir."""
        if hasattr(self.arayuz, "sesli_okuma_var") and self.arayuz.sesli_okuma_var.get() and metin:
            def oku_islem():
                try:
                    if hasattr(self.ses_motoru, "oku"):
                        try:
                            self.ses_motoru.oku(metin, dil=dil)
                        except TypeError:
                            self.ses_motoru.oku(metin)
                    elif hasattr(self.ses_motoru, "seslendir"):
                        try:
                            self.ses_motoru.seslendir(metin, dil=dil)
                        except TypeError:
                            self.ses_motoru.seslendir(metin)
                    elif hasattr(self.ses_motoru, "konus"):
                        self.ses_motoru.konus(metin)
                except Exception as e:
                    print(f"[Ses Okuma Uyarı]: {e}")
                    hata_metni = str(e)
                    self.arayuz.root.after(0, lambda: self.arayuz.metin_guncelle(f"⚠️ DİKKAT: {hata_metni}"))
                    
            threading.Thread(target=oku_islem, daemon=True).start()

    def mikrofon_dinle_ve_cevir(self):
        if not getattr(self.ses_motoru, "kayit_ediliyor", False):
            self.ses_motoru.kayit_baslat()
            if hasattr(self.arayuz, "btn_mikrofon"):
                self.arayuz.btn_mikrofon.config(text="🔴 Durdur & Çevir", bg="#EF4444", activebackground="#DC2626")
            self.arayuz.cevap_kutusu_mesaj("🎙️ Dinleniyor... Konuşmanız bitince 'Durdur' butonuna basın.")
        else:
            if hasattr(self.arayuz, "btn_mikrofon"):
                self.arayuz.btn_mikrofon.config(text="⏳ İşleniyor...", bg="#334155")
            self.arayuz.cevap_kutusu_mesaj("⏳ Ses çözümleniyor ve çevriliyor...")
            
            def islem():
                kaynak_secim = self.arayuz.kaynak_dil_alt.get()
                hedef_secim = self.arayuz.hedef_dil_alt.get()
                motor_secim = self.arayuz.motor_secimi.get()

                kaynak_kod = self.dil_kodu_al(kaynak_secim, "auto")
                hedef_kod = self.dil_kodu_al(hedef_secim, "tr")
                ses_dili = "tr" if kaynak_kod in ["auto", "tr"] else kaynak_kod
                
                metin = ""
                if hasattr(self.ses_motoru, "kayit_durdur_ve_oku"):
                    metin = self.ses_motoru.kayit_durdur_ve_oku(dil=ses_dili)
                
                if metin and metin.strip():
                    ceviri_sonucu = self.ceviri_motoru.cevir(metin, motor_secim, hedef_secim, kaynak_dil=kaynak_kod)
                    
                    def arayuz_guncelle():
                        self.arayuz.root.clipboard_clear()
                        self.arayuz.root.clipboard_append(ceviri_sonucu)
                        self.arayuz.cevap_kutusu.delete(0, tk.END)
                        self.arayuz.cevap_kutusu.insert(0, f"[KOPYALANDI] {ceviri_sonucu}")
                        self.arayuz.cevap_kutusu.select_range(0, tk.END)
                        self.sesle_oku(ceviri_sonucu, dil=hedef_kod)
                        if hasattr(self.arayuz, "btn_mikrofon"):
                            self.arayuz.btn_mikrofon.config(text="🎙️ Konuş", bg="#059669", activebackground="#10B981")
                    
                    self.arayuz.root.after(0, arayuz_guncelle)
                else:
                    def hata_guncelle():
                        self.arayuz.cevap_kutusu_mesaj("⚠️ Ses anlaşılamadı. Lütfen tekrar deneyin.")
                        if hasattr(self.arayuz, "btn_mikrofon"):
                            self.arayuz.btn_mikrofon.config(text="🎙️ Konuş", bg="#059669", activebackground="#10B981")
                    self.arayuz.root.after(0, hata_guncelle)

            threading.Thread(target=islem, daemon=True).start()

    # --- ANA İŞLEMLER VE AKIŞ ---
    def modelleri_yukle(self):
        donanim_bilgisi = "RTX (CUDA)" if getattr(self.ocr_motoru, "device", "cpu") == "cuda" else "İşlemci (CPU)"
        self.ceviri_motoru.yerel_modeli_yukle()
        self.ocr_motoru.ocr_yukle(self.arayuz.ocr_dili_secimi.get())
        
        hazir_mesaji = f"✅ Sistem Hazır! [Motor: {donanim_bilgisi}]\n{self.kisayollar['alan_sec'].upper()} ile alan seçebilir veya 'Profil Kaydet' ile kalıcı yapabilirsiniz."
        self.arayuz.root.after(0, self.arayuz.metin_guncelle, hazir_mesaji)

    def api_anahtarini_guncelle(self, yeni_key):
        """Kullanıcı ayarlar penceresinden kendi Gemini API anahtarını girdiğinde/sildiğinde
        çağrılır. Anahtarı diske kaydeder ve uygulamayı yeniden başlatmaya gerek kalmadan
        çeviri motorundaki Gemini istemcisini günceller."""
        yeni_key = (yeni_key or "").strip()
        self.ayarlar.api_key = yeni_key
        self.ayarlar.kaydet()
        self.ceviri_motoru.api_anahtarini_ayarla(yeni_key)

        if yeni_key:
            self.arayuz.metin_guncelle("✅ Gemini API anahtarı kaydedildi ve etkinleştirildi.")
        else:
            self.arayuz.metin_guncelle("ℹ️ API anahtarı temizlendi. Gemini olmadan (Yerel/Standart motorla) devam edilecek.")

    def ocr_dilini_guncelle(self, event=None):
        secim = self.arayuz.ocr_dili_secimi.get()
        self.arayuz.metin_guncelle(f"⏳ OCR Gözü '{secim}' için ayarlanıyor...")

        # DÜZELTME: Seçilen OCR dili önceden hiç diske kaydedilmiyordu; uygulama her
        # yeniden başlatıldığında sabit "İngilizce"ye dönüyordu.
        self.ayarlar.ocr_dili = secim
        self.ayarlar.kaydet()

        def guncelle():
            self.ocr_motoru.ocr_yukle(secim)
            self.arayuz.root.after(0, self.arayuz.metin_guncelle, f"✅ Oyun dili başarıyla {secim} olarak ayarlandı.")
        threading.Thread(target=guncelle, daemon=True).start()

    def profili_kaydet(self):
        if self.okuma_alani and self.aktif_oyun == "Manuel Seçim":
            isim = self.arayuz.isim_sor("Profil Kaydet", "Bu ekran alanını kaydetmek için oyuna bir isim verin:\n(Örn: GTA V)")
            if isim and isim.strip():
                isim = isim.strip()
                self.ayarlar.profiller[isim] = {"exe": "", "alan": self.okuma_alani}
                self.arayuz.profil_secimi['values'] = list(self.ayarlar.profiller.keys())
                self.arayuz.profil_secimi.set(isim)
                self.aktif_oyun = isim
                self.ayarlar.kaydet()
                self.arayuz.metin_guncelle(f"💾 '{isim}' profili başarıyla kaydedildi!")
        else:
            self.arayuz.uyari_goster("Bilgi", f"Lütfen önce {self.kisayollar['alan_sec'].upper()} ile bir alan seçin, ardından kaydet butonuna basın.")

    def profil_degistir(self, event=None):
        secilen = self.arayuz.profil_secimi.get()
        self.aktif_oyun = secilen
        
        profil_detay = self.ayarlar.profiller.get(secilen)
        if profil_detay and profil_detay.get("alan") is not None:
            self.okuma_alani = profil_detay["alan"]
            self.arayuz.metin_guncelle(f"// {secilen.upper()} PROFİLİ AKTİF //\nKoordinatlar sabitlendi.")
        else:
            self.arayuz.metin_guncelle(f"// MANUEL MOD //\nLütfen {self.kisayollar['alan_sec'].upper()} ile çevrilmesini istediğiniz alanı seçin.")

    def alan_secildi(self, alan):
        self.okuma_alani = alan
        self.arayuz.profil_secimi.set("Manuel Seçim")
        self.arayuz.metin_guncelle(f"// ALAN KİLİTLENDİ //\nİstersen '[+] Kaydet' butonuna basarak bu alanı kaydedebilirsin.\nSürekli çeviri: {self.kisayollar['oto_cevir'].upper()} | Alan Çekim: {self.kisayollar['tek_cekim'].upper()}")

    def tamamen_kapat(self):
        self.uygulama_acik = False
        self.calisiyor = False
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        try:
            self.arayuz.root.quit()
        except Exception:
            pass
        sys.exit()

    def klavye_dinle(self):
        self.kisayollari_guncelle()
        while self.uygulama_acik:
            time.sleep(0.2)

    def durumu_degistir(self):
        self.calisiyor = not self.calisiyor
        if self.calisiyor:
            self.arayuz.durum_guncelle("🟢 OTOMATİK TARAMA AÇIK", "#00FFAA")
            threading.Thread(target=self.ekrani_oku_ve_cevir, daemon=True).start()
        else:
            self.arayuz.durum_guncelle(f"🔴 BEKLEMEDE ({self.kisayollar['alan_sec'].upper()}: Alan Seç | {self.kisayollar['oto_cevir'].upper()}: Oto | {self.kisayollar['tek_cekim'].upper()}: Alan)", "#FF4444")

    def tek_cekim_yap(self):
        if self.calisiyor: self.durumu_degistir()
        self.arayuz.durum_guncelle("📸 ALAN ÇEKİLİYOR...", "#FFAA00")
        threading.Thread(target=self.tek_seferlik_okuma, args=(self.okuma_alani,), daemon=True).start()

    def tam_ekran_cekim_yap(self):
        if self.calisiyor: self.durumu_degistir()
        self.arayuz.durum_guncelle("🖥️ TAM EKRAN ÇEKİLİYOR...", "#00AAFF")
        tam_ekran_alani = self.ocr_motoru.tam_ekran_alani_ver()
        threading.Thread(target=self.tek_seferlik_okuma, args=(tam_ekran_alani,), daemon=True).start()

    def alan_secimini_tetikle(self):
        if self.calisiyor: self.durumu_degistir() 
        self.arayuz.root.after(0, self.arayuz.ekran_secim_penceresi_ac)

    def oyun_dedektifi(self):
        while self.uygulama_acik:
            if self.aktif_oyun == "Manuel Seçim":
                try:
                    calisan_islemler = set()
                    for proc in psutil.process_iter(['name']):
                        try:
                            calisan_islemler.add(proc.info['name'])
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            pass

                    for oyun_adi, detaylar in self.ayarlar.profiller.items():
                        exe_adi = detaylar.get("exe", "")
                        if exe_adi and exe_adi in calisan_islemler:
                            self.aktif_oyun = oyun_adi
                            self.arayuz.root.after(0, self.arayuz.profil_secimi.set, oyun_adi)
                            self.arayuz.root.after(0, self.profil_degistir, None)
                            self.arayuz.root.after(0, self.arayuz.metin_guncelle, f"🎮 {oyun_adi} algılandı! Diyalog alanı kilitlendi.")
                            break
                except Exception:
                    pass
            time.sleep(5)

    def tek_seferlik_okuma(self, alan):
        secilen_dil = self.arayuz.ocr_dili_secimi.get()
        try:
            gray_img = self.ocr_motoru.goruntu_al(alan)
            okunan_metin = self.ocr_motoru.filtreli_oku(gray_img, secilen_dil)

            if okunan_metin and okunan_metin.strip():
                motor = self.arayuz.motor_secimi.get()
                hedef_dil_adi = self.arayuz.hedef_dil.get()
                
                kaynak_kod = self.dil_kodu_al(secilen_dil, "auto")
                hedef_kod = self.dil_kodu_al(hedef_dil_adi, "tr")
                
                # Hedef dil adını ("Türkçe") göndererek Gemini ve Google haritasını en ideal hale getiriyoruz
                turkce_ceviri = self.ceviri_motoru.cevir(okunan_metin, motor, hedef_dil_adi, kaynak_dil=kaynak_kod)
                
                etiket = "[TAM EKRAN]" if alan.get("width", 0) > 1000 else "[ALAN]"
                self.arayuz.root.after(0, self.arayuz.metin_guncelle, f"{etiket} > {turkce_ceviri}")
                
                self.sesle_oku(turkce_ceviri, dil=hedef_kod)
            else:
                self.arayuz.root.after(0, self.arayuz.metin_guncelle, f"Seçili alanda uygun bir {secilen_dil} metin bulunamadı.")
        except Exception as e:
            print(f"[Tek Seferlik Okuma Hatası]: {e}")
            self.arayuz.root.after(0, self.arayuz.metin_guncelle, f"⚠️ Okuma/Çeviri hatası oluştu: {e}")
        finally:
            self.arayuz.root.after(0, lambda: self.arayuz.durum_guncelle(f"🔴 BEKLEMEDE ({self.kisayollar['alan_sec'].upper()}: Alan Seç | {self.kisayollar['oto_cevir'].upper()}: Oto | {self.kisayollar['tek_cekim'].upper()}: Alan)", "#FF4444"))

    def ekrani_oku_ve_cevir(self):
        son_okunan_metin = "" 
        
        while self.calisiyor and self.uygulama_acik:
            try:
                gray_img = self.ocr_motoru.goruntu_al(self.okuma_alani)
                okunan_metin = self.ocr_motoru.hizli_oku(gray_img)
                okunan_metin = okunan_metin.strip() if okunan_metin else ""
                
                if okunan_metin and difflib.SequenceMatcher(None, okunan_metin, son_okunan_metin).ratio() < 0.85:
                    son_okunan_metin = okunan_metin 
                    
                    secilen_dil = self.arayuz.ocr_dili_secimi.get()
                    motor = self.arayuz.motor_secimi.get()
                    hedef_dil_adi = self.arayuz.hedef_dil.get()
                    
                    kaynak_kod = self.dil_kodu_al(secilen_dil, "auto")
                    hedef_kod = self.dil_kodu_al(hedef_dil_adi, "tr")
                    
                    turkce_ceviri = self.ceviri_motoru.cevir(okunan_metin, motor, hedef_dil_adi, kaynak_dil=kaynak_kod)
                    
                    self.arayuz.root.after(0, self.arayuz.metin_guncelle, f"> {turkce_ceviri}")
                    self.sesle_oku(turkce_ceviri, dil=hedef_kod)
            
            except Exception as e:
                print(f"[Ekran Oku/Çevir Hatası]: {e}")
            
            time.sleep(1)

    def cevabi_cevir(self, event=None):
        metin = self.arayuz.cevap_kutusu.get().strip()
        placeholder = "Yaz/Yapıştır ve ENTER'a bas..."
        
        if not metin or metin == placeholder: 
            return
        
        kaynak_secim = self.arayuz.kaynak_dil_alt.get()
        hedef_secim = self.arayuz.hedef_dil_alt.get()
        motor_secim = self.arayuz.motor_secimi.get() 
        
        kaynak_kod = self.dil_kodu_al(kaynak_secim, "auto")
        hedef_kod = self.dil_kodu_al(hedef_secim, "tr")
        
        self.arayuz.cevap_kutusu.delete(0, tk.END)
        self.arayuz.cevap_kutusu.insert(0, f"Yapay Zeka ({hedef_secim}) Çeviriyor...")
        self.arayuz.root.update()
        
        def cevir_ve_kopyala():
            try:
                ceviri_sonucu = self.ceviri_motoru.cevir(metin, motor_secim, hedef_secim, kaynak_dil=kaynak_kod)
                
                def arayuzu_ve_panoyu_guncelle():
                    self.arayuz.root.clipboard_clear()
                    self.arayuz.root.clipboard_append(ceviri_sonucu)
                    
                    self.arayuz.cevap_kutusu.delete(0, tk.END)
                    self.arayuz.cevap_kutusu.insert(0, f"[KOPYALANDI] {ceviri_sonucu}")
                    self.arayuz.cevap_kutusu.select_range(0, tk.END)
                    
                    self.sesle_oku(ceviri_sonucu, dil=hedef_kod)
                
                self.arayuz.root.after(0, arayuzu_ve_panoyu_guncelle)
            except Exception as e:
                self.arayuz.root.after(0, lambda: (self.arayuz.cevap_kutusu.delete(0, tk.END), self.arayuz.cevap_kutusu.insert(0, f"HATA: {str(e)[:40]}")))
                
        threading.Thread(target=cevir_ve_kopyala, daemon=True).start()

if __name__ == "__main__":
    OyunAsistaniPro()