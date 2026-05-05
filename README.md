# Chatbot Konsultasi Pelajaran STT-NF

Aplikasi **chatbot edukatif** berbasis **Streamlit** dan **Google Gemini** (`google.genai`) untuk konsultasi materi perkuliahan. Data percakapan disimpan per pengguna di **SQLite**, jawaban AI dapat diperkaya dengan **RAG hybrid** (keyword + embedding) dari dokumen lokal kampus, serta tersedia **dashboard statistik** dan **ekspor sesi** ke beberapa format.

---

## Daftar isi

- [Ringkasan](#ringkasan)
- [Fitur](#fitur)
- [Stack teknologi](#stack-teknologi)
- [Prasyarat](#prasyarat)
- [Instalasi cepat](#instalasi-cepat)
- [Konfigurasi lingkungan](#konfigurasi-lingkungan)
- [Menjalankan aplikasi](#menjalankan-aplikasi)
- [Struktur folder](#struktur-folder)
- [Cara kerja RAG](#cara-kerja-rag)
- [Basis data](#basis-data)
- [Autentikasi dan keamanan](#autentikasi-dan-keamanan)
- [Batasan API Gemini dan mitigasi](#batasan-api-gemini-dan-mitigasi)
- [Dokumentasi tambahan](#dokumentasi-tambahan)
- [Dokumentasi sistem (diagram & keamanan)](DOKUMENTASI_SISTEM.md)

---

## Ringkasan

| Aspek | Penjelasan singkat |
|--------|---------------------|
| **Peran** | Asisten akademik untuk Prodi TI STT Terpadu Nurul Fikri: jawaban edukatif, bahasa Indonesia, contoh praktis untuk topik teknis. |
| **Antarmuka** | Web interaktif Streamlit: tema **Light/Dark**, menu **Chat**, **Dashboard Mahasiswa**, dan **Admin** (jika `role=admin`), sidebar lengkap. |
| **AI** | Generasi lewat **Gemini** dengan **streaming**; **retry** dan **model fallback** jika satu model sibuk atau error. |
| **Memori** | Riwayat per **sesi chat**; daftar sesi di sidebar; **pin** sesi; pencarian/paginasi riwayat. |
| **Pengetahuan eksternal** | File `.md`/`.txt` di `data/knowledge` (termasuk `uploads/`), filter RAG per sesi, cache embedding `data/rag_index.json`. |
| **Tidak termasuk** | Bukan integrasi **MySQL**; penyimpanan utama adalah **SQLite** (`data/app.db` bawaan konfigurasi). |

---

## Fitur

### Inti chat dan pembelajaran

- Input pertanyaan lewat **chat** dengan respons **real-time (streaming)**.
- **Mode belajar** (mis. ringkas, detail, contoh, kuis) dan **quick prompt** dari toolbar.
- **Flashcard otomatis** (cuplikan ringkas dari jawaban) untuk review cepat.
- **System instruction** khusus asisten TI STT-NF (lihat `src/config/settings.py`).

### Sesi dan riwayat

- **Multi chat session** per akun: buat, pilih, ganti judul, **pin/unpin**, hapus sesi.
- **Cari** isi riwayat dari sidebar; **compact sidebar** untuk tampilan mobile.
- **Hero / stat ringkas**: jumlah sesi, pesan di sesi aktif, mode jawaban.

### RAG dan kutipan sumber

- **Retrieval hybrid**: skor keyword + kemiripan semantik (**embedding** Gemini).
- **Filter per sesi**: semua dokumen vs hanya berkas yang namanya mengandung **`sttnf`** (mode kampus).
- **Sumber RAG** ditampilkan pada jawaban (citation).
- Dokumen pengetahuan di `data/knowledge/`; **unggah PDF** (ekstraksi teks) ke `data/knowledge/uploads/` + rebuild indeks.

### Ekspor dan data

- **Session tools**: unduh percakapan sesi aktif sebagai **Markdown**, **teks biasa**, atau **PDF** (`fpdf2`).
- **Alat data**: backup / restore database SQLite dari antarmuka (sidebar).

### Dashboard Mahasiswa

- Ringkasan **total sesi / pesan**, **target belajar rolling 7 hari** (progress bar), **sesi di-pin** dengan tombol buka ke Chat.
- Daftar **materi RAG** (`data/knowledge`), grafik aktivitas harian, sesi paling aktif, dan **sumber RAG paling sering** dari riwayat jawaban.

### Autentikasi

- **Registrasi / login** multi-akun; kata sandi di-hash (**passlib**, skema PBKdf2 di implementasi saat ini).
- **Token login** di query string (signed) untuk **persistensi** setelah refresh (bergantung pada `AUTH_SECRET_KEY`).
- **Admin** (menu sidebar): statistik global, reset password, ubah role. User pertama dengan hak admin: set **`ADMIN_USERNAMES`** di `.env` (username dipisah koma).

### Mahasiswa (sidebar Chat)

- **Profil** (NIM, angkatan, minat, target pesan/minggu) tersimpan di SQLite.
- **Prompt tersimpan** dan **bookmark pesan**; **filter RAG per sesi** (`semua` vs berkas bernama mengandung `sttnf`).
- **Unggah PDF** ke `data/knowledge/uploads/` + rebuild indeks embedding; pengingat jika sudah lama tidak chat.
- **Skrip opsional:** `python scripts/refresh_rag_index.py`, `python scripts/backup_sqlite.py`, `python scripts/eval_rag_smoke.py` — log di `logs/app.log`.

---

## Stack teknologi

| Kategori | Teknologi |
|----------|-----------|
| Bahasa | Python 3.11+ (disarankan) |
| UI | Streamlit |
| LLM & embedding | Google Gemini API (`google-genai`) |
| Basis data | SQLite (`sqlite3`) |
| Konfigurasi | `python-dotenv` (.env) |
| Autentikasi | passlib + penyimpanan user di SQLite |
| Ekspor PDF | fpdf2 |
| Visualisasi dashboard | Pandas, Altair |
| Ekstraksi PDF (RAG) | pypdf |

---

## Prasyarat

- Python **3.11** atau lebih baru.
- **API key Gemini** (Google AI Studio / Google Cloud).
- Untuk lingkungan Windows + Laragon + Cursor: lihat panduan langkah demi langkah di **[PANDUAN_INSTALASI_AYUB.md](PANDUAN_INSTALASI_AYUB.md)**.

---

## Instalasi cepat

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\activate

pip install -r requirements.txt
copy .env.example .env
# Edit .env — minimal isi GEMINI_API_KEY dan AUTH_SECRET_KEY
```

Penjelasan perintah ringkas dan variabel wajib juga ada di **[CARA_JALANKAN.md](CARA_JALANKAN.md)**.

---

## Konfigurasi lingkungan

Salin `.env.example` menjadi `.env` lalu sesuaikan nilai berikut.

| Variabel | Wajib | Deskripsi |
|----------|-------|-----------|
| `GEMINI_API_KEY` | Ya | Kunci API untuk generate jawaban dan embedding RAG. |
| `AUTH_SECRET_KEY` | Sangat disarankan | Rahasia untuk menandatangani token login di URL; gunakan string panjang dan acak. |
| `APP_NAME` | Tidak | Judul aplikasi di UI. |
| `DB_PATH` | Tidak | Path file SQLite (default: `data/app.db`). |
| `MODEL_NAME` | Tidak | Model utama Gemini (default: `gemini-2.5-flash`). |
| `FALLBACK_MODELS` | Tidak | Daftar model cadangan, dipisah koma. |
| `MAX_RETRY_ATTEMPTS` | Tidak | Jumlah percobaan ulang saat error sementara. |
| `RETRY_DELAY_SECONDS` | Tidak | Jeda antar percobaan (detik). |
| `EMBEDDING_MODEL_NAME` | Tidak | Model embedding (default: `text-embedding-004`). |
| `ADMIN_USERNAMES` | Tidak | Username dipisah koma yang dipromosikan ke **admin** saat aplikasi start (mis. `admin,budi`). Harus sama persis dengan username di database. |

**Catatan:** file `.env` jangan di-commit (sudah diabaikan di `.gitignore`).

---

## Menjalankan aplikasi

```bash
streamlit run app.py
```

Buka browser ke **http://localhost:8501**.

Akun pertama kali dibuat lewat **Register** di sidebar. Jika sebelumnya sudah ada akun uji, gunakan kredensial yang Anda definisikan sendiri (lihat juga **[PANDUAN_INSTALASI_AYUB.md](PANDUAN_INSTALASI_AYUB.md)** untuk contoh akun testing jika dokumentasi tersebut mencantumkannya).

---

## Struktur folder

```
project-ayub/
├── app.py                 # Entry point UI Streamlit (Chat, Dashboard, Admin)
├── requirements.txt
├── .env.example
├── README.md
├── CARA_JALANKAN.md
├── PANDUAN_INSTALASI_AYUB.md
├── DOKUMENTASI_SISTEM.md
├── TROUBLESHOOTING.md
├── scripts/
│   ├── refresh_rag_index.py   # Rebuild cache embedding RAG (CLI)
│   ├── backup_sqlite.py       # Salin DB ke data/backups/
│   └── eval_rag_smoke.py      # Smoke test retrieval
├── src/
│   ├── config/settings.py
│   ├── observability.py       # Logging ke logs/app.log
│   ├── database/
│   │   ├── connection.py
│   │   ├── repository.py      # User, profil, admin, bookmark, prompt, RAG scope, …
│   │   └── schema.sql
│   └── services/
│       ├── chatbot.py
│       └── rag.py
└── data/
    ├── knowledge/             # .md/.txt + uploads/ (PDF → .txt)
    ├── rag_index.json
    ├── backups/               # Output skrip backup (opsional)
    └── app.db                 # SQLite (default di .gitignore)
```

---

## Cara kerja RAG

1. **Sumber:** semua file `.md` dan `.txt` di `data/knowledge/` dibaca dan dipecah menjadi potongan teks.
2. **Embedding:** potongan di-embed dengan API Gemini; vektor disimpan di **`data/rag_index.json`** jika isi dokumen tidak berubah (percepatan startup).
3. **Retrieval:** untuk setiap pertanyaan, skor **keyword** digabung dengan **cosine similarity** embedding untuk memilih potongan relevan.
4. **Generation:** potongan terpilih dimasukkan ke konteks prompt; model menghasilkan jawaban; nama file sumber dapat ditampilkan sebagai **Sumber Belajar**.

**Filter sesi:** jika `rag_scope=sttnf`, hanya potongan dari berkas yang namanya mengandung `sttnf` yang ikut retrieval.

Tidak menggunakan vector database terpisah (mis. FAISS/Chroma) atau orkestrasi LangChain/LlamaIndex; pipeline disengaja dibuat **ringan** dan **self-contained**.

---

## Basis data

- **SQLite** — tabel utama: `users` (profil, `role`, target mingguan), `chat_sessions` (`is_pinned`, `rag_scope`), `chat_messages`, `saved_prompts`, `message_bookmarks`.
- Migrasi kolom/tabel tambahan dijalankan otomatis saat aplikasi start (`ChatRepository`).
- File basis data mengikuti `DB_PATH` di `.env`; skema lengkap di `src/database/schema.sql`.

---

## Autentikasi dan keamanan

- Password tidak disimpan plaintext; verifikasi via hash.
- Persistensi login memakai token bertanda tangan di URL; **ganti `AUTH_SECRET_KEY`** untuk lingkungan produksi dan rahasiakan file `.env`.
- **Admin:** tetapkan `ADMIN_USERNAMES` lalu restart app; panel Admin tidak mengirim password ke log (hanya event login sukses dicatat ringan di `logs/app.log`).
- Unggah PDF disimpan di server (`data/knowledge/uploads/`); batasi akses folder tersebut pada deployment.
- Untuk deployment publik, pertimbangkan HTTPS dan pembatasan rate; aplikasi ini berorientasi pengembangan lokal / akademik.

---

## Batasan API Gemini dan mitigasi

- **`403 PERMISSION_DENIED`:** biasanya masalah project Google, kebijakan, atau kuota. Uji dengan API key/project lain atau hubungi dukungan Google.
- **`Project quota tier unavailable`:** tier kuota belum aktif; sesuaikan billing/tier di konsol Google Cloud sesuai kebijakan Anda.
- **`503 UNAVAILABLE` (high demand):** model sibuk sementara; aplikasi mendukung **retry** dan **fallback model** lewat `.env`.
- **`404 NOT_FOUND` (model):** nama model tidak valid untuk API saat ini; gunakan model yang didukung, misalnya `gemini-2.5-flash`, `gemini-2.0-flash`, `gemini-flash-latest`.
- **Free tier:** batas request lebih ketat; kurangi burst request dan gunakan model ringan + fallback.

Rekomendasi stabilitas di `.env`:

```env
MODEL_NAME=gemini-2.5-flash
FALLBACK_MODELS=gemini-2.0-flash,gemini-flash-latest
MAX_RETRY_ATTEMPTS=2
RETRY_DELAY_SECONDS=1.2
```

Detail error umum dan langkah pengecekan ada di **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**.

---

## Dokumentasi tambahan

| File | Isi |
|------|-----|
| [CARA_JALANKAN.md](CARA_JALANKAN.md) | Langkah ringkas menjalankan server Streamlit |
| [PANDUAN_INSTALASI_AYUB.md](PANDUAN_INSTALASI_AYUB.md) | Instalasi dari nol: Laragon, Cursor, venv, verifikasi |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Solusi error API, login, model, dan lainnya |
| [DOKUMENTASI_SISTEM.md](DOKUMENTASI_SISTEM.md) | Akun uji, use case, user flow, diagram (activity/sequence/class/ER), skema DB, modul pengguna vs admin, keamanan, rute navigasi (Streamlit) |

---

## Status fitur (ringkas)

Fitur yang dirancang untuk skripsi/demo akademik ini meliputi: chat streaming + RAG hybrid, multi-sesi, dashboard mahasiswa, ekspor MD/TXT/PDF, autentikasi multi-akun, panel admin, profil/target belajar, prompt & bookmark, filter RAG per sesi, unggah PDF ke knowledge, skrip backup/refresh/evaluasi, serta logging lokal. **Tidak** termasuk: integrasi MySQL/LMS kampus, email reset password, atau hosting produksi penuh — lihat bagian *Ringkasan* dan *Tidak termasuk*.

---

## Repositori terkait (referensi)

Contoh README/proyek lain dari pengembang yang sama: [web-pendaftaran-tkaqila](https://github.com/Muzaki29/web-pendaftaran-tkaqila) (proyek berbeda; tidak menjadi dependensi folder ini).

---

*Proyek ini dikembangkan untuk konteks pembelajaran dan konsultasi materi di lingkungan STT Terpadu Nurul Fikri.*
