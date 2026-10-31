"""Kripto Piyasa Takip Programi (CoinGecko API).

Global piyasa ozetini, coin piyasa tablosunu ve gecmis fiyat verisini ceker,
Pandas ile analiz eder ve CSV / Excel olarak kaydeder.

Gereksinimler: requests, pandas, openpyxl, python-dotenv
Not: Veriler bilgilendirme amaclidir, yatirim tavsiyesi degildir.
Veri kaynagi: CoinGecko
"""

import logging
import os
import random
import re
import sys
import time

import pandas as pd
import requests
from dotenv import load_dotenv

# .env dosyasindan API anahtarini oku (anahtar kodun icine yazilmaz)
load_dotenv()
API_KEY = os.getenv("COINGECKO_API_KEY")

BASE_URL = "https://api.coingecko.com/api/v3/"
HEADERS = {"x-cg-demo-api-key": API_KEY}
VS_CURRENCY = "usd"

TIMEOUT = 10
MAX_RETRIES = 3
RATE_LIMIT_WAIT = 60      # 429 gelirse ve sunucu sure bildirmezse (saniye)
MIN_WAIT = 1
MAX_WAIT = 3

DEFAULT_COIN_COUNT = 20
MAX_COIN_COUNT = 250
DEFAULT_COIN_ID = "bitcoin"
DEFAULT_DAYS = 7
MAX_DAYS = 365

OUTPUT_DIR = "output"
LOG_FILE = "crypto.log"

# log kurulumu: dosyaya ayrintili (INFO+), ekrana sadece uyarilar (WARNING+)
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s"
    )
)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])
log = logging.getLogger(__name__)


# --- API katmani ---

def get_wait_time(response):
    """429 cevabindaki Retry-After basligini okur, yoksa varsayilan sureyi doner."""
    value = response.headers.get("Retry-After", "")
    return int(value) if value.isdigit() else RATE_LIMIT_WAIT


def api_get(endpoint, params=None):
    """CoinGecko'ya GET istegi atar. Basarili olursa JSON, olmazsa None doner."""
    url = BASE_URL + endpoint

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.info("Istek: %s (deneme %s/%s)", url, attempt, MAX_RETRIES)
            response = requests.get(
                url, headers=HEADERS, params=params, timeout=TIMEOUT
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            log.warning("Baglanti sorunu: %s", e)
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
            continue
        except requests.exceptions.RequestException as e:
            log.error("Istek hatasi: %s", e)
            return None

        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                log.error("Gecersiz JSON cevabi: %s", url)
                return None

        if response.status_code == 429:
            wait = get_wait_time(response)
            log.warning("Istek limiti asildi (429), %s sn bekleniyor.", wait)
            if attempt < MAX_RETRIES:
                time.sleep(wait)
            continue

        if response.status_code >= 500:
            log.warning("Sunucu hatasi (%s): %s", response.status_code, url)
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
            continue

        # 401, 403, 404 gibi tekrar denemenin ise yaramayacagi hatalar
        log.error("HTTP %s hatasi: %s", response.status_code, url)
        return None

    log.error("Maksimum deneme sayisina ulasildi: %s", url)
    return None


def fetch_global():
    """Global piyasa ozetini sozluk olarak doner."""
    raw = api_get("global")
    if not isinstance(raw, dict):
        return None

    data = raw.get("data") or {}
    total_cap = data.get("total_market_cap") or {}
    total_volume = data.get("total_volume") or {}
    percentages = data.get("market_cap_percentage") or {}

    return {
        "active_coins": data.get("active_cryptocurrencies"),
        "markets": data.get("markets"),
        "total_market_cap_usd": total_cap.get("usd"),
        "total_volume_usd": total_volume.get("usd"),
        "btc_dominance_pct": percentages.get("btc"),
        "eth_dominance_pct": percentages.get("eth"),
        "market_cap_change_24h_pct": data.get("market_cap_change_percentage_24h_usd"),
    }


def fetch_markets(count=DEFAULT_COIN_COUNT):
    """Piyasa degerine gore ilk 'count' coini DataFrame olarak doner."""
    params = {
        "vs_currency": VS_CURRENCY,
        "order": "market_cap_desc",
        "per_page": count,
        "page": 1,
    }
    raw = api_get("coins/markets", params)
    if not isinstance(raw, list):
        return pd.DataFrame()

    rows = []
    for coin in raw:
        rows.append(
            {
                "name": coin.get("name"),
                "symbol": (coin.get("symbol") or "").upper(),
                "price_usd": coin.get("current_price"),
                "market_cap": coin.get("market_cap"),
                "change_24h_pct": coin.get("price_change_percentage_24h"),
            }
        )
    return pd.DataFrame(rows)


def fetch_market_chart(coin_id=DEFAULT_COIN_ID, days=DEFAULT_DAYS):
    """Bir coinin gecmis fiyat verisini (zaman serisi) DataFrame olarak doner."""
    params = {"vs_currency": VS_CURRENCY, "days": days}
    raw = api_get(f"coins/{coin_id}/market_chart", params)
    if not isinstance(raw, dict):
        return pd.DataFrame()

    prices = raw.get("prices") or []
    if not prices:
        return pd.DataFrame()

    df = pd.DataFrame(prices, columns=["timestamp_ms", "price_usd"])
    # CoinGecko zamani milisaniye olarak verir
    df["time_utc"] = pd.to_datetime(df["timestamp_ms"], unit="ms")
    return df[["time_utc", "price_usd"]]


# --- Analiz katmani ---

def analyze_markets(df):
    """Coin tablosuna pay sutunu ekler ve temel istatistikleri hesaplar."""
    df = df.copy()
    df["share_in_list_pct"] = (df["market_cap"] / df["market_cap"].sum() * 100).round(2)
    stats = df[["price_usd", "market_cap", "change_24h_pct"]].describe().round(2)
    return df, stats


def analyze_history(df):
    """Zaman serisi icin baslangic, bitis, degisim, en dusuk/yuksek ve ortalama doner."""
    first = df["price_usd"].iloc[0]
    last = df["price_usd"].iloc[-1]
    return {
        "start_price": first,
        "end_price": last,
        "change_pct": (last - first) / first * 100 if first else None,
        "min_price": df["price_usd"].min(),
        "max_price": df["price_usd"].max(),
        "mean_price": df["price_usd"].mean(),
    }


# --- Cikti katmani ---

def save_csv(df, filename):
    """DataFrame'i output klasorune CSV olarak kaydeder."""
    path = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    log.info("CSV kaydedildi: %s", path)


def export_report(global_data, markets_df, stats_df, history_df, coin_id):
    """Elde edilen verileri CSV dosyalarina ve tek bir Excel dosyasina kaydeder."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sheets = {}

    if global_data:
        summary_df = pd.DataFrame([global_data])
        save_csv(summary_df, "crypto_market_summary.csv")
        sheets["global"] = summary_df

    if not markets_df.empty:
        save_csv(markets_df, "crypto_markets.csv")
        sheets["markets"] = markets_df
        sheets["markets_stats"] = stats_df.reset_index().rename(
            columns={"index": "metric"}
        )

    if not history_df.empty:
        save_csv(history_df, f"crypto_history_{coin_id}.csv")
        sheets["history"] = history_df

    if not sheets:
        log.warning("Kaydedilecek veri bulunamadi.")
        return False

    excel_path = os.path.join(OUTPUT_DIR, "crypto_report.xlsx")
    try:
        with pd.ExcelWriter(excel_path) as writer:
            for name, df in sheets.items():
                df.to_excel(writer, sheet_name=name, index=False)
        log.info("Excel raporu kaydedildi: %s", excel_path)
    except (ImportError, OSError) as e:
        # ImportError: openpyxl kurulu degil, OSError: dosya baska programda acik
        log.error("Excel kayit hatasi: %s", e)
        return False

    return True


# --- Ekran ciktilari ---

def fmt(value, decimals=2):
    """Sayiyi binlik ayiracli yazar, bos degerde '-' doner."""
    if value is None or pd.isna(value):
        return "-"
    return f"{value:,.{decimals}f}"


def fmt_pct(value, signed=False):
    """Yuzdeyi '12.34%' bicimine cevirir, signed=True ise +/- isareti ekler."""
    if value is None or pd.isna(value):
        return "-"
    return f"{value:+,.2f}%" if signed else f"{value:,.2f}%"


def print_failure():
    print("\nVeri alınamadı. Ayrıntılar için crypto.log dosyasına bakın.")


def print_global(data):
    print("\n--- GÜNCEL GLOBAL PİYASA DURUMU ---")
    print(f"Aktif coin sayısı        : {fmt(data['active_coins'], 0)}")
    print(f"Borsa sayısı             : {fmt(data['markets'], 0)}")
    print(f"Toplam piyasa değeri     : ${fmt(data['total_market_cap_usd'], 0)}")
    print(f"24s işlem hacmi          : ${fmt(data['total_volume_usd'], 0)}")
    print(f"Bitcoin dominansı        : {fmt_pct(data['btc_dominance_pct'])}")
    print(f"Ethereum dominansı       : {fmt_pct(data['eth_dominance_pct'])}")
    print(
        "Piyasa değeri 24s değişim: "
        f"{fmt_pct(data['market_cap_change_24h_pct'], signed=True)}"
    )


def print_markets(df, stats):
    print(f"\n--- PİYASA DEĞERİNE GÖRE İLK {len(df)} COİN ---")
    for rank, row in enumerate(df.itertuples(index=False), 1):
        print(
            f"{rank:>3}. {row.name} ({row.symbol}) | ${fmt(row.price_usd, 4)} "
            f"| 24s: {fmt_pct(row.change_24h_pct, signed=True)} "
            f"| Liste payı: {fmt_pct(row.share_in_list_pct)}"
        )

    valid = df.dropna(subset=["change_24h_pct"])
    if not valid.empty:
        best = valid.loc[valid["change_24h_pct"].idxmax()]
        worst = valid.loc[valid["change_24h_pct"].idxmin()]
        print(f"\nEn çok yükselen : {best['name']} ({fmt_pct(best['change_24h_pct'], signed=True)})")
        print(f"En çok düşen    : {worst['name']} ({fmt_pct(worst['change_24h_pct'], signed=True)})")

    print("\nİstatistikler:")
    print(stats.to_string(float_format="{:,.2f}".format))


def print_history(df, summary, coin_id, days):
    print(f"\n--- {coin_id.upper()} SON {days} GÜN ---")
    print(f"Veri noktası sayısı : {len(df)}")
    print(f"Başlangıç fiyatı    : ${fmt(summary['start_price'], 4)}")
    print(f"Son fiyat           : ${fmt(summary['end_price'], 4)}")
    print(f"Değişim             : {fmt_pct(summary['change_pct'], signed=True)}")
    print(f"En düşük / En yüksek: ${fmt(summary['min_price'], 4)} / ${fmt(summary['max_price'], 4)}")
    print(f"Ortalama            : ${fmt(summary['mean_price'], 4)}")


# --- Kullanici girdisi ---

def ask_int(prompt, default, min_value, max_value):
    """Sinirlar icinde bir tam sayi ister, gecersizse varsayilani kullanir."""
    value = input(f"{prompt} [{default}]: ").strip()
    if not value:
        return default
    try:
        number = int(value)
    except ValueError:
        print("Geçersiz giriş, varsayılan değer kullanılıyor.")
        return default
    if not min_value <= number <= max_value:
        print(f"Değer {min_value}-{max_value} arasında olmalı, varsayılan kullanılıyor.")
        return default
    return number


def ask_coin_id():
    """Coin ID'sini ister. Sadece harf, rakam, tire, nokta ve alt cizgiye izin verir."""
    value = input(f"Coin ID (örn: bitcoin, ethereum, solana) [{DEFAULT_COIN_ID}]: ")
    value = value.strip().lower()
    if not value:
        return DEFAULT_COIN_ID
    if not re.fullmatch(r"[a-z0-9._-]+", value):
        print("Geçersiz coin ID, varsayılan kullanılıyor.")
        return DEFAULT_COIN_ID
    return value


# --- Akislar ---

def run_full_report():
    """Uc veriyi cekip analiz eder ve dosyalara kaydeder."""
    count = ask_int("Kaç coin listelensin", DEFAULT_COIN_COUNT, 1, MAX_COIN_COUNT)
    coin_id = ask_coin_id()
    days = ask_int("Kaç günlük geçmiş veri", DEFAULT_DAYS, 1, MAX_DAYS)

    print("\nRapor hazırlanıyor, lütfen bekleyin...")
    log.info("Tam rapor basladi (coin sayisi=%s, coin=%s, gun=%s).", count, coin_id, days)

    global_data = fetch_global()
    time.sleep(random.uniform(MIN_WAIT, MAX_WAIT))
    markets_df = fetch_markets(count)
    time.sleep(random.uniform(MIN_WAIT, MAX_WAIT))
    history_df = fetch_market_chart(coin_id, days)

    stats_df = pd.DataFrame()
    if not markets_df.empty:
        markets_df, stats_df = analyze_markets(markets_df)

    if global_data:
        print_global(global_data)
    if not markets_df.empty:
        print_markets(markets_df, stats_df)
    if not history_df.empty:
        print_history(history_df, analyze_history(history_df), coin_id, days)

    if export_report(global_data, markets_df, stats_df, history_df, coin_id):
        print(f"\nRapor '{OUTPUT_DIR}' klasörüne kaydedildi.")
    else:
        print_failure()


def main():
    if not API_KEY:
        log.critical("COINGECKO_API_KEY bulunamadi. .env dosyasini kontrol edin.")
        sys.exit(1)

    while True:
        print("\n" + "=" * 40)
        print("     KRİPTO PİYASA TAKİP PROGRAMI")
        print("=" * 40)
        print("1 - Global piyasa özeti")
        print("2 - Coin piyasa tablosu")
        print("3 - Coin geçmiş fiyat verisi")
        print("4 - Tam rapor (analiz + CSV/Excel kaydı)")
        print("5 - Çıkış")
        print("-" * 40)

        choice = input("İşlem numarası (1-5): ").strip()

        if choice == "1":
            data = fetch_global()
            print_global(data) if data else print_failure()

        elif choice == "2":
            count = ask_int("Kaç coin listelensin", DEFAULT_COIN_COUNT, 1, MAX_COIN_COUNT)
            df = fetch_markets(count)
            if df.empty:
                print_failure()
            else:
                df, stats = analyze_markets(df)
                print_markets(df, stats)

        elif choice == "3":
            coin_id = ask_coin_id()
            days = ask_int("Kaç günlük veri", DEFAULT_DAYS, 1, MAX_DAYS)
            df = fetch_market_chart(coin_id, days)
            if df.empty:
                print_failure()
            else:
                print_history(df, analyze_history(df), coin_id, days)

        elif choice == "4":
            run_full_report()

        elif choice == "5":
            print("\nProgramdan çıkılıyor.")
            break

        else:
            print("\nGeçersiz seçim, lütfen 1 ile 5 arasında bir sayı girin.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgramdan çıkılıyor.")
    except Exception:
        log.exception("Beklenmeyen hata")
        raise