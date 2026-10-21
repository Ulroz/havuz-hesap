#!/usr/bin/env python3
"""81 il için aylık iklim verisini kaynaklardan çeker ve HTML'deki CITIES tablosunu günceller.

Kaynaklar
  - İstasyon konumu ve rakımı : MGM servis.mgm.gov.tr (il merkez istasyonu)
  - Gündüz / gece sıcaklığı   : MGM İllere Ait Mevsim Normalleri (1991-2020),
                                ortalama en yüksek / ortalama en düşük sıcaklık; normal tablosu
                                yayımlanmamış illerde MGM genel istatistik verisi (uzun dönem)
  - Çiy noktası, rüzgar (10 m): PVGIS 5.3 tipik meteorolojik yıl (TMY, ERA5, 2005-2023); saatlik buhar basıncının
                                ve rüzgarın aylık ortalaması, ortalama buhar basıncından çiy noktası
  - Güneş ışınımı (GHI)       : PVGIS 5.3 MRcalc, PVGIS-SARAH3 (2005-2023), yatay düzlem aylık ışınım

Kullanım
  python3 tools/iklim_verisi_guncelle.py --cache <önbellek klasörü> [--html Mekensis_Havuz_Isil_Yuk_Analizi.html]

Ham yanıtlar önbellek klasörüne kaydedilir; tekrar çalıştırmada ağa çıkılmaz.
"""
import argparse
import calendar
import html
import json
import math
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
          "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

NORMALS_PERIOD = (1991, 2020)
PVGIS_PERIOD = (2005, 2023)
QC_CONSTANT_HOURS = 24

# MGM sayfa parametresi (m=) il adından farklı olanlar
MGM_PAGE_NAME = {"Mersin": "ICEL"}

UA = {"User-Agent": "Mekensis-Havuz-Hesap iklim verisi betigi"}


# Magnus bağıntısı (programdaki getSatVaporPressure ile aynı sabitler), hPa
def sat_vapor_pressure(t):
    return 6.112 * math.exp(17.67 * t / (t + 243.5))


def dew_point(p_vapor):
    g = math.log(p_vapor / 6.112)
    return 243.5 * g / (17.67 - g)


def ascii_upper(name):
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return unicodedata.normalize("NFKD", name.translate(tr)).encode("ascii", "ignore").decode().upper()


def fetch(url, cache_path, headers=None, retries=5):
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return f.read()
    delay = 5
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={**UA, **(headers or {})})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read().decode("utf-8")
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(body)
            time.sleep(1)
            return body
        except Exception as e:  # ağ hatası / 429: bekleyip tekrar dene
            if attempt == retries - 1:
                raise
            print(f"  tekrar deneniyor ({e}) ...", file=sys.stderr)
            time.sleep(delay)
            delay *= 2


def mgm_stations(cache):
    body = fetch("https://servis.mgm.gov.tr/web/merkezler/iller",
                 os.path.join(cache, "mgm_iller.json"),
                 headers={"Origin": "https://www.mgm.gov.tr"})
    return {s["il"]: s for s in json.loads(body)}


def _mgm_page_lines(kind, page, cache):
    body = fetch(f"https://www.mgm.gov.tr/veridegerlendirme/il-ve-ilceler-istatistik.aspx?k={kind}&m={page}",
                 os.path.join(cache, f"mgm_{kind}_{page}.html"))
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S)
    return [l.strip() for l in html.unescape(re.sub(r"<[^>]+>", "\n", text)).split("\n") if l.strip()]


def mgm_temperatures(il, cache):
    """Ortalama en yüksek / en düşük sıcaklık. Önce 1991-2020 normalleri (k=H); tablo yoksa
    MGM genel istatistik sayfası (k=A, uzun dönem) kullanılır ve dönemi kaydedilir."""
    page = MGM_PAGE_NAME.get(il, ascii_upper(il))
    for kind in ("H", "A"):
        lines = _mgm_page_lines(kind, page, cache)
        if "Ortalama En Yüksek Sıcaklık (°C)" not in lines:
            continue

        def row(label):
            i = lines.index(label)
            return [float(v.replace(",", ".")) for v in lines[i + 1:i + 13]]

        if kind == "H":
            period = f"{NORMALS_PERIOD[0]}-{NORMALS_PERIOD[1]}"
        else:
            m = next(re.search(r"(\d{4})\s*-\s*(\d{4})", l) for l in lines if l.startswith("Ölçüm Periyodu"))
            period = f"{m.group(1)}-{m.group(2)}"
        return {"tMax": row("Ortalama En Yüksek Sıcaklık (°C)"),
                "tMin": row("Ortalama En Düşük Sıcaklık (°C)"),
                "period": period}
    raise ValueError(f"{il}: MGM sıcaklık tablosu bulunamadı")


def pvgis_tmy_monthly(key, lat, lon, cache):
    """PVGIS tipik meteorolojik yıl (ERA5 + SARAH3, 2005-2023): saatlik buhar basıncı ve rüzgarın aylık ortalaması.

    Nem, saatlik sıcaklık ve bağıl nemden buhar basıncına çevrilerek ortalanır; aylık ortalama bağıl nem,
    farklı kaynaktan gelen (MGM) sıcaklıklarla birleştirildiğinde buhar basıncını yanlış verir."""
    q = urllib.parse.urlencode({"lat": lat, "lon": lon, "outputformat": "json"})
    data = json.loads(fetch(f"https://re.jrc.ec.europa.eu/api/v5_3/tmy?{q}",
                            os.path.join(cache, f"tmy_{key}.json")))
    hours = data["outputs"]["tmy_hourly"]
    # Veri kalite kontrolü: rüzgarın 24 saat ve daha uzun süre aynı kaldığı bloklar bozuk kabul edilir
    # (ör. İstanbul Aralık 2017: 37,79 m/s ve %5 nem, Tekirdağ Aralık 2014: 0 m/s) ve dışarıda bırakılır.
    bad = set()
    i = 0
    while i < len(hours):
        j = i
        while j + 1 < len(hours) and hours[j + 1]["WS10m"] == hours[i]["WS10m"]:
            j += 1
        if j - i + 1 >= QC_CONSTANT_HOURS:
            bad.update(range(i, j + 1))
        i = j + 1
    if bad:
        print(f"  {key}: {len(bad)} saatlik bozuk TMY verisi dışarıda bırakıldı", file=sys.stderr)

    sums = {k: [0.0] * 12 for k in ("pv", "wind")}
    counts = [0] * 12
    for idx, h in enumerate(hours):
        if idx in bad:
            continue
        m = int(h["time(UTC)"][4:6]) - 1
        sums["pv"][m] += h["RH"] / 100.0 * sat_vapor_pressure(h["T2m"])
        sums["wind"][m] += h["WS10m"]
        counts[m] += 1
    return ({k: [v[m] / counts[m] for m in range(12)] for k, v in sums.items()},
            data["inputs"]["location"]["elevation"], len(bad))


def pvgis_ghi_daily(key, lat, lon, cache):
    y0, y1 = PVGIS_PERIOD
    q = urllib.parse.urlencode({"lat": lat, "lon": lon, "horirrad": 1, "outputformat": "json",
                                "startyear": y0, "endyear": y1, "raddatabase": "PVGIS-SARAH3"})
    data = json.loads(fetch(f"https://re.jrc.ec.europa.eu/api/v5_3/MRcalc?{q}",
                            os.path.join(cache, f"pvgis_{key}.json")))
    days = [[] for _ in range(12)]
    for r in data["outputs"]["monthly"]:
        m = r["month"] - 1
        days[m].append(r["H(h)_m"] / calendar.monthrange(r["year"], r["month"])[1])
    return [sum(v) / len(v) for v in days]  # kWh/m²·gün


def existing_keys(html_text):
    m = re.search(r"^\s*const CITIES = (\{.*\});\s*$", html_text, flags=re.M)
    return {v["name"]: k for k, v in json.loads(m.group(1)).items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--html", default="Mekensis_Havuz_Isil_Yuk_Analizi.html")
    ap.add_argument("--json-out", help="Üretilen veriyi ayrıca JSON olarak kaydet")
    args = ap.parse_args()
    os.makedirs(args.cache, exist_ok=True)

    with open(args.html, encoding="utf-8") as f:
        page = f.read()
    keys = existing_keys(page)
    stations = mgm_stations(args.cache)
    missing = set(keys) ^ set(stations)
    if missing:
        sys.exit(f"İl adları eşleşmedi: {sorted(missing)}")

    cities = {}
    for name in sorted(keys, key=lambda n: keys[n]):
        key, st = keys[name], stations[name]
        lat, lon = round(st["enlem"], 4), round(st["boylam"], 4)
        print(f"{name} ...", file=sys.stderr)
        norm = mgm_temperatures(name, args.cache)
        tmy, dem_elev, qc_hours = pvgis_tmy_monthly(key, lat, lon, args.cache)
        ghi = pvgis_ghi_daily(key, lat, lon, args.cache)

        # MGM servisinde rakımı 0 görünen istasyonlarda (eksik kayıt) PVGIS'in DEM rakımı kullanılır
        alt = st["yukseklik"]
        alt_src = "MGM"
        if not alt and dem_elev is not None and dem_elev > 15:
            alt, alt_src = int(round(dem_elev)), "DEM"

        cities[key] = {
            "name": name,
            "refAlt": alt,
            "lat": lat, "lon": lon,
            "station": st["sondurumIstNo"],
            "altSrc": alt_src,
            "tPeriod": norm["period"],
            "qcHours": qc_hours,
            "months": [{
                "m": MONTHS[i],
                "tDay": norm["tMax"][i],
                "tNight": norm["tMin"][i],
                "ghi": round(ghi[i], 2),
                "wind": round(tmy["wind"][i], 1),
                "td": round(dew_point(tmy["pv"][i]), 1),
            } for i in range(12)],
        }

    line = "    const CITIES = " + json.dumps(cities, ensure_ascii=False, separators=(", ", ": ")) + ";"
    new_page, n = re.subn(r"^\s*const CITIES = \{.*\};\s*$", lambda _: line, page, count=1, flags=re.M)
    assert n == 1
    with open(args.html, "w", encoding="utf-8") as f:
        f.write(new_page)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(cities, f, ensure_ascii=False, indent=1)
    print(f"{len(cities)} il güncellendi.", file=sys.stderr)


if __name__ == "__main__":
    main()
