# cahyonews ai v10 — release candidate

paket ini adalah source production-oriented yang sudah terintegrasi. apk tetap harus di-build setelah backend online.

## alur live
android app -> fastapi -> twelve data / finnhub / gdelt -> intelligence engine -> optional openai -> android

## wajib untuk live
- `FINNHUB_API_KEY`
- `TWELVE_DATA_API_KEY`
- backend HTTPS yang bisa diakses hp
- android build variable `CAHYONEWS_API_URL`

## opsional
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

tanpa openai, signal engine tetap berjalan memakai rules engine.

## deploy backend
### render
gunakan `backend/render.yaml`, lalu isi environment variables di dashboard hosting.

### docker
```bash
cd backend
docker compose up -d --build
```

cek:
- `/api/health`
- `/api/status`
- `/api/dashboard`
- `/api/intelligence`
- `/api/news/history`

## build apk otomatis
workflow `.github/workflows/build-apk.yml` memakai gradle 8.9 + android sdk 35.

buat repository variable:
`CAHYONEWS_API_URL=https://domain-backend-kamu/`

lalu jalankan workflow `build-cahyonews-ai-apk`. hasilnya adalah debug apk yang bisa di-install di android.

## catatan
- `10.0.2.2` hanya untuk emulator, bukan hp fisik.
- api key tidak dimasukkan ke apk.
- historical news bergantung pada cakupan provider.
- signal bukan jaminan profit dan bukan nasihat investasi.
