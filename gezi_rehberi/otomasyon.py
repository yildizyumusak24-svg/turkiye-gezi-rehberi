import os
import sys
import requests
import time
from pathlib import Path
from dotenv import load_dotenv
from deep_translator import GoogleTranslator

# UTF-8 cikti
sys.stdout.reconfigure(encoding='utf-8')

# .env yukle
load_dotenv(Path(__file__).parent / ".env")

STRAPI_URL       = "http://localhost:1337"
STRAPI_API_TOKEN = os.environ.get("STRAPI_API_TOKEN", "")
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL       = "llama-3.3-70b-versatile"
GORSEL_KLASOR    = "uretilen_gorseller"
os.makedirs(GORSEL_KLASOR, exist_ok=True)

SEHIR_VE_MEKANLAR = [
    {
        "sehir": {"ad": "Istanbul", "ulke": "Turkiye"},
        "mekanlar": [
            {"ad": "Ayasofya",       "puan": 9.5},
            {"ad": "Topkapi Sarayi", "puan": 9.0},
            {"ad": "Kapalicarsi",    "puan": 8.5},
        ]
    },
    {
        "sehir": {"ad": "Kapadokya", "ulke": "Turkiye"},
        "mekanlar": [
            {"ad": "Goreme Acik Hava Muzesi", "puan": 9.3},
            {"ad": "Uchisar Kalesi",           "puan": 8.8},
        ]
    },
    {
        "sehir": {"ad": "Antalya", "ulke": "Turkiye"},
        "mekanlar": [
            {"ad": "Kaleici",       "puan": 8.7},
            {"ad": "Duden Selalesi","puan": 8.4},
        ]
    },
]

def token_al():
    if not STRAPI_API_TOKEN:
        raise Exception("STRAPI_API_TOKEN bos! .env dosyasini kontrol edin.")
    headers = {"Authorization": f"Bearer {STRAPI_API_TOKEN}"}
    r = requests.get(f"{STRAPI_URL}/api/sehirs", headers=headers, timeout=10)
    if r.status_code == 200:
        print("Token gecerli.")
    else:
        raise Exception(f"Token gecersiz! Kod: {r.status_code} - {r.text}")
    return STRAPI_API_TOKEN

def metin_zenginlestir(mekan_adi, sehir_adi):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": GROQ_MODEL,
        "max_tokens": 300,
        "messages": [
            {"role": "system", "content": "Sen bir Turkiye turizm uzmanissin."},
            {"role": "user", "content": f"{sehir_adi} sehrindeki {mekan_adi} hakkinda 3 cumlelik Turkce tanitim yaz."}
        ]
    }
    r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body, timeout=30)
    r.raise_for_status()
    metin = r.json()["choices"][0]["message"]["content"].strip()
    print(f"   Metin uretildi: {mekan_adi}")
    return metin

def ingilizceye_cevir(tr_metin):
    en = GoogleTranslator(source="tr", target="en").translate(tr_metin)
    print("   Ceviri tamamlandi.")
    return en

def gorsel_indir(mekan_adi):
    seed = abs(hash(mekan_adi)) % 1000
    url = f"https://picsum.photos/seed/{seed}/800/600"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    dosya = os.path.join(GORSEL_KLASOR, f"{mekan_adi.replace(' ','_')}.jpg")
    with open(dosya, "wb") as f:
        f.write(r.content)
    print(f"   Gorsel indirildi: {dosya}")
    return dosya

def gorsel_yukle(token, dosya_yolu):
    headers = {"Authorization": f"Bearer {token}"}
    with open(dosya_yolu, "rb") as f:
        files = {"files": (os.path.basename(dosya_yolu), f, "image/jpeg")}
        r = requests.post(f"{STRAPI_URL}/api/upload", headers=headers, files=files, timeout=30)
    r.raise_for_status()
    gid = r.json()[0]["id"]
    print(f"   Gorsel yuklendi ID: {gid}")
    return gid

def sehir_kaydet(token, sehir):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"data": {"ad": sehir["ad"], "ulke": sehir["ulke"]}}
    r = requests.post(f"{STRAPI_URL}/api/sehirs", headers=headers, json=payload, timeout=10)
    r.raise_for_status()
    sid = r.json()["data"]["id"]
    print(f"Sehir kaydedildi: {sehir['ad']} (ID: {sid})")
    return sid

def mekan_kaydet(token, ad, tr, en, puan, gorsel_id, sehir_id):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "data": {
            "ad": ad,
            "aciklama": [{"type": "paragraph", "children": [{"type": "text", "text": tr}]}],
            "yz_aciklama": en,
            "puan": puan,
            "gorsel": gorsel_id,
            "sehir": sehir_id,
        }
    }
    r = requests.post(f"{STRAPI_URL}/api/mekans", headers=headers, json=payload, timeout=10)
    r.raise_for_status()
    mid = r.json()["data"]["id"]
    print(f"   Mekan kaydedildi: {ad} (ID: {mid})")

def main():
    print("=" * 50)
    print("  BIP210 - Gezi Rehberi Otomasyonu")
    print("=" * 50)

    token = token_al()

    for kayit in SEHIR_VE_MEKANLAR:
        sehir_bilgi = kayit["sehir"]
        print(f"\nSehir: {sehir_bilgi['ad']}")
        sehir_id = sehir_kaydet(token, sehir_bilgi)

        for mekan in kayit["mekanlar"]:
            ad = mekan["ad"]
            print(f"\n  Mekan: {ad}")
            try:
                tr  = metin_zenginlestir(ad, sehir_bilgi["ad"])
                en  = ingilizceye_cevir(tr)
                yol = gorsel_indir(ad)
                gid = gorsel_yukle(token, yol)
                mekan_kaydet(token, ad, tr, en, mekan["puan"], gid, sehir_id)
                time.sleep(1)
            except Exception as e:
                print(f"  HATA ({ad}): {e}")

    print("\nTum islemler tamamlandi!")

if __name__ == "__main__":
    main()
