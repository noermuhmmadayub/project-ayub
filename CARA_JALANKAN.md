# Cara Menjalankan Aplikasi (project-ayub)

Panduan ringkas untuk menjalankan chatbot Streamlit di folder ini. Untuk instalasi dari nol (clone, Laragon, Cursor), lihat **[PANDUAN_INSTALASI_AYUB.md](PANDUAN_INSTALASI_AYUB.md)**.

---

## Prasyarat

- **Python** 3.11 atau lebih baru (disarankan)
- Terminal/PowerShell dibuka di **root project**, misalnya:

  `C:\laragon\www\project-ayub`

---

## 1. Virtual environment (disarankan)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

Jika aktivasi skrip diblokir di PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\activate
```

---

## 2. Install dependency

```powershell
pip install -r requirements.txt
```

---

## 3. File `.env`

1. Salin template:

   ```powershell
   copy .env.example .env
   ```

2. Edit `.env` dan isi minimal:

   | Variabel | Keterangan |
   |----------|------------|
   | `GEMINI_API_KEY` | API key dari Google AI Studio / Cloud |
   | `AUTH_SECRET_KEY` | String acak panjang (untuk stabilitas login/token) |
   | `ADMIN_USERNAMES` | (Opsional) Username admin, pisah koma — setelah itu **restart** app |

Opsional: sesuaikan `MODEL_NAME`, `FALLBACK_MODELS`, `DB_PATH`, `EMBEDDING_MODEL_NAME` jika perlu. **Jangan** meng-commit file `.env` ke Git.

**Perawatan (opsional):** dari folder project, `python scripts/backup_sqlite.py` menyalin DB ke `data/backups/`; `python scripts/refresh_rag_index.py` membangun ulang cache embedding RAG.

---

## 4. Menjalankan aplikasi

Dari root project (folder yang berisi `app.py`):

```powershell
streamlit run app.py
```

Alternatif (port eksplisit):

```powershell
python -m streamlit run app.py --server.port 8501
```

Buka browser ke: **[http://localhost:8501](http://localhost:8501)**

---

## 5. Menghentikan server

Di terminal tempat Streamlit berjalan, tekan **Ctrl+C**.

---

## 6. Verifikasi cepat (opsional)

Cek sintaks Python:

```powershell
python -m compileall app.py src
```

---

## Dokumen terkait

- **[README.md](README.md)** — ringkasan fitur dan cara jalan singkat
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — error API Gemini, login, quota, model tidak ditemukan, dll.

---

## Catatan Laragon

Project ini dijalankan dengan **Streamlit + Python**; tidak memerlukan Apache/Nginx Laragon untuk development lokal. Cukup jalankan perintah di atas; Laragon dipakai biasanya hanya sebagai lokasi folder `www` (`C:\laragon\www\...`).
