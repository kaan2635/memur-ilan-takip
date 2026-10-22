"""GitHub Pages için tek dosyalık (docs/index.html) ilan listesi sayfası. Kişisel bilgi içermez."""
import json
from datetime import date

SABLON = r"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Memur İlanları — uygun açık ilanlar</title>
<meta name="description" content="E-E lisans + KPSS 2026 profiline uygun açık kamu ilanları, her gün güncellenir.">
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#16191d;--mut:#5d6672;--line:#e3e6ea;--ok:#0f7b45;--okbg:#e4f5ec;--warn:#9a5b00;--warnbg:#fdf0d9;--acc:#1d4ed8;--pin:#b42318}
@media(prefers-color-scheme:dark){:root{--bg:#0f1216;--card:#171b21;--ink:#e8ebef;--mut:#98a2b0;--line:#262c35;--ok:#4cc38a;--okbg:#123222;--warn:#f0b34a;--warnbg:#3a2a0c;--acc:#7aa2ff;--pin:#ff8a80}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.w{max-width:820px;margin:0 auto;padding:20px 16px 60px}
h1{font-size:1.5rem;margin:8px 0 2px}.sub{color:var(--mut);font-size:.9rem;margin:0 0 16px}
.bar{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 14px;position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:2}
.bar input{flex:1 1 200px;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);font:inherit}
.chip{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:8px 14px;font:inherit;cursor:pointer}
.chip[aria-pressed=true]{background:var(--acc);border-color:var(--acc);color:#fff}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:0 0 12px}
.top{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:4px}
.tag{font-size:.78rem;font-weight:600;padding:2px 9px;border-radius:999px}
.k{background:var(--okbg);color:var(--ok)}.d{background:var(--warnbg);color:var(--warn)}.p{color:var(--pin);font-weight:600;font-size:.85rem}
.card h2{font-size:1.05rem;margin:2px 0 6px}.card h2 a{color:inherit;text-decoration:none}.card h2 a:hover{text-decoration:underline}
.meta{color:var(--mut);font-size:.9rem;margin:2px 0}.meta b{color:var(--ink)}
.kalan{font-weight:700}.kalan.acil{color:var(--pin)}
ul{margin:6px 0 0;padding-left:18px;color:var(--mut);font-size:.9rem}
.btn{display:inline-block;margin-top:10px;padding:8px 14px;border-radius:10px;background:var(--acc);color:#fff;text-decoration:none;font-size:.92rem}
.bos{color:var(--mut);text-align:center;padding:40px 0}
footer{color:var(--mut);font-size:.82rem;margin-top:24px}
</style></head><body><div class="w">
<h1>📬 Memur İlanları</h1>
<p class="sub" id="sub"></p>
<div class="bar">
<input id="q" type="search" placeholder="Ara: kurum, unvan, il…" aria-label="Ara">
<button class="chip" data-f="hepsi" aria-pressed="true">Hepsi</button>
<button class="chip" data-f="KESIN" aria-pressed="false">✅ Uygun</button>
<button class="chip" data-f="DIKKAT" aria-pressed="false">⚠️ Kontrol et</button>
<button class="chip" data-f="pin" aria-pressed="false">📍 Öncelikli il</button>
</div>
<div id="liste"></div>
<footer>Kaynak: Memurjet. Kural tabanlı eşleştirme; başvurmadan önce resmî ilan metnini oku. Başvuru e-Devlet / Kariyer Kapısı üzerinden yapılır. Her gün 07:30 ve 16:30'da güncellenir.</footer>
</div>
<script id="veri" type="application/json">__VERI__</script>
<script>
const V=JSON.parse(document.getElementById('veri').textContent);
const BUGUN=new Date(V.bugun+'T00:00:00');
let filtre='hepsi';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tr=d=>new Date(d+'T00:00:00').toLocaleDateString('tr-TR',{day:'numeric',month:'long',year:'numeric'});
document.getElementById('sub').textContent=`Son güncelleme: ${tr(V.bugun)} · ${V.ilanlar.length} uygun veya kontrol edilecek açık ilan`;
function kart(i){
  const dg=i.degerlendirme,k=dg.sonuc==='KESIN';
  let kalan='';
  if(i.son_basvuru){const g=Math.round((new Date(i.son_basvuru+'T00:00:00')-BUGUN)/864e5);
    kalan=`<span class="kalan ${g<=3?'acil':''}">${g<=0?'Son gün bugün':g+' gün kaldı'}</span> · ${tr(i.son_basvuru)}${i.son_saat?' '+esc(i.son_saat):''}`;}
  else kalan='Son başvuru tarihi okunamadı';
  const acilis=i.baslangic&&new Date(i.baslangic+'T00:00:00')>BUGUN?` · başvuru ${tr(i.baslangic)} tarihinde açılıyor`:'';
  const uy=(dg.uyarilar||[]).map(u=>`<li>${esc(u)}</li>`).join('');
  return `<article class="card"><div class="top"><span class="tag ${k?'k':'d'}">${k?'✅ Uygun':'⚠️ Kontrol et'}</span>${dg.oncelikli?'<span class="p">📍 Öncelikli il</span>':''}</div>
  <h2><a href="${esc(i.url)}" target="_blank" rel="noopener">${esc(i.baslik)}</a></h2>
  <div class="meta">${kalan}${acilis}</div>
  ${i.unvanlar&&i.unvanlar.length?`<div class="meta"><b>Unvanlar:</b> ${esc(i.unvanlar.slice(0,6).join(', '))}</div>`:''}
  <div class="meta"><b>Yer:</b> ${esc(i.yer||'?')}${i.istihdam?' · '+esc(i.istihdam):''}${i.kadro?' · '+i.kadro+' kadro':''}</div>
  <div class="meta">${esc(dg.neden)}</div>${uy?`<ul>${uy}</ul>`:''}
  ${i.basvuru_yolu?`<div class="meta"><b>Başvuru:</b> ${esc(i.basvuru_yolu)}</div>`:''}
  <a class="btn" href="${esc(i.url)}" target="_blank" rel="noopener">İlanı aç</a></article>`;}
function ciz(){
  const q=document.getElementById('q').value.toLocaleLowerCase('tr');
  const l=V.ilanlar.filter(i=>(filtre==='hepsi'||(filtre==='pin'?i.degerlendirme.oncelikli:i.degerlendirme.sonuc===filtre))
    &&(!q||(i.baslik+' '+(i.unvanlar||[]).join(' ')+' '+(i.yer||'')).toLocaleLowerCase('tr').includes(q)));
  document.getElementById('liste').innerHTML=l.length?l.map(kart).join(''):'<p class="bos">Bu filtreyle ilan yok.</p>';}
document.querySelectorAll('.chip').forEach(b=>b.onclick=()=>{filtre=b.dataset.f;document.querySelectorAll('.chip').forEach(x=>x.setAttribute('aria-pressed',x===b));ciz();});
document.getElementById('q').oninput=ciz;ciz();
</script></body></html>"""


def uret(ilanlar, bugun: date) -> str:
    """ilanlar: sıralı ilan sözlükleri (tam_metin hariç). Kişisel profil bilgisi eklenmez."""
    veri = json.dumps({"bugun": bugun.isoformat(), "ilanlar": ilanlar}, ensure_ascii=False, default=str).replace("</", "<\\/")
    return SABLON.replace("__VERI__", veri)
