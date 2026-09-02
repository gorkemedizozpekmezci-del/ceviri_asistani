import easyocr
import mss
import cv2
import numpy as np
import torch
from langdetect import detect

class OcrMotoru:
    def __init__(self):
        # Ekran kartı (CUDA) varsa kullan, yoksa işlemciye (CPU) geç
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.reader = None
        self.sct = mss.mss()

    def ocr_yukle(self, dil_secimi):
        """Arayüzdeki seçime göre EasyOCR dil paketlerini yükler."""
        dil_haritasi = {
            "İngilizce": ['en'], 
            "Rusça": ['en', 'ru'], 
            "İspanyolca": ['en', 'es'], 
            "Çince": ['en', 'ch_sim']
        }
        kodlar = dil_haritasi.get(dil_secimi, ['en'])
        
        try:
            print(f"[OCR Motoru]: '{dil_secimi}' dilleri için EasyOCR yükleniyor ({self.device})...")
            self.reader = easyocr.Reader(kodlar, gpu=(self.device == "cuda"))
        except Exception as e:
            print(f"[OCR Yükleme Hatası]: EasyOCR başlatılamadı - {e}")
            self.reader = None

    def tam_ekran_alani_ver(self):
        """Birincil monitörün çözünürlük koordinatlarını döndürür."""
        try:
            monitor = self.sct.monitors[1]
            return {"top": monitor["top"], "left": monitor["left"], "width": monitor["width"], "height": monitor["height"]}
        except Exception as e:
            print(f"[OCR Ekran Hatası]: Monitör algılanamadı - {e}")
            return {"top": 0, "left": 0, "width": 1920, "height": 1080}

    def goruntu_al(self, alan):
        """Belirtilen koordinatlardan görüntüyü alır, gri tonlamaya çevirir ve
        OCR başarısını artırmak için ön işleme uygular."""
        try:
            img_array = np.array(self.sct.grab(alan))
            gray_img = cv2.cvtColor(img_array, cv2.COLOR_BGRA2GRAY)

            # DÜZELTME: Oyun içi diyalog kutuları genelde küçük/düşük çözünürlüklü
            # oluyor; EasyOCR küçük harfleri okuyamayıp boş sonuç döndürebiliyordu.
            # Küçük alanları büyüterek okunabilirliği artırıyoruz.
            yukseklik, genislik = gray_img.shape[:2]
            if yukseklik < 120 or genislik < 350:
                gray_img = cv2.resize(gray_img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)

            # DÜZELTME: Düşük kontrastlı (yarı saydam kutu, koyu zemin üzerine koyu
            # yazı vb.) metinlerde CLAHE ile yerel kontrastı artırıyoruz.
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray_img = clahe.apply(gray_img)

            return gray_img
        except Exception as e:
            print(f"[OCR Görüntü Hatası]: Ekran yakalanamadı - {e}")
            return None

    def hizli_oku(self, gray_img):
        """F9 (Oto) modu için dil tespiti yapmadan en hızlı okumayı gerçekleştirir."""
        if self.reader is None or gray_img is None: 
            return ""
            
        try:
            results = self.reader.readtext(gray_img)
            # Güvenilirlik oranı (prob) %30'un üzerinde olanları al
            return " ".join([text for (bbox, text, prob) in results if prob > 0.3]).strip()
        except Exception as e:
            print(f"[OCR Okuma Hatası]: {e}")
            return ""

    def filtreli_oku(self, gray_img, secilen_dil):
        """F10 modu için okunan metnin dilini langdetect ile doğrulayarak okur."""
        if self.reader is None or gray_img is None: 
            return ""
        
        dil_kodlari = {"İngilizce": "en", "Rusça": "ru", "İspanyolca": "es", "Çince": "zh-cn"}
        beklenen_kod = dil_kodlari.get(secilen_dil, "en")
        filtrelenmis_parcalar = []
        tum_gecerli_parcalar = []  # Dil filtresi hepsini eleyip "metin bulunamadı" derse diye yedek

        try:
            results = self.reader.readtext(gray_img)
            for (bbox, text, prob) in results:
                text = text.strip()
                if prob <= 0.3 or not text:
                    continue

                tum_gecerli_parcalar.append(text)

                # DÜZELTME: 3 karakter veya daha kısa metinlerde ("OK", "Go", "5" vb.)
                # langdetect güvenilir sonuç veremiyordu ve bu metinler öncesinde
                # sessizce siliniyordu. Artık kısa metinleri doğrudan kabul ediyoruz.
                if len(text) <= 3:
                    filtrelenmis_parcalar.append(text)
                    continue

                try:
                    tespit_edilen = detect(text)
                    if secilen_dil == "Çince" and tespit_edilen.startswith("zh"):
                        filtrelenmis_parcalar.append(text)
                    elif tespit_edilen == beklenen_kod:
                        filtrelenmis_parcalar.append(text)
                except Exception:
                    # DÜZELTME: langdetect hata verirse (örn. sadece sayı/sembol) metni
                    # tamamen atmak yerine koruyoruz; OCR zaten yeterli güvenle okumuştu.
                    filtrelenmis_parcalar.append(text)

            if filtrelenmis_parcalar:
                return " ".join(filtrelenmis_parcalar).strip()

            # DÜZELTME: Dil filtresi her şeyi elediyse (yanlış dil tespiti gibi),
            # kullanıcıya boş sonuç yerine en azından güvenilirliği yüksek ham
            # metni gösteriyoruz. main.py zaten çeviri motoruna kaynak dili ayrıca
            # iletiyor, dolayısıyla çeviri yine doğru motora gidebilir.
            return " ".join(tum_gecerli_parcalar).strip()
        except Exception as e:
            print(f"[OCR Filtre Hatası]: {e}")
            return ""