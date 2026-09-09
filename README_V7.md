# Cahyonews AI v7 — Intelligence Engine

v7 menggabungkan empat lapisan untuk XAUUSD:

1. **technical** — M5/M15/H1/H4, EMA20/50, RSI14, MACD, ATR14, range 20 candle, posisi harga.
2. **fundamental** — economic calendar USD dari Finnhub, forecast/previous/actual, klasifikasi CPI/PPI/NFP/GDP/FOMC/rate dan dampak USD→gold.
3. **market psychology** — trend agreement, overbought/oversold exhaustion, range position, liquidity sweep / failed breakout pada M15.
4. **news sentiment** — headline umum Finnhub dengan lexicon konservatif untuk risk-on/off, hawkish/dovish, inflasi, pekerjaan, yield, perang/geopolitik.

Decision engine memberi **BUY / SELL / WAIT**. Jika bukti bertentangan atau high-impact event sangat dekat, engine memilih WAIT.

Jika `OPENAI_API_KEY` tersedia, model melakukan final refinement dari data terstruktur dan wajib mengembalikan invalidation, entry zone, logika SL/TP. AI tidak boleh mengarang data yang kosong dan tidak boleh menjanjikan profit.

Endpoint utama:
- `/api/health`
- `/api/xauusd`
- `/api/calendar`
- `/api/technical`
- `/api/intelligence`
- `/api/daily-signal`
- `/api/signal`
- `/api/dashboard`

## setup backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000
```

Jangan taruh API key di APK. Untuk HP fisik, ubah `BuildConfig.API_BASE_URL` pada app ke URL HTTPS backend yang sudah dideploy.

**catatan:** ini engine analisis, bukan jaminan profit atau rekomendasi investasi. Data provider dan keterlambatan jaringan dapat memengaruhi hasil.
