"""Memurjet ilan detay sayfasını ayrıştırır (Astro ile sunucuda üretilmiş statik HTML)."""
import re
from bs4 import BeautifulSoup

from .trdate import TARIH_RE, parse_tarih

ILLER = {s.lower() for s in """Adana Adıyaman Afyonkarahisar Ağrı Aksaray Amasya Ankara Antalya Ardahan Artvin Aydın Balıkesir
Bartın Batman Bayburt Bilecik Bingöl Bitlis Bolu Burdur Bursa Çanakkale Çankırı Çorum Denizli Diyarbakır Düzce Edirne Elazığ
Erzincan Erzurum Eskişehir Gaziantep Giresun Gümüşhane Hakkari Hatay Iğdır Isparta İstanbul İzmir Kahramanmaraş Karabük Karaman
Kars Kastamonu Kayseri Kırıkkale Kırklareli Kırşehir Kilis Kocaeli Konya Kütahya Malatya Manisa Mardin Mersin Muğla Muş Nevşehir
Niğde Ordu Osmaniye Rize Sakarya Samsun Siirt Sinop Sivas Şanlıurfa Şırnak Tekirdağ Tokat Trabzon Tunceli Uşak Van Yalova Yozgat
Zonguldak""".split()}


def _kucuk(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


def metin_cikar(html: str):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "svg", "noscript"]):
        t.decompose()
    h1 = soup.find("h1")
    baslik = h1.get_text(" ", strip=True) if h1 else (soup.title.get_text(strip=True) if soup.title else "")
    unvanlar, kaynak = [], None
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if "kamuilan.sbb.gov.tr" in h and not kaynak:
            kaynak = h
        m = re.search(r"/is-ilanlari/([a-z0-9-]+)$", h)
        if m and not re.search(r"\d", m.group(1)):
            t = a.get_text(" ", strip=True)
            if t and len(t) < 80 and _kucuk(t) not in ILLER and t not in unvanlar and not t.startswith("Nasıl"):
                unvanlar.append(t)
    lines = [l.strip() for l in soup.get_text("\n").split("\n")]
    lines = [l for l in lines if l]
    text = "\n".join(lines)
    for kes in ("Benzer ilanlar", "Memurjet Forum açıldı"):
        i = text.find(kes)
        if i > 0:
            text = text[:i]
    return baslik, text, unvanlar, kaynak


def _tarih(m, bugun=None):
    return parse_tarih(m.group(1), m.group(2), m.group(3), bugun)


def parse_ilan(html: str, url: str, bugun=None) -> dict:
    baslik, text, unvanlar, kaynak = metin_cikar(html)
    flat = re.sub(r"\s+", " ", text)
    d = {"url": url, "baslik": baslik, "unvanlar": unvanlar, "resmi_kaynak": kaynak}

    # --- tarihler ---
    son = None
    eslesmeler = list(re.finditer(r"Son başvuru\s*" + TARIH_RE.pattern, flat, re.I))
    m = next((x for x in eslesmeler if x.group(3)), eslesmeler[0] if eslesmeler else None)  # yıllı olanı tercih et
    if m:
        son = _tarih(m, bugun)
    d["son_basvuru"] = son.isoformat() if son else None
    m = re.search(r"Başlangıç\s*" + TARIH_RE.pattern, flat, re.I)
    bas = _tarih(m, bugun) if m else None
    d["baslangic"] = bas.isoformat() if bas else None
    m = re.search(r"Son başvuru\s*\d{1,2}\s+\w+(?:\s+\d{4})?\s*,?\s*(\d{1,2}[:.]\d{2})", flat)
    d["son_saat"] = m.group(1).replace(".", ":") if m else None

    # --- kurum / istihdam / yer ---
    m = re.search(r"(Kadrolu memur|Sözleşmeli(?: personel)?|Sürekli işçi|İşçi|Akademik)[^\n]{0,80}", text)
    d["istihdam"] = m.group(1) if m else None
    m = re.search(r"Çalışma yeri\s*\n?([^\n]+)", text)
    d["yer"] = m.group(1).strip() if m else None
    m = re.search(r"Kadro\s*\n?(\d+)\s*kişi", text)
    d["kadro"] = int(m.group(1)) if m else None

    # --- öğrenim ---
    ogr = []
    for m in re.finditer(r"Öğrenim:\s*(.{1,160}?)(?=\s*(?:✓|Öğrenim:|Türk\s+vatandaşı|Kamu\s+haklarından|Pozisyona\s+özel|Tüm\s+adaylar|$))", flat):
        ogr.append(re.sub(r"\s*·\s*", " · ", m.group(1)).strip())
    d["ogrenim"] = list(dict.fromkeys(ogr))

    # --- KPSS ---
    turler = sorted({int(x) for x in re.findall(r"\bP(\d{1,2})\b", flat)})
    d["kpss_turleri"] = turler
    puanlar = {}
    for tur, puan in re.findall(r"P(\d{1,2})\s*\(\s*≥\s*(\d{2,3}(?:[.,]\d+)?)", flat):
        puanlar.setdefault(int(tur), float(puan.replace(",", ".")))
    for tur, puan in re.findall(r"P(\d{1,2})\s*puan\s*türünden\s*en\s*az\s*(\d{2,3}(?:[.,]\d+)?)", flat, re.I):
        puanlar.setdefault(int(tur), float(puan.replace(",", ".")))
    d["kpss_asgari"] = {str(k): v for k, v in puanlar.items()}
    yillar = set()
    for m in re.finditer(r"KPSS", flat):
        pencere = flat[max(0, m.start() - 50): m.end() + 50]
        yillar.update(int(y) for y in re.findall(r"\b(20[12]\d)\b", pencere))
    d["kpss_yillari"] = sorted(yillar)
    d["kpss_var"] = "KPSS" in flat

    # --- deneyim / yaş / belge / dil ---
    deneyim = []
    for m in re.finditer(r"(\d{1,2})\s*(?:\([^)]*\)\s*)?yıl[^.\n]{0,70}?(?:deneyim|tecrübe)|(?:deneyim|tecrübe)[^.\n]{0,50}?(\d{1,2})\s*yıl", flat, re.I):
        deneyim.append(int(m.group(1) or m.group(2)))
    d["deneyim_yillari"] = sorted(set(deneyim))
    yas = [int(x) for x in re.findall(r"(\d{2})\s*yaş[ıi]n[ıi]\s*(?:doldurmamış|geçmemiş)", flat, re.I)]
    d["yas_siniri"] = min(yas) if yas else None
    d["yds"] = bool(re.search(r"\bYDS\b|e-YDS|yabancı dil", flat, re.I))
    belge = []
    for anahtar, ad in [(r"silahlı\s+(?:özel\s+)?güvenlik", "silahlı güvenlik belgesi"), (r"sürücü belgesi", "sürücü belgesi"),
                        (r"sertifika", "sertifika"), (r"SGK\s+(?:hizmet\s+)?döküm", "SGK dökümü")]:
        if re.search(anahtar, flat, re.I):
            belge.append(ad)
    d["belgeler"] = belge
    m = re.search(r"\b(Erkek|Kadın)\s+(?:olmak|adaylar\s+(?:başvurabilir|alınacak))", flat)
    d["cinsiyet_siniri"] = _kucuk(m.group(1)) if m else None

    # --- başvuru yolu ---
    m = re.search(r"Nasıl başvurulur\?\s*\n(.*?)(?:\nKaynak:|\Z)", text, re.S)
    yol = ""
    if m:
        adaylar = [l for l in m.group(1).split("\n") if not re.match(r"^(Başlangıç|Son başvuru|Başvuru Saati|\d)", l)]
        yol = " ".join(adaylar[:2])
    d["basvuru_yolu"] = yol[:200] or None
    d["tam_metin"] = text
    return d
