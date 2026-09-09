# cahyonews ai v4 — live integrated architecture

## what is integrated
- android app -> fastapi backend
- live economic calendar via Finnhub
- live XAUUSD quote via Twelve Data
- AI macro/XAUUSD analysis via OpenAI Responses API
- 30-second backend cache
- 30-second android auto-refresh
- running event countdown based on server event timestamp
- forecast / previous / actual
- online/offline state
- no Telegram

## important
API keys are intentionally NOT embedded in the APK. They belong on the backend so they are not exposed to users.

## backend setup
copy `backend/.env.example` to `backend/.env` and fill:
FINNHUB_API_KEY=...
TWELVE_DATA_API_KEY=...
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.6-luna

then:
pip install -r backend/requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

## android
for local emulator, the app uses:
http://10.0.2.2:8000/

for a deployed backend, change `BuildConfig.API_BASE_URL` in `app/build.gradle.kts` to your HTTPS backend URL ending with `/`.

## data provider note
Twelve Data documents REST quote/time-series endpoints and WebSocket streaming; API availability and credits depend on plan. Finnhub is used here for the economic calendar. The AI layer is optional; without an OpenAI key the backend uses a conservative forecast-vs-previous fallback.
