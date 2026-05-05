# Troubleshooting

Panduan cepat ini membantu diagnosis masalah umum pada aplikasi chatbot Streamlit + Gemini.

## Checklist 1 Menit

1. Pastikan app berjalan:
   - `streamlit run app.py`
2. Pastikan file `.env` ada di root project.
3. Cek `GEMINI_API_KEY` terisi dan valid.
4. Cek model utama/fallback sudah diset.
5. Restart app setelah perubahan `.env`.
6. Setelah `git pull` / update kode: jalankan ulang app sekali agar **migrasi SQLite** (kolom/tabel baru) terpasang.

## Menu Admin tidak muncul

- Hanya user dengan `role = admin` yang melihat menu **Admin**.
- Set `ADMIN_USERNAMES=namauser` di `.env` (username **persis** seperti di database), lalu **restart** Streamlit.
- Atau ubah role lewat panel Admin lain / SQL manual pada tabel `users`.

## Unggah PDF gagal / teks kosong

- Beberapa PDF (scan gambar) tidak punya teks; gunakan PDF ber-teks atau tambahkan `.md` manual ke `data/knowledge/`.
- Pastikan `pypdf` terpasang: `pip install -r requirements.txt`.

## Konfigurasi Stabil yang Direkomendasikan

Tambahkan/cek nilai berikut pada `.env`:

```env
MODEL_NAME=gemini-2.5-flash
FALLBACK_MODELS=gemini-2.0-flash,gemini-flash-latest
MAX_RETRY_ATTEMPTS=2
RETRY_DELAY_SECONDS=1.2
EMBEDDING_MODEL_NAME=text-embedding-004
```

## Error Umum dan Solusi

### 1) `403 PERMISSION_DENIED`

Contoh pesan:
- `Your project has been denied access. Please contact support.`

Penyebab umum:
- Project Google terkena pembatasan policy/quota/billing.

Solusi:
- Gunakan API key dari project lain yang aktif.
- Cek status project di Google AI Studio/Google Cloud.
- Jika tetap ditolak, hubungi admin project atau support Google.

### 2) `Project quota tier unavailable`

Penyebab umum:
- Project belum punya tier quota yang valid untuk endpoint generative.

Solusi:
- Aktifkan billing/tier yang sesuai di project.
- Atau pindah ke project lain untuk testing.

### 3) `503 UNAVAILABLE` (high demand)

Contoh pesan:
- `This model is currently experiencing high demand`

Penyebab umum:
- Model sedang overload sementara.

Solusi:
- Retry beberapa detik kemudian.
- Gunakan fallback model (sudah didukung aplikasi).
- Kurangi burst request saat testing.

### 4) `404 NOT_FOUND` model

Contoh pesan:
- `models/... is not found for API version ...`

Penyebab umum:
- Nama model tidak valid/deprecated.

Solusi:
- Ganti ke model yang tersedia, misalnya:
  - `gemini-2.5-flash`
  - `gemini-2.0-flash`
  - `gemini-flash-latest`

### 5) `GEMINI_API_KEY belum diatur`

Penyebab umum:
- `.env` belum ada atau key kosong.

Solusi:
- Copy `.env.example` ke `.env`.
- Isi `GEMINI_API_KEY=...`.
- Restart Streamlit.

### 6) Login/register gagal

Penyebab umum:
- Username sudah dipakai.
- Password terlalu pendek.

Solusi:
- Gunakan username lain.
- Gunakan password minimal 6 karakter.

## Validasi Cepat via Python

Untuk cek key dan model tanpa UI:

```bash
python -c "from src.config.settings import get_settings; from google import genai; s=get_settings(); c=genai.Client(api_key=s.gemini_api_key); r=c.models.generate_content(model=s.model_name, contents='Tes koneksi. Balas: OK'); print(getattr(r,'text','<empty>'))"
```

Jika output `OK`, koneksi API sudah benar.

## Catatan Operasional

- Selalu restart app setelah ubah `.env`.
- Simpan API key hanya di `.env`, jangan di `.env.example`.
- Untuk demo, siapkan minimal 1 model fallback agar lebih tahan gangguan kapasitas.
