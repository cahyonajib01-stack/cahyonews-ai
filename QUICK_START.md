# quick start

## backend lokal
cd backend
cp .env.example .env
# isi API keys
./start.sh

cek: http://127.0.0.1:8000/api/status

## build android
./gradlew assembleDebug -PCAHYONEWS_API_URL=https://domain-backend-kamu/

hasil:
app/build/outputs/apk/debug/app-debug.apk

jika hp-only, push project ke github lalu jalankan workflow `.github/workflows/build-apk.yml` dan ambil artifact apk dari GitHub Actions.
