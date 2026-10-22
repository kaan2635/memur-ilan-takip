"""Memurjet ilan detay sayfasını ayrıştırır (Astro ile sunucuda üretilmiş statik HTML)."""
import re
from bs4 import BeautifulSoup

from .trdate import TARIH_RE, parse_tarih

AY = "Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık"

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
    unvanlar, kaynak, cipler_bitti = [], None, False
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if "kamuilan.sbb.gov.tr" in h and not kaynak:
            kaynak = h
        m = re.search(r"/is-ilanlari/([a-z0-9-]+)$", h)
        if m and not re.search(r"\d", m.group(1)) and not cipler_bitti:
            t = a.get_text(" ", strip=True)
            if re.search(r"ilanları$", t):      # bundan sonrası etiket / benzer ilan bağlantıları
                cipler_bitti = True
                continue
            if t and len(t) < 80 and _kucuk(t) not in ILLER and t not in unvanlar:
                unvanlar.append(t)
    lines = [l.strip() for l in soup.get_text("\n").split("\n")]
    lines = [l for l in lines if l]
    text = "\n".join(lines)
    for kes in ("Benzer ilanlar", "Memurjet Forum açıldı"):
        i = text.find(kes)
        if i > 0:
            text = text[:i]
    meta = ""   # başlığın üstündeki özet: "Kadrolu memur · Sözlü sınav · Şahsen / Posta"
    ls = text.split("\n")
    for i, l in enumerate(ls):
        if l == baslik and i > 0 and " · " in ls[i - 1]:
            meta = ls[i - 1]
            break
    return baslik, text, unvanlar, kaynak, meta


def _tarih(m, bugun=None):
    return parse_tarih(m.group(1), m.group(2), m.group(3), bugun)


def parse_ilan(html: str, url: str, bugun=None) -> dict:
    baslik, text, unvanlar, kaynak, meta = metin_cikar(html)
    flat = re.sub(r"\s+", " ", text)
    d = {"url": url, "baslik": baslik, "unvanlar": unvanlar, "resmi_kaynak": kaynak, "meta": meta}

    # --- tarihler ---
    son = None
    eslesmeler = list(re.finditer(r"Son başvuru\s*" + TARIH_RE.pattern, flat, re.I))
    m = next((x for x in eslesmeler if x.group(3)), eslesmeler[0] if eslesmeler else None)  # yıllı olanı tercih et
    if m:
        son = _tarih(m, bugun)
    d["son_basvuru"] = son.isoformat() if son else None
    m = re.search(r"Başlangıç\s*" + TARIH_RE.pattern, flat, re.I)
    bas = _tarih(m, bugun) if m else None
    if not bas:   # "Başvuru tarihleri 12–26 Ekim" veya "12 Ekim – 3 Kasım"
        m = re.search(r"Başvuru tarihleri\s*(\d{1,2})\s*(?:(" + AY + r")\s*)?[–-]\s*\d{1,2}\s*(" + AY + r")", flat, re.I)
        if m:
            bas = parse_tarih(m.group(1), m.group(2) or m.group(3), None, bugun)
            if bas and son and bas > son:
                bas = bas.replace(year=bas.year - 1)
    d["baslangic"] = bas.isoformat() if bas else None
    m = re.search(r"Son başvuru\s*\d{1,2}\s+\w+(?:\s+\d{4})?\s*,?\s*(\d{1,2}[:.]\d{2})", flat)
    d["son_saat"] = m.group(1).replace(".", ":") if m else None

    # --- istihdam / sınav / başvuru yolu (başlık altındaki özet satır) ---
    segs = [x.strip() for x in meta.split(" · ")] if meta else []
    d["istihdam"] = segs[0] if segs else None
    d["sinav"] = segs[1] if len(segs) > 1 else None
    d["basvuru_yolu"] = segs[2] if len(segs) > 2 else None
    if not d["istihdam"]:
        m = re.search(r"(Kadrolu memur|Sözleşmeli(?: personel)?|Sürekli işçi|İşçi|Akademik personel)", text)
        d["istihdam"] = m.group(1) if m else None

    # --- yer / kadro ---
    m = re.search(r"\nÇalışma yeri\n(.*?)\n(?:KPSS|İstihdam|Çalışma şekli|Kadro|Pozisyonlar)", text, re.S)
    d["yer"] = re.sub(r"\s*,\s*", ", ", re.sub(r"\n+", " ", m.group(1))).strip(" ,") if m else None
    m = re.search(r"Kadro\s*\n?(\d+)\s*kişi", text)
    d["kadro"] = int(m.group(1)) if m else None

    # --- öğrenim (tek satır: "Öğrenim: Lisans · bölümler") ---
    ogr = [re.sub(r"\s*·\s*", " · ", l.split(":", 1)[1]).strip() for l in text.split("\n") if l.startswith("Öğrenim:")]
    d["ogrenim"] = list(dict.fromkeys(ogr))

    # --- KPSS: başlık bloğu "P1 · P2 · P3 (≥ 75)" ya da "P3 (≥ 70)" ---
    m = re.search(r"\nKPSS\n(.*?)\n(?:İstihdam|Çalışma şekli|Çalışma yeri|Kadro|Pozisyonlar)", text, re.S)
    kb = re.sub(r"\s+", " ", m.group(1)) if m else ""
    puanlar, bekleyen, turler = {}, [], set()
    for tok in re.finditer(r"P(\d{1,2})|≥\s*(\d{2,3}(?:[.,]\d+)?)", kb):
        if tok.group(1):
            bekleyen.append(int(tok.group(1)))
            turler.add(int(tok.group(1)))
        else:
            for t in bekleyen:
                puanlar.setdefault(t, float(tok.group(2).replace(",", ".")))
            bekleyen = []
    if not turler:   # başlık bloğu yoksa tüm metinden topla
        turler = {int(x) for x in re.findall(r"\bP(\d{1,2})\b", flat)}
        for tur, puan in re.findall(r"P(\d{1,2})\s*(?:\(\s*)?(?:≥|puan\s*türünden\s*en\s*az)\s*(\d{2,3}(?:[.,]\d+)?)", flat, re.I):
            puanlar.setdefault(int(tur), float(puan.replace(",", ".")))
    d["kpss_turleri"] = sorted(turler)
    d["kpss_asgari"] = {str(k): v for k, v in puanlar.items()}
    yillar = set()
    for mm in re.finditer(r"KPSS", flat):
        pencere = flat[max(0, mm.start() - 50): mm.end() + 50]
        yillar.update(int(y) for y in re.findall(r"\b(20[12]\d)\b", pencere))
    d["kpss_yillari"] = sorted(yillar)
    d["kpss_var"] = bool(kb) or "KPSS" in meta or "KPSS" in flat

    # --- deneyim / yaş / belge / dil ---
    deneyim = []
    for mm in re.finditer(r"(\d{1,2})\s*(?:\([^)]*\)\s*)?yıl[^.\n]{0,70}?(?:deneyim|tecrübe)|(?:deneyim|tecrübe)[^.\n]{0,50}?(\d{1,2})\s*yıl", flat, re.I):
        deneyim.append(int(mm.group(1) or mm.group(2)))
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
    mm = re.search(r"\b(Erkek|Kadın)\s+(?:olmak|adaylar\s+(?:başvurabilir|alınacak))", flat)
    d["cinsiyet_siniri"] = _kucuk(mm.group(1)) if mm else None
    d["tam_metin"] = text
    return d
