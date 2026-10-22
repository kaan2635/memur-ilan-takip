"""Günlük akış: keşfet → indir → ayrıştır → eşleştir → yeni olanları bildir.

Kullanım:
  python -m src.main                 # normal günlük çalışma
  python -m src.main --url <ilan>    # tek ilanı ayrıştır + değerlendir (hata ayıklama)
  python -m src.main --kuru          # bildirim/dosya yazma yok
"""
import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from . import fetch, match, notify, parse, rapor, sayfa

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITEMAP_LIMIT = int(os.environ.get("SITEMAP_LIMIT", "120"))


def bugun_tr():
    return datetime.now(ZoneInfo("Europe/Istanbul")).date()


def yukle(p, varsayilan):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return varsayilan


def isle(s, url, profil, bugun):
    html = fetch.get(s, url)
    if not html:
        return url, None
    ilan = parse.parse_ilan(html, url, bugun)
    ilan["degerlendirme"] = match.degerlendir(ilan, profil, bugun)
    ilan.pop("tam_metin", None)
    time.sleep(0.3)
    return url, ilan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url")
    ap.add_argument("--kuru", action="store_true")
    a = ap.parse_args()
    profil = yaml.safe_load((ROOT / "profile.yml").read_text(encoding="utf-8"))
    bugun = bugun_tr()
    s = fetch.session()

    if a.url:
        html = fetch.get(s, a.url)
        ilan = parse.parse_ilan(html, a.url, bugun)
        ilan["degerlendirme"] = match.degerlendir(ilan, profil, bugun)
        ilan_kisa = {k: v for k, v in ilan.items() if k != "tam_metin"}
        print(json.dumps(ilan_kisa, ensure_ascii=False, indent=2, default=str))
        return

    state = yukle(DATA / "state.json", {})   # url -> {ilk_gorulme, son_basvuru, sonuc, bildirilen, hatirlatilan}
    liste = fetch.liste_kesfet(s)
    sitemap = fetch.sitemap_kesfet(s)
    print(f"liste: {len(liste)} ilan, sitemap: {len(sitemap)} ilan, state: {len(state)}")

    # İşlenecekler: listedeki tüm açık ilanlar + state'te açık görünenler + sitemap'ten hiç görülmemiş (sınırlı)
    islenecek = set(liste)
    for u, v in state.items():
        if not v.get("son_basvuru") or v["son_basvuru"] >= bugun.isoformat():
            islenecek.add(u)
    gorulmemis = sorted((u for u in sitemap if u not in state and u not in islenecek), key=lambda u: sitemap[u], reverse=True)
    islenecek |= set(gorulmemis[:SITEMAP_LIMIT])
    print(f"işlenecek: {len(islenecek)} (sitemap'ten {min(len(gorulmemis), SITEMAP_LIMIT)} yeni)")

    ilanlar, basarisiz = {}, 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        for url, ilan in ex.map(lambda u: isle(s, u, profil, bugun), sorted(islenecek)):
            if ilan is None:
                basarisiz += 1
            else:
                ilanlar[url] = ilan
    print(f"indirilen: {len(ilanlar)}, başarısız: {basarisiz}")
    if not ilanlar and basarisiz:
        raise SystemExit("Hiç ilan indirilemedi — site engelliyor olabilir. Logları kontrol et.")

    yeni, yaklasan = [], []
    for url, ilan in ilanlar.items():
        d = ilan["degerlendirme"]
        st = state.setdefault(url, {"ilk_gorulme": bugun.isoformat(), "bildirilen": False, "hatirlatilan": False})
        st["son_basvuru"] = ilan.get("son_basvuru")
        st["sonuc"] = d["sonuc"]
        st["baslik"] = ilan.get("baslik")
        if d["sonuc"] and not st["bildirilen"]:
            yeni.append(ilan)
            st["bildirilen"] = True
        if d["sonuc"] and ilan.get("son_basvuru") and not st["hatirlatilan"]:
            kalan = (date.fromisoformat(ilan["son_basvuru"]) - bugun).days
            if 0 <= kalan <= int(profil.get("son_gun_uyari", 3)) and ilan not in yeni:
                yaklasan.append(ilan)
                st["hatirlatilan"] = True

    acik = [i for i in ilanlar.values() if i["degerlendirme"]["sonuc"]]
    # state'te olup bu sefer işlenmeyen (süresi dolmuş) kayıtları şişirmemek için 120 günden eskileri at
    for u in [u for u, v in state.items()
              if v.get("son_basvuru") and (bugun - date.fromisoformat(v["son_basvuru"])).days > 120]:
        state.pop(u)

    print(f"uygun/kontrol: {len(acik)}, yeni: {len(yeni)}, son gün yaklaşan: {len(yaklasan)}")
    if a.kuru:
        print(rapor.markdown(acik, bugun))
        return

    DATA.mkdir(exist_ok=True)
    (DATA / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    (DATA / "acik_ilanlar.json").write_text(json.dumps(rapor.sirala(acik), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (ROOT / "ACIK_ILANLAR.md").write_text(rapor.markdown(acik, bugun), encoding="utf-8")
    # GitHub Pages (Source: main / root) bu dosyayı README yerine site olarak sunar
    (ROOT / "index.html").write_text(sayfa.uret(rapor.sirala(acik), bugun), encoding="utf-8")

    # Bildirim metinleri (workflow bunları issue olarak açar)
    out = ROOT / "bildirim.md"
    if yeni or yaklasan:
        parca = [f"# {bugun.strftime('%d.%m.%Y')} — {len(yeni)} yeni, {len(yaklasan)} son günü yaklaşan ilan", ""]
        if yeni:
            parca += ["## 🆕 Yeni ilanlar", ""] + [rapor.satir(i, bugun) + "\n" for i in rapor.sirala(yeni)]
        if yaklasan:
            parca += ["## ⏰ Son günü yaklaşanlar", ""] + [rapor.satir(i, bugun) + "\n" for i in rapor.sirala(yaklasan)]
        parca += ["---", f"Tüm açık liste: ACIK_ILANLAR.md ({len(acik)} ilan). Başvurular e-Devlet/Kariyer Kapısı üzerinden senin tarafından yapılır."]
        metin = "\n".join(parca)
        out.write_text(metin, encoding="utf-8")
        ilk = rapor.sirala(yeni or yaklasan)[0]
        ozet = "\n".join(rapor.satir(i, bugun, md=False) for i in rapor.sirala(yeni + yaklasan)[:6])
        notify.ntfy(f"Memur ilanı: {len(yeni)} yeni, {len(yaklasan)} son gün", ozet, ilk["url"],
                    "high" if any(i["degerlendirme"]["sonuc"] == "KESIN" for i in yeni + yaklasan) else "default")
        notify.telegram(f"Memur ilanı takip — {len(yeni)} yeni, {len(yaklasan)} son gün yaklaşan\n\n" + ozet)
    elif out.exists():
        out.unlink()
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"bildirim={'true' if (yeni or yaklasan) else 'false'}\nyeni={len(yeni)}\nyaklasan={len(yaklasan)}\n")


if __name__ == "__main__":
    main()
