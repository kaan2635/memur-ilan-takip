# memur-ilan-takip

Memurjet'teki açık kamu ilanlarını her gün otomatik tarar, `profile.yml`'deki profile (E-E lisans, KPSS 2026) uyanları süzer, **yeni** çıkanları ve **son günü yaklaşanları** sana bildirir.

## Nasıl çalışır
1. GitHub Actions her gün 07:30 ve 16:30'da (TR saati) çalışır (`.github/workflows/gunluk.yml`).
2. `src/fetch.py` Memurjet liste sayfaları + sitemap'ten ilan adreslerini toplar, `src/parse.py` her ilanın detayını ayrıştırır.
3. `src/match.py` kurallarla eler: süre geçmiş mi, lisans mı, bölüm (E-E / mühendislik / herhangi lisans), KPSS türü (P3) ve yılı (2026), asgari puan, yaş, deneyim, YDS.
4. Sonuç iki grup: **✅ Uygun** ve **⚠️ Kontrol et** (deneyim/YDS/bölüm belirsiz). Kahramanmaraş'lı ilanlar 📍 ile öne çıkar.
5. `ACIK_ILANLAR.md` her gün güncellenir, `data/state.json` hangi ilanı bildirdiğini hatırlar (aynı ilan iki kez bildirilmez).

## Bildirim (hepsi bedava)
- **GitHub Issue** (varsayılan, kurulum gerekmez): yeni ilan olunca bir Issue açılır. Sana e-posta gelir; GitHub mobil uygulamasını kurarsan telefona push da gelir. Repo'da *Watch → All activity* açık olsun.
- **ntfy.sh** (opsiyonel, anlık telefon bildirimi): telefona ntfy uygulamasını kur, tahmin edilmesi zor bir konu adı seç (ör. `kaan-ilan-8f3k2x`), uygulamada abone ol, repo *Settings → Secrets and variables → Actions* içine `NTFY_TOPIC` olarak ekle.
- **Telegram** (opsiyonel): BotFather ile bot aç, `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID` secret'larını ekle.

## Kurulum
1. *Actions* sekmesinden workflow'ları etkinleştir.
2. *Actions → Günlük ilan taraması → Run workflow* ile ilk taramayı elle başlat (ilk çalışmada şu an açık tüm uygun ilanlar bir Issue olarak gelir).
3. `profile.yml`'yi doldur: özellikle `p3_puani`, `dogum_yili`, `cinsiyet`, `yds_var`, `deneyim_gerekiyorsa_gizle`. Doldurdukça liste daralır.

## Yerelde deneme
```bash
pip install -r requirements.txt
python -m unittest discover -s tests
python -m src.main --url https://www.memurjet.com/is-ilanlari/kesan-belediye-baskanligi-2-memur-alimi   # tek ilanı ayrıştır
python -m src.main --kuru                                                                                  # bildirim yazmadan tüm akış
```

## Sınırlar
- **Otomatik başvuru yok.** Başvurular e-Devlet / Kariyer Kapısı girişi ve kişisel belge gerektirir; sistem ilanı bulur, uygunluğunu işaretler, son tarihi ve başvuru linkini verir.
- Kaynak Memurjet'tir; ilanların resmî metni (kamuilan.sbb.gov.tr, kurum siteleri) başvurmadan önce okunmalıdır. Eşleştirme kural tabanlıdır, "⚠️ Kontrol et" ilanlarda özellikle bölüm ve deneyim şartını kendin doğrula.
- Memurjet sayfa yapısını değiştirirse ayrıştırıcı (`src/parse.py`) güncellenmelidir; hiç ilan indirilemezse workflow hata verir ve GitHub sana "failed run" e-postası gönderir.
- `kamuilan.sbb.gov.tr` yurt dışı IP'lere kapalı olduğundan (Actions sunucuları ABD'de) doğrudan taranmaz.
