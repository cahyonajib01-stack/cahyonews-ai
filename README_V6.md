# cahyonews ai v6 — multi-timeframe XAUUSD engine

tambahan:
- m5, m15, h1, h4 OHLC
- EMA20/EMA50
- RSI14
- MACD
- ATR14
- 20-candle support/resistance range
- weighted multi-timeframe scoring
- BUY / SELL / WAIT otomatis
- confidence 50–95
- AI refinement opsional
- endpoint `/api/technical`
- daily signal dan event signal tetap dapat dikirim lewat notifikasi worker v5

logika sengaja memakai WAIT saat bukti teknikal tidak cukup kuat. signal bukan jaminan profit dan bukan rekomendasi investasi.
