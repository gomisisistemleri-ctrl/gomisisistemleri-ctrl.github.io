"""
Telegram meslek kanalları tanıtım sitesi üreticisi (GitHub Pages).
Kullanım:
  python olustur.py --taban https://KULLANICI.github.io/DEPO [--csv gunluk.csv ...]
Verilen günlük CSV'lerden (kuyruk biçimi) her kanalın son gönderilerini
sayfasına yazar; Google için başlık, açıklama, sitemap ve yapılandırılmış veri üretir.
Çıktı: bu klasörün içine (index.html, kanal/<ad>/index.html, sitemap.xml, robots.txt).
"""
import argparse
import csv
import html
import json
import re
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parent
SON_N = 15

AILELER = [
    ("Özel Güvenlik", "#13294B", "#2B5A8C", ["ozelguvenlikilan_tr", "ogg_sinav", "ozelguvenliksinavi"]),
    ("Öğretmen", "#B4541A", "#E8892E", ["ogretmen_isilani", "ags_hazirlik", "evrak_ogretmen"]),
    ("Hemşire ve Sağlık", "#0B6E70", "#18A2A0", ["hemsire_isilanlari", "yurtdisi_hemsire", "saglik_atama"]),
    ("Eczane ve İlaç Sektörü", "#1F6B43", "#36A36A", ["eczane_isilani", "devir_eczane", "mumessil_ilan", "utt_sinav"]),
    ("İş Güvenliği", "#B87A00", "#F2B705", ["isguzmani_sinav"]),
    ("KPSS ve Kamu", "#8E1F1A", "#D2463B", ["kpss_gunluksoru", "kpsstercih_tr", "kamu_alimlari", "sinav_gorevi"]),
]
KANAL = {
    "ozelguvenlikilan_tr": ("Özel Güvenlik İş İlanları – Türkiye", "Türkiye geneli özel güvenlik (ÖGG) iş ilanları: silahlı ve silahsız güvenlik görevlisi alımları, maaş ve il bilgisiyle. Her gün güncel, reklamsız.", "özel güvenlik iş ilanları, güvenlik görevlisi alımı, ÖGG iş ilanı, silahsız güvenlik ilanları"),
    "ogg_sinav": ("ÖGG Sınav Hazırlık – Günlük Soru", "Özel güvenlik temel ve yenileme sınavına her gün çözümlü soru, quiz ve konu özeti. Sınav takvimi ve geri sayım.", "özel güvenlik sınav soruları, ÖGG sınavı, özel güvenlik test, yenileme sınavı"),
    "ozelguvenliksinavi": ("Özel Güvenlik Sınavı – Çıkmış Sorular ve PDF", "Özel güvenlik temel ve yenileme sınavları için konu özeti ve çözümlü soru PDF arşivi.", "özel güvenlik çıkmış sorular pdf, ÖGG soru bankası, özel güvenlik sınavı pdf"),
    "ogretmen_isilani": ("Öğretmen İş İlanları – Reklamsız", "Özel okul, kurs ve dershane öğretmen iş ilanları; branş ve il etiketli, reklamsız Telegram kanalı.", "öğretmen iş ilanları, özel okul öğretmen ilanı, ücretli öğretmenlik, dershane öğretmen ilanı"),
    "ags_hazirlik": ("AGS ve ÖABT Hazırlık – Günlük Soru", "MEB Akademi Giriş Sınavı (AGS) ve ÖABT için her gün çözümlü soru, konu özeti ve deneme.", "AGS soruları, akademi giriş sınavı, ÖABT hazırlık, MEB AGS"),
    "evrak_ogretmen": ("Öğretmen Evrak ve Materyal", "Yıllık plan, zümre tutanağı, veli toplantısı ve rehberlik evrakları; sınıf ve branş etiketli arşiv.", "öğretmen evrakları, zümre tutanağı, yıllık plan, veli toplantısı tutanağı"),
    "hemsire_isilanlari": ("Hemşire ve Sağlık Personeli İş İlanları", "Hemşire, ebe, ATT, paramedik ve sağlık personeli iş ilanları; özel hastane, OSGB ve nöbet ilanları.", "hemşire iş ilanları, sağlık personeli alımı, ebe iş ilanı, ATT iş ilanı"),
    "yurtdisi_hemsire": ("Yurt Dışında Hemşirelik – Almanya ve İngiltere", "Almanya ve İngiltere'de hemşire olmak için denklik, dil sınavı, vize ve maaş rehberi.", "Almanya'da hemşirelik, İngiltere hemşire, hemşire denklik, yurt dışı hemşire"),
    "saglik_atama": ("Sağlıkçı Atama ve KPSS", "Sağlık Bakanlığı atama takvimi, KPSS taban puanları ve tercih rehberi.", "sağlık atama, hemşire ataması, KPSS sağlık taban puan"),
    "eczane_isilani": ("Eczacı ve Eczane Teknikeri İlanları", "İkinci eczacı, eczane teknikeri ve kalfa iş ilanları; SGK ve mevzuat özetleri.", "eczane teknikeri iş ilanı, eczacı iş ilanı, eczane kalfa ilanı"),
    "devir_eczane": ("Devir Eczane Vitrini", "Türkiye geneli devir ve satılık eczane ilanları; il, ciro aralığı ve reçete bilgisiyle.", "devir eczane, satılık eczane, eczane devri"),
    "mumessil_ilan": ("Tıbbi Mümessil ve Medikal Satış İlanları", "İlaç ve medikal firmalarının tıbbi tanıtım temsilcisi ve satış ilanları.", "tıbbi mümessil iş ilanı, tıbbi tanıtım temsilcisi, medikal satış ilanı"),
    "utt_sinav": ("ÜTT Sınavı ve Mümessil Kariyer Rehberi", "Ürün Tanıtım Temsilcisi (ÜTT) yeterlilik belgesi, sınav notları ve kariyer rehberi.", "ÜTT sınavı, ürün tanıtım temsilcisi belgesi, mümessil olmak"),
    "isguzmani_sinav": ("İş Güvenliği (İSG) Uzmanlığı – Sınav ve İlan", "İSG uzmanlık sınavına günlük soru ve PDF, mevzuat özetleri, OSGB ve iş güvenliği uzmanı ilanları.", "İSG sınav soruları, iş güvenliği uzmanı ilanı, OSGB iş ilanı"),
    "kpss_gunluksoru": ("KPSS Günlük Soru ve Notlar", "Her gün 1 konu, madde madde özet ve 5 soru; genel kültür ve genel yetenek.", "KPSS soruları, KPSS günlük soru, KPSS notları, genel kültür"),
    "kpsstercih_tr": ("KPSS Tercih ve Atama Takvimi", "KPSS tercih kılavuzu, taban puanları ve atama sonuçları.", "KPSS tercih, KPSS atama takvimi, taban puanlar"),
    "kamu_alimlari": ("Kamu Personel Alımları – Eğitim Düzeyine Göre", "Memur ve sözleşmeli personel alımları; lise, önlisans ve lisans etiketli, son başvuru tarihleriyle.", "kamu personel alımı, memur alımı, sözleşmeli personel ilanları"),
    "sinav_gorevi": ("Sınav Görevleri ve Ek Gelir", "ÖSYM, MEB ve AÖF sınav görevi başvuru tarihleri ve güncel ücret tabloları.", "sınav görevi, ÖSYM görevli, MEB sınav görevi ücretleri"),
}

CSS = """
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:#1d1d1f;background:#f6f6f4;line-height:1.55}
a{color:inherit}header{padding:40px 20px 24px;max-width:960px;margin:auto}h1{font-size:2rem;margin:0 0 8px}header p{color:#555;margin:0}
main{max-width:960px;margin:auto;padding:0 20px 60px}.aile{margin:28px 0}.aile h2{font-size:1.15rem;margin:0 0 12px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.kart{display:flex;gap:12px;align-items:center;background:#fff;border-radius:14px;padding:12px;text-decoration:none;border:1px solid #e6e6e2}
.kart:hover{border-color:#bbb}.kart img{width:56px;height:56px;border-radius:50%}.kart b{display:block;font-size:.95rem}.kart span{font-size:.82rem;color:#666}
.bant{color:#fff;padding:36px 20px}.bant .ic{max-width:960px;margin:auto;display:flex;gap:20px;align-items:center}
.bant img{width:96px;height:96px;border-radius:50%;border:3px solid #fff}.bant h1{color:#fff}.bant p{color:#eef;margin:4px 0 0}
.btn{display:inline-block;margin-top:14px;background:#fff;color:#111;padding:10px 18px;border-radius:999px;font-weight:600;text-decoration:none}
.gonderi{background:#fff;border:1px solid #e6e6e2;border-radius:12px;padding:14px 16px;margin:10px 0;white-space:pre-wrap;font-size:.95rem}
.gonderi small{display:block;color:#888;margin-bottom:6px}footer{text-align:center;color:#888;font-size:.85rem;padding:30px}
"""


def e(s):
    return html.escape(s or "", quote=True)


def sayfa(baslik, aciklama, kelimeler, kanonik, govde, jsonld, gorsel):
    return f"""<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(baslik)}</title><meta name="description" content="{e(aciklama)}"><meta name="keywords" content="{e(kelimeler)}">
<link rel="canonical" href="{e(kanonik)}"><meta property="og:title" content="{e(baslik)}"><meta property="og:description" content="{e(aciklama)}">
<meta property="og:type" content="website"><meta property="og:url" content="{e(kanonik)}"><meta property="og:image" content="{e(gorsel)}">
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
<style>{CSS}</style></head><body>{govde}<footer>Telegram meslek kanalları · güncellendi {date.today():%d.%m.%Y}</footer></body></html>"""


def temizle(metin):
    # bağlantıları ve paylaşım çağrısını sade tut
    metin = re.sub(r"↪️.*", "", metin or "").strip()
    return metin


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--taban", required=True)
    p.add_argument("--csv", nargs="*", default=[])
    p.add_argument("--davet", help="davet_baglantilari.csv (google kaynaklı bağlantılar için)")
    a = p.parse_args()
    taban = a.taban.rstrip("/")
    katil = {k: f"https://t.me/{k}" for k in KANAL}
    if a.davet and Path(a.davet).exists():
        with open(a.davet, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                k = r["kanal"].lstrip("@").lower()
                if r["kaynak"] == "google" and k in katil:
                    katil[k] = r["baglanti"]

    son = {k: [] for k in KANAL}
    for yol in sorted(a.csv):
        with open(yol, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                k = r.get("kanal", "").lstrip("@").lower()
                if k in son and r.get("tur") in ("metin", "quiz", "anket") and r.get("metin"):
                    if "@ihsantayfun" in r["metin"]:
                        continue  # tanıtım mesajını listeleme
                    son[k].append((r["tarih"], r["saat"], r["tur"], temizle(r["metin"])))
    gecmis = KOK / "veri.json"
    eski = json.loads(gecmis.read_text(encoding="utf-8")) if gecmis.exists() else {}
    for k in KANAL:
        birlesik = {tuple(x) for x in eski.get(k, [])} | set(son[k])
        son[k] = sorted(birlesik, key=lambda x: (x[0], x[1]), reverse=True)[:SON_N]
    gecmis.write_text(json.dumps(son, ensure_ascii=False), encoding="utf-8")

    # ana sayfa
    bloklar = []
    for ad, c1, c2, liste in AILELER:
        kartlar = "".join(
            f'<a class="kart" href="kanal/{k}/"><img src="img/{k}.jpg" alt="{e(KANAL[k][0])}" loading="lazy">'
            f'<div><b>{e(KANAL[k][0])}</b><span>@{k}</span></div></a>' for k in liste)
        bloklar.append(f'<section class="aile"><h2 style="color:{c1}">{e(ad)}</h2><div class="grid">{kartlar}</div></section>')
    govde = ('<header><h1>Meslek ve İş İlanı Telegram Kanalları</h1>'
             '<p>Özel güvenlik, öğretmen, hemşire, eczane, tıbbi mümessil, İSG, KPSS ve kamu alımları için '
             'her gün güncellenen, reklamsız Telegram kanalları.</p></header><main>' + "".join(bloklar) + "</main>")
    jsonld = {"@context": "https://schema.org", "@type": "ItemList", "name": "Meslek ve İş İlanı Telegram Kanalları",
              "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{taban}/kanal/{k}/", "name": KANAL[k][0]}
                                  for i, k in enumerate(KANAL)]}
    (KOK / "index.html").write_text(sayfa(
        "Meslek ve İş İlanı Telegram Kanalları | Özel Güvenlik, Öğretmen, Hemşire, KPSS",
        "Özel güvenlik, öğretmen, hemşire, eczane, tıbbi mümessil, İSG, KPSS ve kamu alımları için her gün güncellenen Telegram kanalları.",
        "telegram iş ilanları, telegram kanalları, iş ilanı telegram", f"{taban}/", govde, jsonld,
        f"{taban}/img/ozelguvenlikilan_tr.jpg"), encoding="utf-8")

    # kanal sayfaları
    for ad, c1, c2, liste in AILELER:
        for k in liste:
            baslik, aciklama, kelime = KANAL[k]
            gonderiler = "".join(
                f'<article class="gonderi"><small>{t[0][8:10]}.{t[0][5:7]}.{t[0][:4]} {t[1]}'
                f'{" · soru" if t[2] in ("quiz", "anket") else ""}</small>{e(t[3])}</article>' for t in son[k]
            ) or '<p>İlk gönderiler çok yakında burada.</p>'
            kardes = "".join(f'<a class="kart" href="../{x}/"><img src="../../img/{x}.jpg" alt="" loading="lazy">'
                             f'<div><b>{e(KANAL[x][0])}</b><span>@{x}</span></div></a>' for x in liste if x != k)
            govde = (f'<div class="bant" style="background:linear-gradient(135deg,{c1},{c2})"><div class="ic">'
                     f'<img src="../../img/{k}.jpg" alt="{e(baslik)}"><div><h1>{e(baslik)}</h1><p>{e(aciklama)}</p>'
                     f'<a class="btn" href="{e(katil[k])}">Telegram\'da katıl · @{k}</a></div></div></div>'
                     f'<main><h2>Son paylaşımlar</h2>{gonderiler}'
                     + (f'<h2>Aynı aileden kanallar</h2><div class="grid">{kardes}</div>' if kardes else "")
                     + '<p><a href="../../">← Tüm kanallar</a></p></main>')
            jsonld = {"@context": "https://schema.org", "@type": "WebPage", "name": baslik, "description": aciklama,
                      "url": f"{taban}/kanal/{k}/", "about": {"@type": "Thing", "name": baslik,
                                                              "sameAs": f"https://t.me/{k}"}}
            hedef = KOK / "kanal" / k
            hedef.mkdir(parents=True, exist_ok=True)
            (hedef / "index.html").write_text(sayfa(
                f"{baslik} | Telegram @{k}", aciklama, kelime, f"{taban}/kanal/{k}/", govde, jsonld,
                f"{taban}/img/{k}.jpg"), encoding="utf-8")

    bugun = f"{date.today()}"
    urls = [f"{taban}/"] + [f"{taban}/kanal/{k}/" for k in KANAL]
    (KOK / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{u}</loc><lastmod>{bugun}</lastmod><changefreq>daily</changefreq></url>" for u in urls)
        + "</urlset>", encoding="utf-8")
    (KOK / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {taban}/sitemap.xml\n", encoding="utf-8")
    print("Site üretildi:", len(urls), "sayfa")


if __name__ == "__main__":
    main()
