# PRD — DS Explainer: Pipeline Video Edukasi Data Science

**Owner:** Peargy (Firgy Matannatikka)
**Status:** Draft v1 (19 Nov 2026), prototipe visual sudah ada di `prototype/`
**Executor coding:** Claude Code

---

## 1. Ringkasan

Channel edukasi data science dengan dua format per topik:

| Format | Platform | Rasio | Durasi | Fungsi |
|---|---|---|---|---|
| **Long** | YouTube | 16:9 (1920×1080) | 8–12 menit | Penjelasan lengkap dan mendalam |
| **Short** | YouTube Shorts, TikTok, IG Reels | 9:16 (1080×1920) | 30–60 detik | Satu insight "aha" + ajakan ke video panjang |

Gaya penjelasan terinspirasi channel **Antidote**: konsep abstrak dibuat konkret lewat analogi dan contoh, visual menemani narasi (bukan hiasan). Gaya visual: **motion graphics flat** dengan tekstur grain, pill label, subtitle per frasa, dan **avatar karakter** yang mirip Peargy. Narasi pakai **suara clone Peargy**.

Targetnya adalah pipeline yang mengubah **satu topik** jadi **dua video siap upload** dengan intervensi manual minimal (review script dan QA visual).

## 2. Tujuan & non-tujuan

### Tujuan
1. Dari satu *episode spec* (file YAML/JSON) bisa me-render versi long dan short secara deterministik.
2. Library scene template yang bisa dipakai ulang (chart, diagram, kartu definisi, dan seterusnya), supaya video baru cukup dibuat dengan menulis spec, tanpa menulis code animasi baru.
3. Lip sync, subtitle, dan timing animasi otomatis mengikuti audio narasi.
4. Biaya per video rendah, render lokal ≤ 5 menit untuk short.
5. Mendukung produksi series (sekitar 100+ episode) dengan identitas visual yang konsisten.

### Non-tujuan (untuk sekarang)
- Animasi karakter frame-by-frame atau full body. Cukup puppet rig: kepala, mulut, mata, alis, lengan.
- Auto-upload ke TikTok/IG. Upload manual dulu, karena API keduanya butuh approval atau akun bisnis.
- Editor visual / GUI. Cukup CLI + preview.
- Multi-bahasa dalam satu episode.

## 3. Audiens & konten

- **Audiens:** pelajar, mahasiswa, fresh graduate, dan orang yang pindah karier ke data. Level pemula sampai menengah.
- **Bahasa:** ⚠️ *Belum diputuskan* (lihat §12). Default prototipe: Bahasa Indonesia, istilah teknis tetap bahasa Inggris.
- **Struktur series:**
  - **Fondasi** (dipakai bersama semua roadmap): statistik deskriptif, distribusi, probabilitas, korelasi vs kausalitas, SQL, Python untuk data, visualisasi
  - **Roadmap Data Analyst**: SQL lanjutan, dashboard, metrik bisnis, A/B testing, storytelling
  - **Roadmap Data Scientist**: regresi, klasifikasi, overfitting, evaluasi model, feature engineering
  - **Roadmap Data Engineering**: ETL/ELT, warehouse, orkestrasi (Airflow), streaming, data modeling
  - **Roadmap AI/ML**: neural network, backprop, optimisasi
  - **Roadmap NLP**: tokenisasi, embedding, transformer, LLM, RAG
  - **Roadmap CV**: konvolusi, CNN, deteksi objek, segmentasi
  - Setiap roadmap dibuka dengan **Episode 0 berupa peta roadmap**. Episode di roadmap merujuk ke episode Fondasi.
- **Prioritas awal:** Fondasi + satu roadmap (Data Analyst atau Data Scientist).

### Prinsip penulisan script ("Antidote-like")
1. Hook dalam 3 detik pertama: fakta aneh, pertanyaan, atau kesalahan umum.
2. Analogi atau contoh nyata dulu, istilah formal belakangan.
3. Satu konsep per scene. Visual harus mencerminkan kalimat yang sedang diucapkan.
4. Tidak ada jargon tanpa definisi.
5. Short: satu insight dan satu takeaway, diakhiri CTA ke video panjang.
6. Long: bab-bab berurutan (masalah → intuisi → cara kerja → contoh nyata → kesalahan umum → recap).
7. Data sintetis wajib diberi label "ilustrasi". Angka statistik (misalnya r) harus dihitung dari data yang ditampilkan, bukan ditulis tangan.

## 4. Identitas visual (dari prototipe)

| Token | Nilai |
|---|---|
| Background scene (rotasi) | `#1E2A5A` navy, `#0F172A` navy gelap, `#5B3CC4` ungu, `#0F766E` teal, `#111827` hampir hitam |
| Aksen/highlight | `#FFB703` amber |
| Sekunder data | `#7DD3FC` biru muda, `#4ADE80` hijau (naik), `#E63946` merah (salah/silang) |
| Pill terang | `#FFF6E6`, teks `#151a2d` |
| Font heading | **Anton** (uppercase/condensed) |
| Font body/pill/caption | **Poppins** 600–700 |
| Caption | kotak `rgba(12,18,38,.88)`, radius 22, 56px bold, kata kunci warna amber, pop-in per frasa |
| Tekstur | grain overlay (`mix-blend-mode: overlay`, opacity ~0.3, ganti tile tiap 2 frame) |
| Dekorasi | simbol statistik samar melayang (%, Σ, σ, μ, r, R², x̄), opacity 0.07 |
| Animasi | pop-in `easeBack` 0.35s, slide-in `easeOut`, draw-on untuk garis/panah (stroke-dashoffset) |

## 5. Karakter (avatar Peargy)

- **Gaya:** flat vector, kepala besar (proporsi chibi ala explainer), tekstur grain dari overlay global.
- **Ciri:** rambut hitam pendek disisir ke atas/samping dengan volume di atas, wajah bulat, kulit sawo matang (`#E3A77C`, bayangan `#D9996E`/`#C98B63`), pipi blush, senyum lebar, tanpa kacamata.
- **Pakaian:** kaos polos lengan pendek warna krem (`#F1E6D3`, bayangan `#DCCDB4`). Jangan pakai batik.
- **Rig:** kepala (bob/tilt mengikuti audio), mata (kedip), alis (naik saat bertanya), 5 bentuk mulut (`smile`, `small`, `mid`, `wide`, `o`), lengan 2 segmen (upper arm dengan lengan kaos + forearm kulit) dengan pose `rest`, `wave`, `shrug`, `open`, ditambah `point` (sudah ada di v1, perlu di-port).
- **Lip sync:** amplitudo RMS audio per frame dipetakan ke bentuk mulut (threshold 0.05 / 0.14 / 0.28), tiap bentuk ditahan minimal 2 frame. Upgrade opsional: Rhubarb Lip Sync (berbasis fonem).
- **Kehadiran di frame:** karakter **hanya muncul** di hook, momen pertanyaan/emosi, dan CTA. Di scene penjelasan karakter **turun keluar frame** (slide 0.5s) supaya materi memakai layar penuh. Ini keputusan eksplisit dari owner.
- **Masa depan:** desain final bisa dibuat ilustrator (SVG dengan layer terpisah per part) lalu di-rig dengan sistem yang sama.

## 6. Arsitektur pipeline

```
topic ──► [1] Outline/master script (Claude API + style guide)
          │
          ├─► [2a] Script LONG ─┐
          └─► [2b] Script SHORT ┴─► [3] Episode spec (YAML: lines + scenes + timing hints)
                                        │
                                  [4] HUMAN REVIEW (wajib)
                                        │
                                  [5] TTS voice clone (ElevenLabs, with-timestamps)
                                        │  voice.wav + alignment per karakter/kata
                                  [6] Timing build: line start/dur, caption chunks, envelope per frame
                                        │
                                  [7] Render scenes (deterministik per frame) → scene MP4s
                                        │
                                  [8] Assembly: concat + audio + musik (ducking) → final MP4
                                        │
                                  [9] QA: contact sheet frame kunci + cek durasi/loudness
                                        │
                                  [10] Publish: YouTube Data API (long + Shorts); TikTok/IG manual
                                       + metadata (judul, deskripsi, tag, chapter, thumbnail)
```

### 6.1 Episode spec (kontrak inti)
Satu file per format per episode, contohnya `specs/fondasi-01-korelasi.short.yaml`. Strukturnya:
- `meta`: id, series, episode, format (`short`/`long`), resolution, fps, bahasa, link ke pasangan long/short
- `voice`: provider, voice_id, speed
- `scenes[]`: tiap scene berisi:
  - `line`: teks narasi (yang diucapkan)
  - `captions[]`: pecahan frasa; `*kata*` = highlight
  - `character`: `on` / `off`, dan `pose` (opsional, dengan waktu relatif)
  - `bg`: warna token
  - `template`: nama scene template + `props`
  - `cues[]`: `{at: <fraksi 0–1 dari durasi line atau kata kunci>, do: <aksi elemen>}`

Contoh lengkap: `specs/fondasi-01-korelasi.short.yaml` (hasil terjemahan prototipe v2).

### 6.2 Scene template library (minimum v1)
Template yang sudah terbukti di prototipe: `title_icons` (hook dengan ikon dan panah naik), `line_chart`, `scatter_regression` (r dihitung otomatis), `question_link` (A → ? → B), `causal_diagram` (confounder + link palsu dicoret), `definition_card` (kata + definisi + diagram Z→X, Z→Y), `takeaway` (judul ≠ + poin + pill tips), `follow_cta`.

Backlog: `code_snippet` (syntax highlight + reveal per baris), `table`, `formula` (KaTeX), `process_flow`, `comparison_split`, `bar_chart`, `distribution` (histogram/kurva), `roadmap_map` (untuk Episode 0), `chapter_title` (long).

Setiap template harus punya varian layout **9:16 dan 16:9**.

### 6.3 Engine render — keputusan
- **Prototipe (sekarang):** satu HTML/SVG vanilla dengan fungsi `render(t)` deterministik, Playwright mengambil screenshot JPEG per frame lalu dipipe ke ffmpeg. Sudah terbukti jalan: 32 detik video ±1 menit render.
- **Rekomendasi produksi: Remotion (React + TypeScript).** Alasannya: komponen scene bisa dipakai ulang dan bertipe, ada preview Studio untuk iterasi cepat, audio sync dan sequencing sudah built-in, dan rendernya paralel. Lisensinya gratis untuk individu/tim kecil, tapi tetap cek ulang ketentuan terbaru sebelum mulai.
- **Alternatif kalau Remotion ditolak:** pertahankan engine vanilla, tapi pecah jadi modul (`templates/*.js`, `rig.js`, `captions.js`) dan generate HTML dari spec.
- Bagaimanapun pilihannya, **render harus deterministik per frame**: tidak boleh pakai `Date.now()`, CSS animation real-time, atau random tanpa seed.

### 6.4 Audio
- **TTS produksi:** ElevenLabs voice clone milik Peargy. Gunakan endpoint text-to-speech *with timestamps* untuk alignment per karakter, lalu turunkan jadi timing kata dan caption.
- **Fallback/dev:** Piper `id_ID-news_tts-medium` via sherpa-onnx (offline, gratis, kualitas robotik). Ini yang dipakai prototipe.
- Generate per line, trim silence, gap 0.35s antar line, normalisasi peak 0.9. Target loudness final sekitar −14 LUFS.
- **Musik latar:** royalty-free dengan lisensi jelas, di-duck −18 dB di bawah narasi. Sumber musiknya belum dipilih.

### 6.5 Infrastruktur
- **Fase 1:** lokal (laptop), CLI `make`/`python -m dsx ...`.
- **Fase 2:** GCP. Cloud Run Jobs untuk render, GCS untuk aset dan output, Secret Manager untuk API key. Orkestrasi dengan Airflow (sudah familiar) atau Cloud Workflows.
- **Secrets:** `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, kredensial OAuth YouTube. Simpan di `.env` (jangan di-commit).

## 7. Requirement fungsional

| ID | Requirement | Prioritas |
|---|---|---|
| F1 | CLI `dsx new <topic>` membuat outline + draft spec long & short via Claude API | P1 |
| F2 | Spec divalidasi dengan schema (pydantic/zod) sebelum render | P0 |
| F3 | `dsx tts <spec>` → `voice.wav` + `timing.json` (line start/dur, kata, envelope 30fps) | P0 |
| F4 | `dsx preview <spec>` → contact sheet PNG frame kunci (titik paling ramai tiap scene) | P0 |
| F5 | `dsx render <spec>` → MP4 final (H.264, yuv420p, 30fps, AAC 192k) | P0 |
| F6 | Render ulang satu scene saja tanpa render semua | P1 |
| F7 | Ganti audio (misalnya re-record) tanpa re-render visual kalau timing sama; kalau timing berubah, re-render | P1 |
| F8 | Lip sync, kedip, gerak kepala, dan pose otomatis dari timing | P0 |
| F9 | Caption per frasa dengan highlight, posisi aman dari UI TikTok/IG (bawah ~20% dikosongkan) | P0 |
| F10 | Generate metadata: judul, deskripsi, hashtag, chapter (long) | P2 |
| F11 | Upload YouTube via API (private dulu) | P2 |
| F12 | Thumbnail generator (template + karakter + judul) | P2 |

## 8. Requirement non-fungsional
- Render short (≤60s) ≤ 5 menit di laptop; long (10 menit) ≤ 45 menit, atau paralel di cloud.
- Output konsisten antar render (deterministik).
- Semua angka di chart berasal dari data di spec.
- Tidak ada aset berhak cipta pihak lain (karakter, logo, musik tanpa lisensi).
- Label konten AI: centang opsi "altered/synthetic content" saat upload karena suaranya clone.

## 9. Milestone

| Fase | Output | Kriteria selesai |
|---|---|---|
| **M0 (selesai)** | Prototipe v2 short "Korelasi bukan kausalitas" | Video 32s, karakter on/off, 7 scene |
| **M1** | Repo terstruktur + spec schema + port prototipe ke engine pilihan, spec-driven | Render ulang pilot dari `specs/*.yaml` dan hasilnya identik secara visual |
| **M2** | Voice clone ElevenLabs + alignment + caption dari timestamp | Pilot dengan suara Peargy, lip sync rapi |
| **M3** | Varian 16:9 + template long-form + versi long pilot (8–12 menit) | Satu pasang long+short siap upload |
| **M4** | Generator script (Claude API) + review flow + 5 template baru | Episode baru dari topik → spec draft < 10 menit kerja manual |
| **M5** | Cloud (Cloud Run + GCS) + upload YouTube API + metadata | Satu perintah: spec → video ter-upload private |

## 10. Metrik keberhasilan
- Waktu produksi per pasang video (target: < 2 jam kerja manual).
- Retensi Shorts (rata-rata durasi tonton > 70%), CTR dari Short ke Long.
- Konsistensi upload (target: 1 pasang/minggu setelah M3).

## 11. Risiko
| Risiko | Mitigasi |
|---|---|
| Suara clone kurang natural dalam Bahasa Indonesia | Tes beberapa provider; siapkan opsi rekam suara asli |
| Visual terasa template/monoton | Library template terus bertambah; variasi layout dan warna per series |
| Render long lambat | Render paralel per scene; cloud |
| Akurasi materi | Review manual wajib di tahap [4]; sertakan referensi di deskripsi |
| Lisensi Remotion/musik berubah | Cek ketentuan saat setup; simpan bukti lisensi musik |

## 12. Keputusan terbuka (perlu jawaban owner)
1. **Bahasa video**: Indonesia, Inggris, atau Indonesia + istilah Inggris.
2. **Nama channel** dan handle.
3. **Engine render**: Remotion (rekomendasi) atau lanjut vanilla HTML.
4. **Desain karakter final**: iterasi SVG sendiri atau ilustrator.
5. **Provider suara**: ElevenLabs (rekomendasi) atau open-source.
6. **Sumber musik latar.**
7. **Series pertama** setelah Fondasi: Data Analyst atau Data Scientist.
