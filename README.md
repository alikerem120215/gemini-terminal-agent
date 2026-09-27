# ⚡ Gemini Terminal Agent — Web Tabanlı Yapay Zekalı Terminal Asistanı

Web tarayıcınız üzerinden doğal dilde verdiğiniz komutları (örn: *"Son değiştirilen 5 dosyayı listele ve boyutlarını göster"*) anlayıp uygun shell/bash komutlarını üreten, yürüten ve sonuçları analiz eden **Gemini AI** destekli terminal asistanı.

---

## 🌟 Özellikler
- **Doğal Dil ➔ Terminal Çevirisi:** Karmaşık bash/zsh komutlarını ezberlemek yerine doğrudan Türkçe veya İngilizce talimat verme imkanı.
- **Güvenli Komut Yürütme (`run_terminal_command`):** Komut çıktılarını (`stdout`, `stderr`, `returncode`) yakalayarak kullanıcıya anlaşılır şekilde özetleme.
- **Bağlam ve Dizin Takibi:** Aktif çalışma dizinini (CWD) hatırlayarak oturum boyunca tutarlı işlem yapma.
- **Tek Sayfa Web Arayüzü:** Kurulumsuz, tarayıcıdan anında kullanılabilir hafif Flask sunucusu.

---

## 🚀 Çalıştırma

```bash
pip install Flask google-generativeai
export GEMINI_API_KEY="your_gemini_api_key"
python3 app.py
```
