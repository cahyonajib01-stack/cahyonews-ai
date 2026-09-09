# cahyonews ai v9 — full intelligence integration

v9 menyatukan pipeline live XAUUSD + multi-timeframe technical + fundamental + market psychology + news + persistent archive + optional OpenAI reasoning.

## real integrations
- Twelve Data: live XAU/USD quote dan OHLC M5/M15/H1/H4.
- Finnhub: economic calendar dan current general news feed.
- GDELT: news discovery/backfill untuk topik gold, XAUUSD, Fed/FOMC, CPI/PPI/NFP, DXY, Treasury, geopolitik, tarif, perang, dll.
- SQLite: persistent news/economic/market/intelligence history.
- OpenAI Responses API: optional final reasoning layer; jika API key kosong, deterministic rules engine tetap berjalan dan status AI menjadi fallback/rules.
- Android Retrofit: dashboard, intelligence, calendar, signals, dan news archive terhubung ke backend.
- WorkManager: background signal notification dari worker yang sudah ada.

## pipeline
provider -> normalize -> archive -> technical/fundamental/psychology/news engines -> weighted decision -> optional AI refinement -> Android dashboard/notifications.

## historical news
`POST /api/news/backfill?start=YYYY-MM-DD&end=now`

backfill memakai GDELT secara chunk 30 hari. provider menentukan batas arsip dan hasil, jadi sistem tidak mengklaim dapat memulihkan setiap artikel yang pernah terbit di internet.

## live archive
backend otomatis sync default setiap 5 menit. setiap berita yang berhasil diperoleh akan di-dedupe dan disimpan.

## important deployment
jangan memasukkan API key ke APK. isi key pada backend environment. untuk hp fisik, build Android dengan:

`./gradlew assembleDebug -PCAHYONEWS_API_URL=https://domain-backend-kamu/`

`10.0.2.2` hanya default untuk emulator Android.

## safety
signal BUY/SELL/WAIT adalah hasil analisis probabilistik, bukan jaminan profit. engine memprioritaskan WAIT ketika evidence bertentangan atau high-impact news sangat dekat.
