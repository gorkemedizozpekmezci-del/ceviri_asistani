# 🎮 Ekran Çeviri Asistanı

Masaüstünde (özellikle oyunlarda ve yabancı dilde uygulamalarda) ekrandaki seçili bir bölgeyi **OCR** ile okuyup **anlık çeviren**, isteğe bağlı olarak **sesli okuyan** açık kaynaklı bir Python/Tkinter aracı.

## ✨ Özellikler

- 🖼️ **Ekran OCR:** EasyOCR + OpenCV ile seçtiğin ekran bölgesindeki metni okur
- 🌐 **3 Katmanlı Çeviri Motoru:**
  - **Yerel (Çevrimiçi/İnternetsiz):** Meta'nın NLLB-200 modeli, tamamen offline çalışır
  - **Gemini AI:** Bağlama duyarlı, yüksek kaliteli çeviri (kendi Gemini API anahtarınla)
  - **Standart:** Google Translate tabanlı hızlı yedek motor
- 🔊 **Sesli Okuma (TTS)** ve mikrofon ile konuşma tanıma (STT)
- ⌨️ **Global Kısayollar:** F8-F11 ile alan seçme, oto-çeviri, tek seferlik okuma, tam ekran okuma
- 🎨 Koyu temalı, saydamlığı ayarlanabilir arayüz
- 💾 Tüm tercihler (dil, motor, kısayollar) otomatik kaydedilir

## 📦 Kurulum

```bash
git clone https://github.com/gorkemedizozpekmezci-del/ceviri_asistani.git
cd ceviri_asistani
pip install -r requirements.txt
python main.py
```

> **Not:** `pyaudio` bazı Windows sistemlerinde doğrudan `pip install` ile kurulamayabilir. Sorun yaşarsan:
> ```bash
> pip install pipwin
> pipwin install pyaudio
> ```

## 🔑 Gemini API Anahtarı (Opsiyonel)

Program **hiçbir API anahtarı içermez** — Gemini motorunu kullanmak istersen:

1. [Google AI Studio](https://aistudio.google.com/apikey) üzerinden ücretsiz bir Gemini API anahtarı al
2. Uygulamayı aç → ⚙️ Ayarlar → "Gemini API Anahtarı" alanına yapıştır → Kaydet

Anahtar girmezsen uygulama **Yerel (NLLB)** ve **Standart (Google Translate)** motorlarıyla sorunsuz çalışmaya devam eder.

## ⌨️ Kısayollar (varsayılan)

| Tuş | İşlev |
|-----|-------|
| `F8` | Ekranda çevrilecek alanı seç |
| `F9` | Otomatik/canlı çeviriyi başlat-durdur |
| `F10` | Seçili alanı tek seferlik oku ve çevir |
| `F11` | Tüm ekranı oku ve çevir |

Kısayollar, uygulama içindeki ayarlar penceresinden değiştirilebilir.

## ⚠️ Bilinmesi Gerekenler

- **NLLB-200 modeli** [CC-BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) lisansıyla (Meta AI) dağıtılmaktadır — yalnızca **kişisel/ticari olmayan** kullanım içindir.
- Bu araç ekran okuma ve global klavye kısayolları kullanır; bazı çok oyunculu oyunların **anti-cheat sistemleri** (EAC, BattlEye, VAC vb.) bu tür araçları şüpheli olarak işaretleyebilir. Riski bilerek kullan, çevrimiçi rekabetçi oyunlarda dikkatli ol.
- Google Translate entegrasyonu resmi ücretli API değil, kişisel kullanım ölçeğinde bir yedek motordur.

## 🛠️ Kullanılan Teknolojiler

Python · Tkinter · EasyOCR · OpenCV · PyTorch · Hugging Face Transformers (NLLB-200) · Google GenAI SDK (Gemini) · deep-translator · pyttsx3 · SpeechRecognition

## 📄 Lisans

Bu projenin kaynak kodu açık kaynaktır. Bağımlılıkların (özellikle NLLB-200) kendi lisans şartlarına dikkat ediniz.

---

Katkı, hata bildirimi ve öneriler için **Issues** sekmesini kullanabilirsiniz.