"""Türkçe tarih yardımcıları."""
import re
from datetime import date

AYLAR = {"ocak": 1, "şubat": 2, "subat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "mayis": 5,
         "haziran": 6, "temmuz": 7, "ağustos": 8, "agustos": 8, "eylül": 9, "eylul": 9,
         "ekim": 10, "kasım": 11, "kasim": 11, "aralık": 12, "aralik": 12}
KISA = {"oca": 1, "şub": 2, "sub": 2, "mar": 3, "nis": 4, "may": 5, "haz": 6, "tem": 7,
        "ağu": 8, "agu": 8, "eyl": 9, "eki": 10, "kas": 11, "ara": 12}


def ay_no(s: str):
    s = s.lower().replace("İ", "i").replace("I", "ı")
    return AYLAR.get(s) or KISA.get(s[:3])


def parse_tarih(gun, ay, yil=None, bugun=None):
    """'19', 'Kasım', 2026 -> date. Yıl yoksa bugüne göre en yakın makul yılı seçer."""
    m = ay_no(ay)
    if not m:
        return None
    bugun = bugun or date.today()
    try:
        if yil:
            return date(int(yil), m, int(gun))
        d = date(bugun.year, m, int(gun))
        # yıl yoksa: 6 aydan fazla geçmişte kalıyorsa gelecek yıl say
        if (bugun - d).days > 180:
            d = date(bugun.year + 1, m, int(gun))
        return d
    except ValueError:
        return None


TARIH_RE = re.compile(r"(\d{1,2})\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s*(\d{4})?", re.I)
