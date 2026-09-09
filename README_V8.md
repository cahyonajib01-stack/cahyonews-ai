# cahyonews ai v8 — permanent news archive

v8 menambahkan arsip berita persisten berbasis SQLite.

- berita umum + berita relevan XAUUSD dari Finnhub dan GDELT
- arsip macro/economic calendar
- snapshot harga XAUUSD
- sinkronisasi otomatis default setiap 5 menit
- `/api/news/history` untuk pencarian/pagination
- `/api/news/xauusd` untuk berita yang relevan ke XAUUSD
- `/api/news/sync` untuk sinkronisasi manual
- `/api/news/backfill?start=YYYY-MM-DD&end=YYYY-MM-DD` untuk backfill historis

catatan penting: tidak ada sumber gratis yang bisa menjamin "semua berita yang pernah terbit di dunia". backfill akan mengambil sebanyak yang tersedia dari provider. setelah v8 berjalan, semua berita yang berhasil diambil akan disimpan ke database sehingga arsip terus bertambah ke depan.
