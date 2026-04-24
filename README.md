# Chatbot Konsultasi Pelajaran STT-NF

Aplikasi chatbot berbasis Streamlit + Gemini (`google.genai`) dengan fitur:

- Input pertanyaan via antarmuka web interaktif
- Respons AI kontekstual
- Streaming respons real-time
- Riwayat percakapan tersimpan di SQLite
- Multi chat session
- Sidebar daftar sesi chat
- Pin/unpin sesi penting
- Pencarian riwayat percakapan + pagination dari sidebar
- Export sesi chat ke `.md` dan `.txt`
- RAG hybrid (keyword + embedding Gemini) dari data eksternal lokal (`data/knowledge`)
- Citation sumber RAG pada jawaban
- UI sederhana dan responsif
- Autentikasi multi-akun (register/login)
- Backup/restore database SQLite dari sidebar

## Menjalankan Aplikasi

1. Buat virtual environment (opsional tapi disarankan).
2. Install dependency:

   ```bash
   pip install -r requirements.txt
   ```

3. Salin `.env.example` menjadi `.env`, lalu isi:
   - `GEMINI_API_KEY`
   - (opsional) `EMBEDDING_MODEL_NAME` (default: `text-embedding-004`)
4. Jalankan:

   ```bash
   streamlit run app.py
   ```

## Limitations & Mitigation (Gemini API)

- `403 PERMISSION_DENIED`:
  - **Penyebab umum**: project Google ditolak akses (policy/billing/quota project).
  - **Mitigasi**: gunakan API key dari project lain yang aktif, atau hubungi admin/support Google.

- `Project quota tier unavailable`:
  - **Penyebab umum**: project belum memiliki tier quota yang valid untuk endpoint generative.
  - **Mitigasi**: aktifkan billing/tier yang sesuai pada project, atau pindah ke project lain.

- `503 UNAVAILABLE` (high demand):
  - **Penyebab umum**: model sedang overload sementara.
  - **Mitigasi**: retry otomatis + fallback model telah diaktifkan via konfigurasi:
    - `MODEL_NAME`
    - `FALLBACK_MODELS`
    - `MAX_RETRY_ATTEMPTS`
    - `RETRY_DELAY_SECONDS`

- `404 NOT_FOUND` model:
  - **Penyebab umum**: nama model tidak tersedia/deprecated untuk API version saat ini.
  - **Mitigasi**: gunakan model valid dari `ListModels`, contoh:
    - `gemini-2.5-flash`
    - `gemini-2.0-flash`
    - `gemini-flash-latest`

- Batasan free tier:
  - **Dampak**: limit request lebih ketat, lebih rentan throttling saat trafik tinggi.
  - **Mitigasi**: gunakan model ringan, kurangi request burst, dan siapkan fallback.

- Rekomendasi `.env` untuk stabilitas:
  - `MODEL_NAME=gemini-2.5-flash`
  - `FALLBACK_MODELS=gemini-2.0-flash,gemini-flash-latest`
  - `MAX_RETRY_ATTEMPTS=2`
  - `RETRY_DELAY_SECONDS=1.2`

## Struktur Utama

- `app.py`: UI Streamlit + alur chat
- `src/database`: koneksi dan repository SQLite
- `src/services/chatbot.py`: integrasi Gemini + streaming
- `src/services/rag.py`: retrieval konteks dari dokumen eksternal
- `data/rag_index.json`: cache embedding untuk percepatan startup berikutnya
- `data/knowledge`: sumber data untuk RAG
- `data/app.db`: database user/sesi/chat
