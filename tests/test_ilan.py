import unittest
from datetime import date

from src import match, parse

BUGUN = date(2026, 10, 19)
PROFIL = {"puan_turleri": ["P3"], "kpss_yili": 2026, "oncelikli_iller": ["Kahramanmaraş"], "herhangi_lisans_ilanlari": True,
          "deneyim_yili": 0, "yds_var": False}


def sayfa(baslik, ust, ogrenim, ek="", unvanlar=()):
    un = "".join(f'<a href="https://www.memurjet.com/is-ilanlari/{u[1]}">{u[0]}</a>' for u in unvanlar)
    og = "".join(f"<li><span>✓</span><span>Öğrenim: {o}</span></li>" for o in ogrenim)
    return f"""<html><body><h1>{baslik}</h1><ul>{un}</ul>{ust}
    <h2>Başvuru şartları</h2><ul>{og}</ul>{ek}
    <h2>Benzer ilanlar</h2><a>Son: 1 Kas</a> Öğrenim: Lisans · Hukuk</body></html>"""


KESAN = sayfa(
    "Keşan Belediye Başkanlığı 2 Memur Alımı",
    """<div>Son başvuru</div><div>19 Kasım, 17:30</div><div>Başvuru tarihleri</div><div>16–19 Kasım</div>
    <div>Kadro</div><div>2 kişi</div><div>Çalışma yeri</div><a href="/is-ilanlari/edirne">Edirne</a>
    <div>KPSS</div><div>P3 (≥ 70)</div><div>İstihdam</div><div>Kadrolu memur</div>
    <h2>Nasıl başvurulur?</h2><div>Başlangıç</div><div>16 Kasım 2026</div><div>Son başvuru</div><div>19 Kasım 2026, 17:30</div>
    <p>Elektronik ortamda mail yoluyla veya şahsen/iadeli taahhütlü posta ile</p><p>Kaynak:
    <a href="https://kamuilan.sbb.gov.tr/#ilan-x">kamuilan.sbb.gov.tr</a></p>""",
    ["Lisans · İnşaat Mühendisliği", "Lisans · Elektrik-Elektronik Mühendisliği"],
    "<p>2026 yılı KPSS (B grubu) sınavına girmiş olmak</p><p>KPSS P3 puan türünden en az 70 puan almış olmak</p>",
    [("İnşaat Mühendisi", "insaat-muhendisi"), ("Elektrik-Elektronik Mühendisi", "elektrik-elektronik-muhendisi"), ("Edirne", "edirne")])


class Parse(unittest.TestCase):
    def test_kesan_alanlar(self):
        d = parse.parse_ilan(KESAN, "u", BUGUN)
        self.assertEqual(d["son_basvuru"], "2026-11-19")
        self.assertEqual(d["son_saat"], "17:30")
        self.assertEqual(d["baslangic"], "2026-11-16")
        self.assertEqual(d["kadro"], 2)
        self.assertEqual(d["kpss_asgari"], {"3": 70.0})
        self.assertIn(2026, d["kpss_yillari"])
        self.assertEqual(d["unvanlar"], ["İnşaat Mühendisi", "Elektrik-Elektronik Mühendisi"])  # il adı elendi
        self.assertEqual(len(d["ogrenim"]), 2)
        self.assertTrue(d["resmi_kaynak"].startswith("https://kamuilan"))
        self.assertNotIn("Hukuk", d["tam_metin"])  # 'Benzer ilanlar' kesildi

    def test_kesan_uygun(self):
        d = parse.parse_ilan(KESAN, "u", BUGUN)
        r = match.degerlendir(d, PROFIL, BUGUN)
        self.assertEqual(r["sonuc"], "KESIN", r)


class Eslestirme(unittest.TestCase):
    def ilan(self, html):
        return parse.parse_ilan(html, "u", BUGUN)

    def test_hukuk_elenir(self):
        h = sayfa("Gelir İdaresi 860 Alımı", "<div>Son başvuru 3 Kasım 2026</div><div>KPSS P17 P18 P22 P23 P47 P48</div>",
                  ["Lisans · Hukuk", "Lisans · İktisat", "Lisans · İşletme"], "<p>2026 yılı KPSS</p>")
        r = match.degerlendir(self.ilan(h), PROFIL, BUGUN)
        self.assertIsNone(r["sonuc"])

    def test_on_lisans_elenir(self):
        h = sayfa("Düzce Ü. Sözleşmeli", "<div>Son başvuru 28 Ekim 2026</div><div>KPSS P93</div>", ["Ön lisans · Tıbbi Görüntüleme"], "<p>2026 KPSS</p>")
        self.assertIsNone(match.degerlendir(self.ilan(h), PROFIL, BUGUN)["sonuc"])

    def test_suresi_gecmis(self):
        h = sayfa("Eski", "<div>Son başvuru 10 Ekim 2026</div><div>P3 (≥ 60)</div>", ["Lisans · Elektrik-Elektronik Mühendisliği"], "<p>2026 KPSS</p>")
        self.assertEqual(match.degerlendir(self.ilan(h), PROFIL, BUGUN)["neden"], "başvuru süresi geçmiş")

    def test_kpss_2024_elenir(self):
        h = sayfa("TÜSEB", "<div>Son başvuru 30 Ekim 2026</div><div>P3 (≥ 60)</div>", ["Lisans · Elektrik-Elektronik Mühendisliği"], "<p>2024 yılı KPSS B grubu</p>")
        r = match.degerlendir(self.ilan(h), PROFIL, BUGUN)
        self.assertIsNone(r["sonuc"]); self.assertIn("yılı", r["neden"])

    def test_deneyim_dikkat(self):
        h = sayfa("Sayıştay Bilişim", "<div>Son başvuru 30 Ekim 2026</div><div>P3 (≥ 70)</div>",
                  ["Lisans · Bilgisayar, Elektrik-Elektronik ve Endüstri Mühendisliği"],
                  "<p>En az 3 yıl yazılım geliştirme deneyimine sahip olmak</p><p>2026 yılı KPSS</p>")
        r = match.degerlendir(self.ilan(h), PROFIL, BUGUN)
        self.assertEqual(r["sonuc"], "DIKKAT"); self.assertTrue(any("deneyim" in u for u in r["uyarilar"]))

    def test_herhangi_lisans_ve_oncelik(self):
        h = sayfa("Kahramanmaraş Büyükşehir Memur", "<div>Son başvuru 5 Kasım 2026</div><div>P3 (≥ 60)</div><div>Çalışma yeri Kahramanmaraş</div>",
                  ["Lisans · Herhangi bir lisans bölümü"], "<p>2026 yılı KPSS</p>")
        r = match.degerlendir(self.ilan(h), PROFIL, BUGUN)
        self.assertEqual(r["sonuc"], "KESIN"); self.assertTrue(r["oncelikli"])

    def test_p3_puan_filtresi(self):
        d = parse.parse_ilan(KESAN, "u", BUGUN)
        r = match.degerlendir(d, dict(PROFIL, p3_puani=65), BUGUN)
        self.assertIsNone(r["sonuc"])

    def test_akademik(self):
        h = sayfa("Bursa Uludağ Üniversitesi 37 Öğretim Üyesi Alımı", "<div>Son başvuru 30 Ekim 2026</div>", ["Lisans · Mühendislik"], "")
        self.assertIsNone(match.degerlendir(self.ilan(h), PROFIL, BUGUN)["sonuc"])


if __name__ == "__main__":
    unittest.main()
