"""Profil ↔ ilan eşleştirme. Kural tabanlı; sonuç: KESİN / DİKKAT / None (+ neden)."""
import re
from datetime import date

from .parse import _kucuk

EE_RE = re.compile(r"elektrik\s*(?:[-–/]|ve)?\s*elektronik|elektronik|elektrik|haberleşme|kontrol\s+ve\s+otomasyon|mekatronik", re.I)
MUH_GENEL_RE = re.compile(r"tüm\s+(?:dört\s+yıllık\s+)?mühendislik|dört\s+yıllık\s+tüm\s+mühendislik|mühendislik\s+(?:lisans\s+)?(?:programları|fakülteleri|bölümleri)|ilgili\s+mühendislik|mühendislik\s+lisans", re.I)
GENEL_RE = re.compile(r"herhangi\s+bir\s+(?:lisans|bölüm|fakülte)|tüm\s+lisans|her\s+(?:türlü|bölüm)|bölüm\s+(?:şartı|fark)\s+(?:aranmaz|yok)|fark\s+etmeksizin", re.I)
ASKERI_RE = re.compile(r"muvazzaf|subay|astsubay|komiser\s+yardımcısı|polis\s+(?:memuru|akademisi)|uzman\s+erbaş|sözleşmeli\s+er\b", re.I)
BELIRSIZ_RE = re.compile(r"tablo|ekte|ilan\s+metni|belirtilen\s+(?:lisans|bölüm)|ilgili\s+(?:alan|bölüm)|unvana\s+göre|değişiklik", re.I)
AKADEMIK_RE = re.compile(r"öğretim\s+(?:üyesi|elemanı|görevlisi)|doçent|profesör|akademik\s+personel|araştırma\s+görevlisi|öğr\.\s*üyesi", re.I)
KAPANDI_RE = re.compile(r"başvuru(?:lar)?\s+(?:süresi\s+)?(?:sona\s+erdi|kapandı)|ilan\s+kapandı", re.I)


def _lisans_satiri(s: str):
    ilk = _kucuk(s.split("·")[0]).strip()
    return ilk.startswith("lisans") and not ilk.startswith("lisansüstü")


def degerlendir(ilan: dict, profil: dict, bugun: date = None) -> dict:
    """Dönüş: {sonuc: 'KESIN'|'DIKKAT'|None, neden: str, uyarilar: [..], oncelikli: bool}"""
    bugun = bugun or date.today()
    uy = []
    metin = ilan.get("tam_metin", "")
    flat = re.sub(r"\s+", " ", metin)
    sonuc = lambda s, n: {"sonuc": s, "neden": n, "uyarilar": uy, "oncelikli": oncelikli}

    iller = [i for i in profil.get("oncelikli_iller", [])]
    oncelikli = any(_kucuk(i) in _kucuk(flat) for i in iller)

    # 1) tarih
    if ilan.get("son_basvuru"):
        son = date.fromisoformat(ilan["son_basvuru"])
        if son < bugun:
            return sonuc(None, "başvuru süresi geçmiş")
    else:
        if KAPANDI_RE.search(flat):
            return sonuc(None, "ilan kapanmış")
        if not ilan.get("listede", True):
            return sonuc(None, "tarihi yok ve açık ilan listesinde görünmüyor (eski ilan)")
        uy.append("son başvuru tarihi okunamadı, ilan sayfasından doğrula")

    hariç = [h.lower() for h in profil.get("haric_kadrolar", ["zabıta", "itfaiye", "koruma ve güvenlik", "temizlik", "hizmetli", "şoför", "bekçi", "gassal"])]
    unv = ilan.get("unvanlar", [])
    if hariç and ((unv and all(any(h in _kucuk(u) or h in u.lower() for h in hariç) for u in unv))
                  or any(h in ilan.get("baslik", "").lower() for h in hariç)):
        return sonuc(None, "profildeki hariç kadro türü (zabıta/itfaiye/güvenlik vb.)")

    # 2) akademik / askeri
    ogr = ilan.get("ogrenim", [])
    ist = (ilan.get("istihdam") or "") + " " + (ilan.get("meta") or "")
    if re.search(r"akademik\s+personel", ist, re.I) or AKADEMIK_RE.search(ilan.get("baslik", "")):
        return sonuc(None, "akademik kadro")
    if re.search(r"askeri", ist, re.I) or ASKERI_RE.search(ilan.get("baslik", "")):
        return sonuc(None, "askeri/kolluk kadrosu")

    # 3) öğrenim düzeyi
    if ogr:
        lisans = [o for o in ogr if _lisans_satiri(o)]
        if not lisans:
            return sonuc(None, "lisans düzeyi aranmıyor (ön lisans/lise)")
    else:
        lisans = []
        if not re.search(r"(?<![öÖ]n )(?<!ön\s)lisans", flat, re.I):
            return sonuc(None, "öğrenim bilgisi yok")
        uy.append("öğrenim satırı ayrıştırılamadı, ilan metnini kontrol et")

    # 4) bölüm
    bolumler = [o.split("·", 1)[1].strip() if "·" in o else "" for o in lisans]
    unvanlar = ilan.get("unvanlar", [])
    ee = any(EE_RE.search(b) for b in bolumler) or any(EE_RE.search(u) and re.search(r"müh", u, re.I) for u in unvanlar)
    muh = any(MUH_GENEL_RE.search(b) for b in bolumler) or bool(MUH_GENEL_RE.search(flat)) or \
        any(x.strip().lower() == "mühendislik" for b in bolumler for x in re.split(r"[,/]", b))
    genel = any(GENEL_RE.search(b) for b in bolumler) or bool(GENEL_RE.search(flat))
    ee = ee or bool(re.search(r"elektrik(?:\s*[-–/]|\s+ve)?\s*elektronik\s+müh|elektronik\s+(?:ve\s+haberleşme\s+)?müh|elektrik\s+müh", flat, re.I))
    bos = any(b == "" or BELIRSIZ_RE.search(b) for b in bolumler) and bool(lisans)
    if not lisans and EE_RE.search(flat):
        ee = ee or bool(re.search(r"elektrik\s*(?:[-–/]|ve)?\s*elektronik\s+müh", flat, re.I))

    if not (ee or muh or genel or bos or not lisans):
        return sonuc(None, "bölüm şartı E-E ile uyuşmuyor: " + "; ".join(bolumler)[:80])
    if not ee and (genel or bos) and not muh and not profil.get("herhangi_lisans_ilanlari", True) and not oncelikli:
        return sonuc(None, "bölümsüz/herhangi-lisans ilanı (profilde kapalı)")

    # 5) KPSS
    turler = {f"P{t}" for t in ilan.get("kpss_turleri", [])}
    benim = {t.upper() for t in profil.get("puan_turleri", ["P3"])}
    if ilan.get("kpss_var") and turler:
        if not (turler & benim):
            return sonuc(None, f"KPSS türü uymuyor ({', '.join(sorted(turler))[:40]})")
    elif not ilan.get("kpss_var"):
        uy.append("KPSS aranmıyor (sınav/dosya ile alım)")
    yillar = ilan.get("kpss_yillari", [])
    if yillar and max(yillar) < int(profil.get("kpss_yili", 2026)):
        return sonuc(None, f"KPSS yılı uymuyor ({max(yillar)})")
    p3 = profil.get("p3_puani")
    asg = ilan.get("kpss_asgari", {})
    if p3 and asg.get("3") and float(asg["3"]) > float(p3):
        return sonuc(None, f"P3 asgari puan {asg['3']} > {p3}")
    if asg:
        uy.append("asgari puan: " + ", ".join(f"P{k}≥{int(v) if v == int(v) else v}" for k, v in asg.items()))

    # 6) yaş / cinsiyet
    if ilan.get("yas_siniri"):
        dy = profil.get("dogum_yili")
        if dy and bugun.year - int(dy) >= ilan["yas_siniri"]:
            return sonuc(None, f"yaş sınırı ({ilan['yas_siniri']}) aşılıyor")
        uy.append(f"yaş sınırı: {ilan['yas_siniri']}")
    c = profil.get("cinsiyet")
    if ilan.get("cinsiyet_siniri") and c and _kucuk(c).startswith(ilan["cinsiyet_siniri"][0]) is False:
        return sonuc(None, f"cinsiyet şartı: {ilan['cinsiyet_siniri']}")

    # 7) deneyim / dil / belge
    dene = ilan.get("deneyim_yillari", [])
    kendi = int(profil.get("deneyim_yili", 0) or 0)
    deneyim_sorun = bool(dene) and min(dene) > kendi
    if deneyim_sorun:
        if profil.get("deneyim_gerekiyorsa_gizle"):
            return sonuc(None, f"{min(dene)}+ yıl deneyim isteniyor")
        uy.append(f"deneyim isteniyor: {min(dene)}–{max(dene)} yıl (bazı unvanlarda)" if min(dene) != max(dene) else f"deneyim isteniyor: {dene[0]} yıl")
    if ilan.get("yds") and not profil.get("yds_var"):
        uy.append("YDS/yabancı dil belgesi geçiyor")
    if ilan.get("belgeler"):
        uy.append("belge/sertifika: " + ", ".join(ilan["belgeler"]))

    # 8) sonuç
    kesin_bolum = ee or (muh and not bos) or (genel and not bos)
    if ee or muh:
        neden = "Elektrik-Elektronik / mühendislik bölümü kabul ediliyor"
    elif genel or bos:
        neden = "herhangi bir lisans / bölüm kısıtı yok"
    else:
        neden = "lisans düzeyi"
    ciddi = deneyim_sorun or (bos and not ee) or (not kesin_bolum) or any("okunamadı" in u or "ayrıştırılamadı" in u for u in uy)
    if ilan.get("yds") and not profil.get("yds_var"):
        ciddi = True
    return sonuc("DIKKAT" if ciddi else "KESIN", neden)
