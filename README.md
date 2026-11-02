# Kripto Piyasa Takip Programı (CoinGecko API)

CoinGecko API'sinden global piyasa özetini, coin piyasa tablosunu ve geçmiş fiyat verisini çeken, Pandas ile analiz eden ve sonuçları CSV ve Excel olarak kaydeden konsol tabanlı Python programı.

> Veriler bilgilendirme amaçlıdır, **yatırım tavsiyesi değildir.**
> Veri kaynağı: [CoinGecko](https://www.coingecko.com)

## Özellikler

- **Global piyasa özeti:** Aktif coin sayısı, borsa sayısı, toplam piyasa değeri ve hacim, Bitcoin/Ethereum dominansı, 24 saatlik değişim
- **Coin piyasa tablosu:** Piyasa değerine göre ilk N coin (fiyat, piyasa değeri, 24s değişim)
- **Geçmiş fiyat verisi:** Seçilen coin için son N günün zaman serisi
- **Pandas ile analiz:** Her coinin listedeki payı, ortalama / en yüksek / en düşük değerler, en çok yükselen ve düşen coin, geçmiş verideki toplam değişim
- **Tam rapor:** Üç veriyi tek seferde çeker, analiz eder, dosyalara kaydeder
- **Sağlam hata yönetimi:**
  - İstek zaman aşımı (timeout)
  - Limit aşımında (HTTP 429) bekleyip otomatik tekrar deneme
  - Bağlantı ve sunucu hatalarında artan bekleme süresiyle tekrar deneme
  - Eksik veya boş (null) alanlara karşı korumalı veri okuma
  - Geçersiz kullanıcı girdilerine karşı doğrulama
- **Loglama:** Tüm işlemler `crypto.log` dosyasına zaman damgasıyla kaydedilir
- **Güvenli anahtar yönetimi:** API anahtarı kodda değil, `.env` dosyasında tutulur

## Kullanılan Teknolojiler

Python 3, `requests`, `pandas`, `openpyxl`, `python-dotenv`, `logging`

## Kurulum

1. Depoyu indirin ve klasöre girin.

2. Gerekli paketleri kurun:

```bash
pip install -r requirements.txt
```

3. [CoinGecko](https://www.coingecko.com) sitesinden ücretsiz bir API anahtarı alın.

4. `.env.example` dosyasını `.env` olarak kopyalayın ve anahtarınızı yazın:

```
COINGECKO_API_KEY=buraya_anahtarinizi_yazin
```

> `.env` dosyası gizli kalmalıdır, GitHub'a yüklenmez (`.gitignore` içinde).

## Kullanım

```bash
python crypto_tracker.py
```

```
========================================
     KRİPTO PİYASA TAKİP PROGRAMI
========================================
1 - Global piyasa özeti
2 - Coin piyasa tablosu
3 - Coin geçmiş fiyat verisi
4 - Tam rapor (analiz + CSV/Excel kaydı)
5 - Çıkış
```

### Örnek Çıktı

Seçenek 4 (tam rapor), 10 coin, Bitcoin, 7 gün. Çıktı 1 Kasım 2026 tarihlidir, değerler sürekli değişir.

```
Rapor hazırlanıyor, lütfen bekleyin...

--- GÜNCEL GLOBAL PİYASA DURUMU ---
Aktif coin sayısı        : 22,670
Borsa sayısı             : 1,520
Toplam piyasa değeri     : $2,627,229,732,711
24s işlem hacmi          : $78,658,162,097
Bitcoin dominansı        : %59.25
Ethereum dominansı       : %10.45
Piyasa değeri 24s değişim: %-2.02

--- PİYASA DEĞERİNE GÖRE İLK 10 COİN ---
  1. Bitcoin (BTC) | $77,503.0000 | 24s: %1.09 | Liste payı: %65.17
  2. Ethereum (ETH) | $2,252.5200 | 24s: %0.71 | Liste payı: %11.51
  3. Tether (USDT) | $0.9995 | 24s: %0.04 | Liste payı: %7.53
  4. BNB (BNB) | $702.1300 | 24s: %0.88 | Liste payı: %3.86
  5. XRP (XRP) | $1.2500 | 24s: %0.18 | Liste payı: %3.32
  ...

--- BITCOIN SON 7 GÜN ---
Veri noktası sayısı : 169
Başlangıç fiyatı    : $80,348.4838
Son fiyat           : $77,513.1481
Değişim             : %-3.53
En düşük / En yüksek: $76,360.1781 / $81,691.7499
Ortalama            : $79,539.4463

Rapor 'output' klasörüne kaydedildi.
```

> **Liste payı**, coinin yalnızca listelenen coinler içindeki payıdır. Bitcoin dominansı ise tüm kripto piyasasına göre hesaplanır, bu yüzden iki değer farklıdır.

## Çıktı Dosyaları

Seçenek 4 çalıştırıldığında `output/` klasöründe oluşur:

| Dosya | Açıklama |
|---|---|
| `crypto_market_summary.csv` | Global piyasa özeti |
| `crypto_markets.csv` | Coin tablosu (liste payı dahil) |
| `crypto_history_<coin>.csv` | Seçilen coinin geçmiş fiyat serisi |
| `crypto_report.xlsx` | Hepsi tek Excel dosyasında, ayrı sayfalar halinde (istatistik sayfası dahil) |

Ayrıca proje klasöründe `crypto.log` oluşur.

## Proje Yapısı

```
crypto_tracker.py   # Ana program
requirements.txt    # Gerekli paketler
.env.example        # Ortam değişkeni şablonu
README.md
```

Kod katmanlara ayrılmıştır: **API katmanı** (istek, tekrar deneme, hata yönetimi), **analiz katmanı** (Pandas), **çıktı katmanı** (CSV/Excel), **kullanıcı arayüzü** (menü).

## Notlar

- Ücretsiz planın istek limitleri CoinGecko'nun güncel dokümanına bağlıdır. Program, limit aşımında bekleyip tekrar dener.
- Zaman serisindeki saatler UTC'dir.

## Sürüm

**v1.0**

---

## English Summary

A command-line Python tool that pulls global market data, a ranked coin table, and historical price series from the CoinGecko API, analyzes them with Pandas, and exports the results to CSV and Excel. It includes request timeouts, automatic retry with backoff on rate limits (HTTP 429), null-safe parsing, input validation, file logging, and secure API key handling via `.env`.

**Setup:** `pip install -r requirements.txt`, copy `.env.example` to `.env` and add your CoinGecko API key, then run `python crypto_tracker.py`.

Data provided by CoinGecko. For informational purposes only, not financial advice.
