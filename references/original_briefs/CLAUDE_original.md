# CLAUDE.md — konteks proyek untuk Claude Code

## Proyek ini apa
Pipeline untuk membuat video edukasi data science (motion graphics flat + avatar karakter + narasi suara clone) dari **episode spec** YAML. Setiap topik menghasilkan dua format: **short** 9:16 (30–60 detik) dan **long** 16:9 (8–12 menit). Requirement lengkap ada di `docs/PRD.md`, dan itu sumber kebenaran untuk scope serta prioritas.

Owner: Peargy, seorang data scientist. Fasih Python, BigQuery, GCP, dan Airflow. Komunikasi dalam Bahasa Indonesia, istilah teknis boleh dalam bahasa Inggris.

## Isi repo saat ini
```
docs/PRD.md                         requirement, arsitektur, milestone, keputusan terbuka
specs/fondasi-01-korelasi.short.yaml  contoh episode spec (terjemahan prototipe v2)
prototype/                          prototipe yang SUDAH JALAN (referensi visual & perilaku)
  scene.html     seluruh video dalam satu HTML/SVG; window.render(t) deterministik
  render.py      Playwright → screenshot JPEG per frame → ffmpeg per scene → concat + audio
  tts.py         TTS Piper (sherpa-onnx) per line + timing.json (start/dur per line, envelope RMS 30fps)
  lines.json     narasi per scene
  make_noise.py  membuat noise0-2.png (tekstur grain)
```

### Menjalankan prototipe
```bash
cd prototype
pip install "sherpa-onnx<1.13" soundfile numpy pillow playwright && playwright install chromium
curl -L -O https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-id_ID-news_tts-medium.tar.bz2 && tar xjf vits-piper-id_ID-news_tts-medium.tar.bz2
python make_noise.py
python tts.py                     # → voice.wav, timing.json
python render.py stills 3.5 10.8  # → still_*.png untuk cek visual
python render.py full             # → contoh_korelasi_kausalitas.mp4
```
Butuh ffmpeg di PATH dan font **Anton** serta **Poppins** terinstal di sistem (Google Fonts).

## Tugas pertama (Milestone M1)
1. Buat struktur paket (usulan: `dsx/` Python untuk CLI, TTS, timing, assembly, dan upload; folder render terpisah).
2. Definisikan **schema episode spec** (pydantic) berdasarkan `specs/*.yaml`, plus validasinya.
3. **Engine render:** konfirmasi dulu ke owner apakah pakai Remotion (rekomendasi PRD §6.3) atau tetap vanilla. Jangan diputuskan sepihak.
4. Port prototipe jadi **scene templates** yang digerakkan oleh spec. Kriteria selesai: render ulang pilot dari YAML hasilnya identik secara visual dengan `prototype/`.
5. CLI minimum: `dsx tts <spec>`, `dsx preview <spec>` (contact sheet), `dsx render <spec>`.

## Aturan render (wajib)
- **Deterministik per frame:** state visual adalah fungsi murni dari `t` (dan timing.json). Dilarang `Date.now()`, CSS animation/transition real-time, `requestAnimationFrame` sebagai sumber waktu, atau random tanpa seed. Pengecualian yang disengaja: state mulut punya "hold minimal 2 frame", jadi frame harus dirender **berurutan**.
- 30 fps. Gambar langsung di ukuran output (1080×1920 untuk short, 1920×1080 untuk long).
- Satu file MP4 per scene dengan setting encoder identik (`libx264 -crf 18 -preset veryfast -pix_fmt yuv420p`), lalu digabung dengan concat demuxer `-c copy`. Audio ditambahkan dengan `-c:v copy`. Crossfade dibuat di dalam file scene, bukan antar file.
- Tulis ke nama sementara `*.tmp.mp4`, rename setelah ffmpeg exit 0.
- Screenshot frame dalam format JPEG kualitas 92, dipipe langsung ke ffmpeg (`image2pipe`, `mjpeg`). Jangan simpan PNG per frame.
- Sebelum render penuh, render dulu beberapa still di momen paling ramai tiap scene dan **lihat hasilnya**.
- Jaga safe area: elemen penting di short tidak boleh masuk ±20% bawah (UI TikTok/IG). Caption berada di y≈1505.

## Desain (jangan diubah tanpa izin owner)
- Token warna, font, caption, grain, dan floaters: lihat PRD §4. Implementasi referensinya ada di `prototype/scene.html`.
- **Karakter:** PRD §5. Kaos polos krem (bukan batik), kepala besar, torso ramping. Karakter **keluar frame saat scene penjelasan**, dan hanya muncul di hook, pertanyaan, dan CTA.
- Lip sync: RMS envelope → `smile <0.05 ≤ small <0.14 ≤ mid <0.28 ≤ wide`, sesekali `o`. Mulut terkunci `smile` saat karakter keluar frame.
- Ikon digambar sendiri dalam SVG. Jangan pakai karakter, logo, atau aset berhak cipta pihak lain.

## Gotcha yang sudah ketemu
- **sherpa-onnx ≥ 2.0** gagal untuk model Piper ("phoneme_codepoints is empty, no frontend available"). Pin ke `sherpa-onnx<1.13`.
- Voice Piper Indonesia di HuggingFace bisa diblokir di beberapa lingkungan. Mirror-nya ada di GitHub release `k2-fsa/sherpa-onnx` tag `tts-models`.
- Lebar pill harus diukur **setelah font termuat** (`getComputedTextLength()` di render pertama). Kalau diukur saat script load, hasilnya pakai font fallback dan pill-nya kebesaran atau kekecilan.
- Glyph `≠` tidak ada di font Anton. Gambar sendiri pakai SVG (dua bar + garis miring), atau hindari di teks.
- Hati-hati tabrakan nama konstanta global dalam satu file JS. Prototipe sempat crash karena `const SH` didefinisikan dua kali. Ini alasan lain untuk memecah jadi modul.
- Group yang di-`pop()`/`slideIn()` mendapat transform dari fungsi itu. Group statis harus diberi `transform=translate(x y)` saat dibuat.
- Nilai statistik di layar (misalnya `r`) wajib dihitung dari data spec. Jangan di-hardcode.

## Audio
- Produksi: ElevenLabs voice clone (`ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`), pakai endpoint TTS *with timestamps* untuk alignment. Jalankan per line, trim silence, gap 0.35s, normalisasi peak 0.9.
- Dev/offline: Piper Indonesia (lihat prototipe).
- Timing caption sementara dibagi proporsional dengan panjang karakter per chunk. Setelah ada alignment, ganti dengan timing kata yang sebenarnya.

## Konvensi kode
- Python 3.11+, type hints, `ruff` + `pytest`. Config lewat `.env` (jangan commit secret; sediakan `.env.example`).
- Output ke `out/<episode_id>/<format>/` (gitignored): `voice.wav`, `timing.json`, `scenes/*.mp4`, `final.mp4`, `contact.png`.
- Commit kecil per fitur. Sebelum mengubah desain visual, kirim still/contact sheet ke owner dulu.
