"""Memurjet'ten alınmış gerçek ilan sayfalarıyla (tests/fixtures) uçtan uca doğrulama."""
import unittest
from datetime import date
from pathlib import Path

from src import match, parse

BUGUN = date(2026, 10, 22)
FX = Path(__file__).parent / "fixtures"
PROFIL = {"puan_turleri": ["P3"], "kpss_yili": 2026, "oncelikli_iller": ["Kahramanmaraş"], "herhangi_lisans_ilanlari": True,
          "deneyim_yili": 0, "yds_var": False}


def ilan(ad):
    d = parse.parse_ilan((FX / f"{ad}.html").read_text(encoding="utf-8"), ad, BUGUN)
    d["listede"] = True
    return d, match.degerlendir(d, PROFIL, BUGUN)


class Gercek(unittest.TestCase):
    def test_kesan(self):
        d, r = ilan("kesan-belediye-baskanligi-2-memur-alimi")
        self.assertEqual((d["son_basvuru"], d["baslangic"], d["yer"]), ("2026-11-19", "2026-11-16", "Edirne"))
        self.assertEqual(d["kpss_asgari"], {"3": 70.0})
        self.assertEqual(d["unvanlar"], ["İnşaat Mühendisi", "Elektrik-Elektronik Mühendisi"])
        self.assertEqual(r["sonuc"], "KESIN")

    def test_spk_cok_turlu_kpss(self):
        d, r = ilan("sermaye-piyasasi-kurulu-40-uzman-yardimcisi-alim-ilani")
        self.assertIn(3, d["kpss_turleri"]); self.assertEqual(d["kpss_asgari"]["3"], 75.0)
        self.assertEqual(d["yer"], "Ankara, İstanbul")
        self.assertIsNotNone(r["sonuc"])  # "Mühendislik" bölüm listesinde
        d2 = dict(d)
        self.assertIsNone(match.degerlendir(d2, dict(PROFIL, p3_puani=72), BUGUN)["sonuc"])  # 72 < 75

    def test_zabita_herhangi_lisans_haric(self):
        d, r = ilan("didim-belediye-baskanligi-18-zabita-memuru-alimi")
        self.assertIsNone(r["sonuc"]); self.assertIn("hariç", r["neden"])
        self.assertEqual(match.degerlendir(d, dict(PROFIL, haric_kadrolar=[]), BUGUN)["sonuc"], "KESIN")

    def test_akademik_ve_askeri_elenir(self):
        self.assertEqual(ilan("abdullah-gul-universitesi-6-ogretim-elemani-alimi")[1]["neden"], "akademik kadro")
        self.assertEqual(ilan("jandarma-genel-komutanligi-135-muvazzaf-subay-alimi")[1]["neden"], "askeri/kolluk kadrosu")

    def test_iett_unvana_gore(self):
        d, r = ilan("iett-44-memur-alimi")
        self.assertEqual(d["son_basvuru"], "2026-11-02")
        self.assertEqual(r["sonuc"], "KESIN")


if __name__ == "__main__":
    unittest.main()
