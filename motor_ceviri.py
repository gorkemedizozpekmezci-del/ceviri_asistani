import torch
import re
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from google import genai
from deep_translator import GoogleTranslator

try:
    from langdetect import detect as dil_tespit_et
except Exception:
    dil_tespit_et = None

class CeviriMotoru:
    def __init__(self, api_key=None):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.yerel_model_hazir = False
        self.client = None
        self.tokenizer = None
        self.local_model = None
        
        if api_key:
            try:
                self.client = genai.Client(api_key=api_key)
                print("[Çeviri Motoru]: Gemini API istemcisi başarıyla oluşturuldu.")
            except Exception as e:
                print(f"[Çeviri Motoru Uyarı]: Gemini API Hatası - {e}")

    def api_anahtarini_ayarla(self, api_key):
        """Kullanıcı ayarlar penceresinden yeni bir API anahtarı girdiğinde/sildiğinde
        Gemini istemcisini uygulamayı yeniden başlatmadan günceller. Boş anahtar
        gönderilirse Gemini devre dışı bırakılır; diğer motorlar (Yerel/Standart)
        etkilenmeden çalışmaya devam eder."""
        self.client = None
        api_key = (api_key or "").strip()
        if api_key:
            try:
                self.client = genai.Client(api_key=api_key)
                print("[Çeviri Motoru]: Gemini API istemcisi (yeni anahtarla) oluşturuldu.")
            except Exception as e:
                print(f"[Çeviri Motoru Uyarı]: Gemini API Hatası - {e}")

    def yerel_modeli_yukle(self):
        """NLLB-200 modelini yerel (çevrimdışı) kullanım için GPU/CPU belleğine yükler."""
        try:
            model_adi = "facebook/nllb-200-distilled-600M"
            print(f"[Çeviri Motoru]: Yerel model ({model_adi}) yükleniyor, lütfen bekleyin...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_adi)
            self.local_model = AutoModelForSeq2SeqLM.from_pretrained(model_adi).to(self.device)
            self.yerel_model_hazir = True
            print(f"[Çeviri Motoru]: Yerel Yapay Zeka modeli [{self.device.upper()}] üzerinde başarıyla yüklendi.")
        except Exception as e:
            print(f"[Çeviri Motoru Hata]: Yerel Model Yükleme Hatası - {e}")
            self.yerel_model_hazir = False

    def _gecerli_ceviri_mi(self, metin):
        """Google'ın çeviri yerine döndürdüğü HTML/Sunucu hatalarını filtreler."""
        if not metin:
            return False
        # Eğer gelen "çeviride" bu kelimeler varsa, bu gerçek bir çeviri değil Google hatasıdır!
        hatali_kaliplar = ["Error 500", "500.That’s an error", "Server Error", "<html>", "429 Too Many Requests", "Please try again later"]
        for kalip in hatali_kaliplar:
            if kalip.lower() in str(metin).lower():
                return False
        return True

    def cevir(self, metin, motor_secimi, hedef_gorunen, kaynak_dil="auto"):
        """Gelen metni seçilen motora (Yerel, Gemini, Google) göre çevirir ve hatalarda yedeğe geçer."""
        
        # --- AJAN KODUMUZ BURADA ---
        print(f"\n--- ÇEVİRİ SİSTEMİNE GELEN VERİ ---")
        print(f"Gelen Metin  : '{metin}'")
        print(f"Motor Seçimi : '{motor_secimi}' | Hedef: '{hedef_gorunen}' | Kaynak: '{kaynak_dil}'")
        print(f"-----------------------------------\n")

        metin = str(metin).strip()
        if not metin:
            return ""

        # Dil Kodları Haritalandırması
        google_kodlari = {
            "Türkçe": "tr", "İngilizce": "en", "İspanyolca": "es", "Almanca": "de",
            "Fransızca": "fr", "Rusça": "ru", "Çince": "zh-CN", "Japonca": "ja",
            "Korece": "ko", "Arapça": "ar", "İtalyanca": "it", "Portekizce": "pt", "Otomatik": "auto",
            "tr": "tr", "en": "en", "es": "es", "de": "de", "fr": "fr",
            "ru": "ru", "zh-CN": "zh-CN", "zh": "zh-CN", "ja": "ja", "ko": "ko", "ar": "ar", "it": "it", "pt": "pt", "auto": "auto"
        }

        nllb_kodlari = {
            "Türkçe": "tur_Latn", "İngilizce": "eng_Latn", "İspanyolca": "spa_Latn",
            "Almanca": "deu_Latn", "Fransızca": "fra_Latn", "Rusça": "rus_Cyrl",
            "Çince": "zho_Hans", "Japonca": "jpn_Jpan", "Korece": "kor_Hang",
            "Arapça": "arb_Arab", "İtalyanca": "ita_Latn", "Portekizce": "por_Latn", "Otomatik": "tur_Latn",
            "tr": "tur_Latn", "en": "eng_Latn", "es": "spa_Latn", "de": "deu_Latn",
            "fr": "fra_Latn", "ru": "rus_Cyrl", "zh": "zho_Hans", "zh-CN": "zho_Hans",
            "ja": "jpn_Jpan", "ko": "kor_Hang", "ar": "arb_Arab", "it": "ita_Latn", "pt": "por_Latn", "auto": "eng_Latn"
        }

        hedef_str = str(hedef_gorunen).strip()
        kaynak_str = str(kaynak_dil).strip()

        hedef_google = google_kodlari.get(hedef_str, "tr")
        kaynak_google = google_kodlari.get(kaynak_str, "auto")

        nllb_hedef = nllb_kodlari.get(hedef_str, "tur_Latn")
        nllb_kaynak = nllb_kodlari.get(kaynak_str, "eng_Latn")

        # 1. SEÇENEK: Yerel AI (NLLB - Çevrimdışı)
        if "Yerel" in str(motor_secimi) and self.yerel_model_hazir:
            try:
                # DÜZELTME: Kaynak dil "Otomatik" ise NLLB'ye sabit "İngilizce" varsaymak yerine
                # metnin gerçek dilini tespit ediyoruz. Aksi halde örn. Türkçe metin yanlışlıkla
                # İngilizceymiş gibi işlenip anlamsız/boş bir "çeviri" üretiyordu.
                gercek_nllb_kaynak = nllb_kaynak
                if kaynak_str in ("Otomatik", "auto", "") and dil_tespit_et:
                    try:
                        tespit_kodu = dil_tespit_et(metin)
                        if tespit_kodu.startswith("zh"):
                            tespit_kodu = "zh-CN"
                        gercek_nllb_kaynak = nllb_kodlari.get(tespit_kodu, nllb_kaynak)
                    except Exception:
                        pass

                self.tokenizer.src_lang = gercek_nllb_kaynak
                inputs = self.tokenizer(metin, return_tensors="pt").to(self.device)

                # DÜZELTME: convert_tokens_to_ids bazı transformers sürümlerinde dil kodunu
                # bulamayıp <unk> döndürebiliyor; bu durumda çeviri sessizce bozuk çıkıyordu.
                # Eski API (lang_code_to_id) ile yedekli çözüm ekledik ve hâlâ bulunamazsa
                # hatayı fırlatıp bir sonraki motora (Gemini/Google) düşülmesini sağlıyoruz.
                target_lang_id = self.tokenizer.convert_tokens_to_ids(nllb_hedef)
                if target_lang_id == self.tokenizer.unk_token_id:
                    eski_harita = getattr(self.tokenizer, "lang_code_to_id", None)
                    if eski_harita and nllb_hedef in eski_harita:
                        target_lang_id = eski_harita[nllb_hedef]
                    else:
                        raise ValueError(f"NLLB hedef dil kodu '{nllb_hedef}' tokenizer içinde bulunamadı.")

                # DÜZELTME: Sabit max_new_tokens=100, uzun diyalog metinlerini yarıda kesiyordu.
                # Kelime sayısına göre dinamik bir üst sınır belirliyoruz.
                tahmini_token_siniri = min(512, max(80, len(metin.split()) * 4))

                # PRO EKLENTİ: torch.no_grad() bellek tasarrufu ve hız
                with torch.no_grad():
                    translated_tokens = self.local_model.generate(
                        **inputs,
                        forced_bos_token_id=target_lang_id,
                        max_new_tokens=tahmini_token_siniri,
                        repetition_penalty=1.4,
                        num_beams=2,
                        early_stopping=True
                    )
                
                sonuc = self.tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]
                sonuc = re.sub(r'\s+([,.!?])', r'\1', sonuc)
                return sonuc.strip()
            except Exception as e:
                print(f"[Yerel Model Hatası]: {e} -> Standart çeviriye geçiliyor...")

        # 2. SEÇENEK: Cloud AI (Gemini 2.5 Pro)
        elif "Gemini" in str(motor_secimi) and self.client:
            try:
                # Düzeltme: Gemini'ye 'tr' yerine doğrudan 'Türkçe' vb. tam adını gönderiyoruz.
                prompt = f"Şu metni {hedef_str} diline çevir. Sadece çeviriyi ver, başka hiçbir kelime ekleme: {metin}"
                response = self.client.models.generate_content(model='gemini-2.5-pro', contents=prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[Gemini Hatası]: {e} -> Standart çeviriye geçiliyor...")

        # 3. SEÇENEK: Standart / Fallback (Google Translator)
        try:
            ceviri = GoogleTranslator(source=kaynak_google, target=hedef_google).translate(metin)
            # Filtre: Eğer sonuç bir Google HTML hatasıysa, bunu çeviri sayma!
            if self._gecerli_ceviri_mi(ceviri):
                return ceviri
        except Exception:
            pass

        # DÜZELTME: kaynak_google zaten "auto" ise, aşağıdaki deneme yukarıdakiyle
        # birebir aynı isteği tekrar atıp gereksiz gecikme yaratıyordu ve hiçbir şeyi
        # düzeltmiyordu. Sadece belirli bir kaynak dil seçiliyken ve o dil kodu
        # hatalıysa "auto" ile tekrar denemek mantıklı.
        if kaynak_google != "auto":
            try:
                ceviri_yedek = GoogleTranslator(source='auto', target=hedef_google).translate(metin)
                if self._gecerli_ceviri_mi(ceviri_yedek):
                    return ceviri_yedek
            except Exception as e:
                print(f"[Standart Çeviri Hatası]: {e}")
            
        # Eğer Google inatla kilitli kalırsa veya hata döndürürse; çirkin yazıyı değil, orijinal oyun metnini ekrana yazdır.
        return metin