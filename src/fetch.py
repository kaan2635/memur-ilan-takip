"""Ağ katmanı: liste sayfaları + sitemap ile ilan keşfi, detay sayfası indirme."""
import re
import time
import requests

BASE = "https://www.memurjet.com"
UA = "Mozilla/5.0 (compatible; memur-ilan-takip/1.0; kisisel kullanim)"
ILAN_RE = re.compile(r'(?:https://www\.memurjet\.com)?(/is-ilanlari/[a-z0-9-]*\d[a-z0-9-]*)(?=["\'?#<\s]|$)')


def session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9"})
    return s


def get(s, url, tries=3, timeout=30):
    for i in range(tries):
        try:
            r = s.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.text
            if r.status_code in (404, 410):
                return None
        except requests.RequestException:
            pass
        time.sleep(1.5 * (i + 1))
    return None


def linkler(html: str):
    return {BASE + m for m in ILAN_RE.findall(html or "")}


def liste_kesfet(s, max_sayfa=20, bekle=0.4):
    """Liste sayfalarından açık ilan URL'leri. ?sayfa=N, N*10'a kadar listenin son 10 kartını verir."""
    bulunan = set()
    ek = ["/is-ilanlari/kahramanmaras", "/is-ilanlari?ogrenim=lisans", "/is-ilanlari?kpss=p3", "/is-ilanlari"]
    for yol in ek:
        bulunan |= linkler(get(s, BASE + yol))
        time.sleep(bekle)
    bos = 0
    for n in range(1, max_sayfa + 1):
        yeni = linkler(get(s, f"{BASE}/is-ilanlari?sayfa={n}")) - bulunan
        bulunan |= yeni
        bos = 0 if yeni else bos + 1
        if bos >= 2:
            break
        time.sleep(bekle)
    return bulunan


def sitemap_kesfet(s):
    """Sitemap'teki tüm ilan URL'leri {url: lastmod}."""
    xml = get(s, BASE + "/sitemap-dinamik.xml") or ""
    sonuc = {}
    for loc, lm in re.findall(r"<loc>(https://www\.memurjet\.com/is-ilanlari/[^<]*\d[^<]*)</loc>\s*<lastmod>([^<]*)</lastmod>", xml):
        sonuc[loc] = lm
    return sonuc
