import threading
import time
import wave
import io
import pyaudio
import speech_recognition as sr
import pyttsx3

class SesMotoru:
    def __init__(self):
        # --- KONUŞMA TANIMA (STT) AYARLARI ---
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300  # Hassasiyet eşiği (Düşük sesleri de duyar)
        self.recognizer.dynamic_energy_threshold = True
        
        self.kayit_ediliyor = False
        self.frames = []
        self.audio_thread = None
        
        # PyAudio Ses Formatı Ayarları
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1024

        # --- SESLİ OKUMA (TTS) AYARLARI ---
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150) # Konuşma hızı
        except Exception as e:
            print(f"[TTS Başlatma Hatası]: {e}")
            self.tts_engine = None

    # --- YENİ EKLENEN: MANUEL KAYIT (Tıkla-Konuş) ---
    def kayit_baslat(self):
        """Kullanıcı butona bastığında kaydı başlatır."""
        self.kayit_ediliyor = True
        self.frames = []
        self.audio_thread = threading.Thread(target=self._kayit_dongusu, daemon=True)
        self.audio_thread.start()

    def _kayit_dongusu(self):
        """Arka planda mikrofonu sen durdurana kadar kesintisiz dinler."""
        p = pyaudio.PyAudio()
        try:
            stream = p.open(format=self.FORMAT, channels=self.CHANNELS,
                           rate=self.RATE, input=True,
                           frames_per_buffer=self.CHUNK)
            while self.kayit_ediliyor:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                self.frames.append(data)
            stream.stop_stream()
            stream.close()
        except Exception as e:
            print(f"[Ses Kayıt Hatası]: {e}")
        finally:
            p.terminate()

    def kayit_durdur_ve_oku(self, dil="tr"):
        """Kullanıcı tekrar butona bastığında kaydı durdurur ve metne çevirir."""
        self.kayit_ediliyor = False
        if self.audio_thread:
            self.audio_thread.join(timeout=2)
        
        if not self.frames:
            return ""
        
        # Ham ses verisini bellekte WAV formatına dönüştür
        wav_buffer = io.BytesIO()
        wf = wave.open(wav_buffer, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        
        wav_buffer.seek(0)
        
        # Yapay Zeka Ses Tanıma
        try:
            with sr.AudioFile(wav_buffer) as source:
                audio = self.recognizer.record(source)
            
            dil_kodu = "tr-TR" if dil in ["tr", "auto"] else ("en-US" if dil == "en" else dil)
            metin = self.recognizer.recognize_google(audio, language=dil_kodu)
            return metin
        except sr.UnknownValueError:
            print("[Ses Motoru Bilgi]: Ses anlaşılamadı.")
            return ""
        except Exception as e:
            print(f"[Ses Motoru Hatası]: {e}")
            return ""

    # --- EKRANDAKİ ÇEVİRİYİ SESLİ OKUMA ---
    def oku(self, metin, dil="tr"):
        """Verilen metni sesli olarak okur, paket yoksa uyarı fırlatır."""
        if not self.tts_engine or not metin:
            return
            
        try:
            voices = self.tts_engine.getProperty('voices')
            ses_bulundu = False
            
            # Doğru dili bulmak için dinamik arama yapıyoruz
            for voice in voices:
                v_name = voice.name.lower()
                v_id = voice.id.lower()
                
                # Türkçe için özel kontrol
                if dil == "tr" and ("turkish" in v_name or "tolga" in v_name or "tr" in v_id):
                    self.tts_engine.setProperty('voice', voice.id)
                    ses_bulundu = True
                    break
                # İngilizce için özel kontrol
                elif dil == "en" and ("english" in v_name or "zira" in v_name or "david" in v_name or "en" in v_id):
                    self.tts_engine.setProperty('voice', voice.id)
                    ses_bulundu = True
                    break
                # Diğer diller (es, de, fr vb.)
                elif dil != "tr" and dil != "en" and (f"{dil}-" in v_id or f" {dil} " in v_id or dil in v_name):
                    self.tts_engine.setProperty('voice', voice.id)
                    ses_bulundu = True
                    break
                    
            # EĞER SES PAKETİ YÜKLÜ DEĞİLSE UYARI FIRLAT:
            if not ses_bulundu:
                hata_mesaji = f"'{dil}' dili için Windows ses paketi eksik. Lütfen ayarlardan yükleyin."
                raise Exception(hata_mesaji) 
                
            self.tts_engine.say(metin)
            self.tts_engine.runAndWait()
            
        except Exception as e:
            # Main.py'nin bu hatayı yakalayıp ekrana basması için fırlat
            raise Exception(str(e))