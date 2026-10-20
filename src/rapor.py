"""Mesaj / Markdown üretimi."""
from datetime import date

ETIKET = {"KESIN": "✅ Uygun", "DIKKAT": "⚠️ Kontrol et"}


def kalan(ilan, bugun):
    if not ilan.get("son_basvuru"):
        return "tarih ?"
    g = (date.fromisoformat(ilan["son_basvuru"]) - bugun).days
    s = date.fromisoformat(ilan["son_basvuru"]).strftime("%d.%m.%Y")
    saat = f" {ilan['son_saat']}" if ilan.get("son_saat") else ""
    return f"{s}{saat} (bugün)" if g == 0 else f"{s}{saat} ({g} gün kaldı)"


def satir(ilan, bugun, md=True):
    d = ilan["degerlendirme"]
    pin = "📍" if d["oncelikli"] else ""
    basla = ilan.get("baslik") or ilan["url"]
    if ilan.get("baslangic") and date.fromisoformat(ilan["baslangic"]) > bugun:
        bas = f" · başvuru {date.fromisoformat(ilan['baslangic']).strftime('%d.%m')}'de açılıyor"
    else:
        bas = ""
    unv = ", ".join(ilan.get("unvanlar", [])[:4])
    parcalar = [
        f"{ETIKET[d['sonuc']]} {pin} **{basla}**" if md else f"{ETIKET[d['sonuc']]} {pin} {basla}",
        f"   Son başvuru: {kalan(ilan, bugun)}{bas}",
    ]
    if unv:
        parcalar.append(f"   Unvanlar: {unv}")
    parcalar.append(f"   Yer: {ilan.get('yer') or '?'} · {ilan.get('istihdam') or ''} · {d['neden']}")
    for u in d["uyarilar"]:
        parcalar.append(f"   • {u}")
    if ilan.get("basvuru_yolu"):
        parcalar.append(f"   Başvuru: {ilan['basvuru_yolu']}")
    parcalar.append(f"   {ilan['url']}")
    return "\n".join(parcalar)


def sirala(ilanlar):
    return sorted(ilanlar, key=lambda i: (not i["degerlendirme"]["oncelikli"], i["degerlendirme"]["sonuc"] != "KESIN",
                                          i.get("son_basvuru") or "9999"))


def markdown(ilanlar, bugun):
    out = [f"# Açık ilanlar — {bugun.strftime('%d.%m.%Y')}", "",
           f"Profil: E-E lisans · KPSS 2026. Toplam **{len(ilanlar)}** uygun/kontrol edilecek ilan.", ""]
    for i in sirala(ilanlar):
        out += [satir(i, bugun), ""]
    return "\n".join(out)
