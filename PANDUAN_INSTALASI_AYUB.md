# Panduan Instalasi Ayub (Cursor AI + Laragon)

Dokumen ini berisi langkah lengkap untuk menjalankan project dari nol di Windows menggunakan Laragon dan Cursor AI.

---

## 1. Prasyarat

Pastikan tools berikut sudah tersedia:

- **Laragon** (sudah terpasang dan bisa dibuka)
- **Python** (disarankan 3.11+; project ini sudah diuji di 3.13)
- **Git**
- **Cursor AI**
- **Akun Google AI Studio** + API key Gemini

Cek cepat lewat terminal:

```bash
python --version
git --version
```

---

## 2. Clone Repository

1. Buka terminal (PowerShell / terminal di Cursor).
2. Masuk ke folder web Laragon:

```bash
cd C:\laragon\www
```

3. Clone project:

```bash
git clone https://github.com/Muzaki29/project-ayub.git
```

4. Masuk ke folder project:

```bash
cd project-ayub
```

---

## 3. Buka Project di Cursor AI

1. Buka Cursor AI.
2. Pilih **Open Folder**.
3. Arahkan ke:
   - `C:\laragon\www\project-ayub`
4. Tunggu indexing selesai.

---

## 4. Setup Environment Python

Disarankan pakai virtual environment lokal project:

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

Jika aktivasi PowerShell terblokir, jalankan PowerShell sebagai user biasa lalu:

```bash
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\activate
```

---

## 5. Install Dependency

Jalankan:

```bash
pip install -r requirements.txt
```

Dependency utama project:

- `streamlit`
- `google-genai`
- `python-dotenv`
- `passlib[bcrypt]`
- `fpdf2`
- `pandas`
- `altair`

---

## 6. Konfigurasi File `.env`

1. Copy dari template:

```bash
copy .env.example .env
```

2. Isi `.env` minimal:

```env
GEMINI_API_KEY=isi_api_key_kamu
APP_NAME=Chatbot Konsultasi Pelajaran STT-NF
DB_PATH=data/app.db
MODEL_NAME=gemini-2.5-flash
FALLBACK_MODELS=gemini-2.0-flash,gemini-flash-latest
MAX_RETRY_ATTEMPTS=2
RETRY_DELAY_SECONDS=1.2
EMBEDDING_MODEL_NAME=text-embedding-004
AUTH_SECRET_KEY=isi_random_secret_panjang
```

Catatan:
- Jangan commit `.env` ke Git.
- `AUTH_SECRET_KEY` wajib panjang/acak untuk kestabilan login berbasis token.

---

## 7. Jalankan Aplikasi

Dari root project:

```bash
streamlit run app.py
```

Atau dengan Python module:

```bash
python -m streamlit run app.py --server.port 8501
```

URL default:
- [http://localhost:8501](http://localhost:8501)

---

## 8. Akun Testing

Jika akun belum ada, lakukan register di UI.

Jika akun testing sudah dibuat sebelumnya:
- Username: `tester_edu`
- Password: `Test12345`

Jika login gagal:
- cek kembali spasi di input username/password
- refresh browser (`Ctrl+F5`)
- lihat `TROUBLESHOOTING.md`

---

## 9. Verifikasi Dasar Setelah Instalasi

### 9.1 Compile check (syntax)

```bash
python -m compileall app.py src
```

### 9.2 Uji fitur inti

Minimal cek:

1. Login/Register
2. Chat normal (streaming jawaban)
3. Sidebar session (buat/pilih session)
4. Dashboard statistik
5. Session tools export (`.md`, `.txt`, `.pdf`)
6. RAG source muncul pada jawaban

---

## 10. Struktur Folder Penting

- `app.py` -> aplikasi Streamlit utama
- `src/config/settings.py` -> konfigurasi env
- `src/database/` -> koneksi + repository database
- `src/services/chatbot.py` -> integrasi model Gemini
- `src/services/rag.py` -> retrieval knowledge
- `data/knowledge/` -> sumber knowledge RAG
- `TROUBLESHOOTING.md` -> panduan penanganan error

---

## 11. Menambah Knowledge Kampus (RAG)

Tambahkan file `.md` di folder:

- `data/knowledge/`

Contoh pola konten yang konsisten:

```md
# Judul Topik
Sumber utama: https://nurulfikri.ac.id/
Pembaruan konten: YYYY-MM-DD

Konten ringkas terstruktur...
```

Setelah update knowledge, restart app agar index retrieval dimuat ulang.

---

## 12. Troubleshooting Cepat

- Jika error API Gemini (`403`, `503`, `404`), baca `TROUBLESHOOTING.md`.
- Jika port bentrok:

```bash
python -m streamlit run app.py --server.port 8502
```

- Jika dependency error, ulang:

```bash
pip install -r requirements.txt
```

---

## 13. Workflow Harian (Singkat)

1. Buka Laragon
2. Buka folder project di Cursor
3. Aktifkan `.venv`
4. `streamlit run app.py`
5. Uji fitur / lanjut pengembangan

---

## 14. Catatan Keamanan

- Jangan simpan API key di `.env.example` atau file publik.
- Jangan push `.env` ke GitHub.
- Rotasi API key jika pernah terekspos.

---

Selesai. Dengan panduan ini, setup dari nol hingga aplikasi berjalan dapat dilakukan secara konsisten.
