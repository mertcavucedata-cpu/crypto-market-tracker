import os
import time
import random
import requests
from dotenv import load_dotenv

# .env dosyasını aktif etme ve sabit ayarlar (En tepede)
load_dotenv()
API_KEY = os.getenv("COINGECKO_API_KEY")
API_URL = "https://api.coingecko.com/api/v3/"

# İsteklerde kullanılacak sabit headers yapısı
HEADERS = {
    "x-cg-demo-api-key": API_KEY
}

TIMEOUT = 10
MIN_BEKLEME = 1
MAX_BEKLEME = 3


# 1. Fonksiyon: Global Piyasa Verileri (/global) ve Süzgeci
def global_verisini_cek():
    url = API_URL + "global"
    try:
        time.sleep(random.uniform(MIN_BEKLEME, MAX_BEKLEME))
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        
        # HTTP hata kodlarını yakala (Örn: 401 Unauthorized, 429 Rate Limit, 500 Server Error)
        response.raise_for_status()
        
        ham_veri = response.json()
        data = ham_veri.get("data", {})
        
        temiz_global_veri = {
            "Aktif Coin Sayısı": data.get("active_cryptocurrencies"),
            "Toplam Borsa Sayısı": data.get("markets"),
            "Toplam Piyasa Değeri ($)": data.get("total_market_cap", {}).get("usd"),
            "Bitcoin Dominansı (%)": data.get("market_cap_percentage", {}).get("btc"),
            "Piyasa Korku Skoru": data.get("fear_and_greed_index", {}).get("value"),
            "Piyasa Psikolojisi": data.get("fear_and_greed_index", {}).get("sentiment")
        }
        return temiz_global_veri

    except requests.exceptions.HTTPError as err:
        print(f"\n❌ Sunucu Hatası (HTTP): {err}")
    except requests.exceptions.ConnectionError:
        print("\n❌ Bağlantı Hatası: İnternet bağlantınızı kontrol edin.")
    except requests.exceptions.Timeout:
        print("\n❌ Zaman Aşımı: Sunucu çok geç yanıt verdi.")
    except Exception as err:
        print(f"\n❌ Beklenmeyen bir hata oluştu: {err}")
    return None


# 2. Fonksiyon: Piyasa Listesi (/coins/markets) ve Veri Süzgeci
def coin_markets_cek(vs_currency="usd", per_page=5):
    url = API_URL + "coins/markets"
    
    parametreler = {
        "vs_currency": vs_currency,
        "per_page": per_page,
        "order": "market_cap_desc"
    }
    
    try:
        time.sleep(random.uniform(MIN_BEKLEME, MAX_BEKLEME))
        response = requests.get(url, headers=HEADERS, params=parametreler, timeout=TIMEOUT)
        response.raise_for_status()
        
        ham_veri = response.json()
        temiz_liste = []
        
        for coin in ham_veri:
            bilgi = {
                "İsim": coin.get("name"),
                "Sembol": coin.get("symbol", "").upper(),
                "Fiyat ($)": coin.get("current_price"),
                "Piyasa Değeri": coin.get("market_cap"),
                "24s Değişim (%)": coin.get("price_change_percentage_24h")
            }
            temiz_liste.append(bilgi)
            
        return temiz_liste

    except requests.exceptions.HTTPError as err:
        print(f"\n❌ Sunucu Hatası (HTTP): {err}")
    except requests.exceptions.ConnectionError:
        print("\n❌ Bağlantı Hatası: İnternet bağlantınızı kontrol edin.")
    except requests.exceptions.Timeout:
        print("\n❌ Zaman Aşımı: Sunucu çok geç yanıt verdi.")
    except Exception as err:
        print(f"\n❌ Beklenmeyen bir hata oluştu: {err}")
    return []


# 3. Fonksiyon: Geçmiş Grafik Verisi (/coins/{id}/market_chart) ve Süzgeci
def coin_market_chart_cek(coin_id="bitcoin", days="1", vs_currency="usd"):
    url = f"{API_URL}coins/{coin_id}/market_chart"
    
    parametreler = {
        "vs_currency": vs_currency,
        "days": days
    }
    
    try:
        time.sleep(random.uniform(MIN_BEKLEME, MAX_BEKLEME))
        response = requests.get(url, headers=HEADERS, params=parametreler, timeout=TIMEOUT)
        
        # Eğer kullanıcı sistemde olmayan bir coin adı girerse CoinGecko 404 döner
        if response.status_code == 404:
            print(f"\n❌ Hata: '{coin_id}' adında bir coin bulunamadı! Lütfen geçerli bir coin ID'si girin (örn: bitcoin, ethereum).")
            return []
            
        response.raise_for_status()
        
        ham_veri = response.json()
        fiyat_listesi = ham_veri.get("prices", [])
        
        temiz_chart_listesi = []
        for item in fiyat_listesi:
            zaman_damgasi = item[0]
            fiyat = item[1]
            
            temiz_chart_listesi.append({
                "Zaman Damgası": zaman_damgasi,
                "Fiyat ($)": fiyat
            })
            
        return temiz_chart_listesi

    except requests.exceptions.HTTPError as err:
        print(f"\n❌ Sunucu Hatası (HTTP): {err}")
    except requests.exceptions.ConnectionError:
        print("\n❌ Bağlantı Hatası: İnternet bağlantınızı kontrol edin.")
    except requests.exceptions.Timeout:
        print("\n❌ Zaman Aşımı: Sunucu çok geç yanıt verdi.")
    except Exception as err:
        print(f"\n❌ Beklenmeyen bir hata oluştu: {err}")
    return []


# --- KULLANICI ETKİLEŞİM DÖNGÜSÜ (ANA MENÜ) ---
if __name__ == "__main__":
    while True:
        print("\n" + "=" * 40)
        print("     KRİPTO PİYASA TAKİP PROGRAMI")
        print("=" * 40)
        print("1 - Global Piyasa Özetini Göster (/global)")
        print("2 - Popüler Coinleri Listele (/coins/markets)")
        print("3 - Coinin Geçmiş Grafik Verisini Çek (/market_chart)")
        print("4 - Çıkış")
        print("-" * 40)
        
        secim = input("Lütfen yapmak istediğiniz işlemin numarasını girin (1-4): ").strip()
        
        if secim == "1":
            print("\n⏳ Global piyasa verileri çekiliyor, lütfen bekleyin...")
            veri = global_verisini_cek()
            if veri:
                print("\n--- GÜNCEL GLOBAL PİYASA DURUMU ---")
                for anahtar, deger in veri.items():
                    print(f"{anahtar}: {deger}")
                
        elif secim == "2":
            try:
                adet = int(input("Kaç tane coin listelemek istiyorsun? (Örn: 5, 10): "))
            except ValueError:
                adet = 5
                print("⚠️ Geçersiz giriş yapıldı, varsayılan olarak 5 coin listeleniyor.")
                
            print(f"\n⏳ İlk {adet} coinin piyasa verileri çekiliyor...")
            coinler = coin_markets_cek(per_page=adet)
            
            if coinler:
                print(f"\n--- EN POPÜLER İLK {len(coinler)} COİN ---")
                for sira, coin in enumerate(coinler, 1):
                    print(f"{sira}. {coin['İsim']} ({coin['Sembol']})")
                    print(f"   Fiyat: ${coin['Fiyat ($)']}")
                    print(f"   Piyasa Değeri: {coin['Piyasa Değeri']}")
                    print(f"   24s Değişim: %{coin['24s Değişim (%)']}")
                    print("-" * 30)
                
        elif secim == "3":
            coin_adi = input("Hangi coinin geçmiş verisini istiyorsun? (Örn: bitcoin, ethereum, solana): ").strip().lower()
            gun = input("Kaç günlük veri olsun? (Örn: 1, 7, 30): ").strip()
            
            if not coin_adi:
                coin_adi = "bitcoin"
            if not gun:
                gun = "1"
                
            print(f"\n⏳ {coin_adi.capitalize()} için son {gun} günlük grafik verisi çekiliyor...")
            chart_verisi = coin_market_chart_cek(coin_id=coin_adi, days=gun)
            
            if chart_verisi:
                print(f"\n--- {coin_adi.upper()} GEÇMİŞ GRAFİK ÖZETİ ---")
                print(f"Toplam Veri Noktası Sayısı: {len(chart_verisi)}")
                print("İlk 5 Örnek Nokta:")
                for nokta in chart_verisi[:5]:
                    print(f"  Zaman: {nokta['Zaman Damgası']} | Fiyat: ${nokta['Fiyat ($)']}")
                print("...")
            
        elif secim == "4":
            print("\nKripto takip programından çıkılıyor. Bol kazançlar dostum!")
            break
            
        else:
            print("\n❌ Geçersiz bir seçim yaptın! Lütfen 1 ile 4 arasında bir sayı gir.")