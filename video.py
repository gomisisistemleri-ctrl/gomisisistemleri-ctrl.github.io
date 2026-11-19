"""
Günlük kısa dikey video üreticisi (Instagram Reels / TikTok / YouTube Shorts, 1080x1920, ~15 sn).

Kullanım:
  python video.py --csv gunluk.csv --cikti KLASOR [--soru ogg_sinav kpss_gunluksoru ...] [--ilan ozelguvenlikilan_tr ...]

--soru: verilen kanalların o günkü İLK quiz'inden "Günün sorusu" videosu
        (soru + şıklar → 5 sn geri sayım → doğru cevap + açıklama → kanala katıl).
--ilan: verilen kanalların o günkü ilan kartlarından "Bugünün ilanları" videosu (en fazla 5 ilan).
Çıktı: KLASOR/<kanal>_soru.mp4, KLASOR/<kanal>_ilanlar.mp4 ve her video için paylaşım açıklaması (.txt).
"""
import argparse
import csv
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from olustur import KANAL, RENK, ilan_ayristir

W, H, FPS = 1080, 1920, 25
FONT_YOLLARI = {
    "kalin": ["/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "orta": ["/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "normal": ["/usr/share/fonts/opentype/inter/Inter-Regular.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}
_fcache = {}


def font(tur, n):
    if (tur, n) not in _fcache:
        yol = next((f for f in FONT_YOLLARI[tur] if Path(f).exists()), None)
        _fcache[(tur, n)] = ImageFont.truetype(yol, n) if yol else ImageFont.load_default()
    return _fcache[(tur, n)]


def kucuk(s):
    return s.replace("İ", "i").replace("I", "ı").lower()


def etiketler(k, n):
    return " ".join("#" + kucuk(x).replace(" ", "").replace("'", "") for x in KANAL[k][2].split(",")[:n])


def hex2rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def arkaplan(k):
    c1, c2, _ = RENK[k]
    a, b = hex2rgb(c1), hex2rgb(c2)
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3)))
    return im


def sar(d, metin, f, genislik):
    satirlar = []
    for paragraf in metin.split("\n"):
        satir = ""
        for k in paragraf.split():
            dene = (satir + " " + k).strip()
            if d.textlength(dene, font=f) > genislik and satir:
                satirlar.append(satir)
                satir = k
            else:
                satir = dene
        satirlar.append(satir)
    return satirlar


def yaz(d, metin, f, x, y, genislik, renk="white", aralik=1.25, sinir=None):
    satirlar = sar(d, metin, f, genislik)
    if sinir and len(satirlar) > sinir:
        satirlar = satirlar[:sinir]
        satirlar[-1] = satirlar[-1].rstrip(".,;:") + "…"
    for s in satirlar:
        d.text((x, y), s, font=f, fill=renk)
        y += int(f.size * aralik)
    return y


def uygun_font(d, metin, tur, buyuk, kucuk, genislik, max_satir):
    for n in range(buyuk, kucuk - 1, -4):
        if len(sar(d, metin, font(tur, n), genislik)) <= max_satir:
            return font(tur, n)
    return font(tur, kucuk)


def ust_bant(im, k, etiket):
    d = ImageDraw.Draw(im)
    prof = Path(__file__).resolve().parent / "img" / f"{k}.jpg"
    if prof.exists():
        p = Image.open(prof).convert("RGB").resize((150, 150))
        m = Image.new("L", (150, 150), 0)
        ImageDraw.Draw(m).ellipse([0, 0, 150, 150], fill=255)
        im.paste(p, (80, 130), m)
    d.text((260, 150), KANAL[k][0][:34], font=font("orta", 40), fill="white")
    d.text((260, 205), f"@{k}", font=font("normal", 36), fill=(225, 230, 245))
    f = font("kalin", 44)
    w = d.textlength(etiket, font=f)
    d.rounded_rectangle([80, 330, 80 + w + 60, 410], radius=40, fill="white")
    d.text((110, 342), etiket, font=f, fill=hex2rgb(RENK[k][0]))


def kapanis(k, ust, alt):
    im = arkaplan(k)
    d = ImageDraw.Draw(im)
    prof = Path(__file__).resolve().parent / "img" / f"{k}.jpg"
    if prof.exists():
        p = Image.open(prof).convert("RGB").resize((360, 360))
        m = Image.new("L", (360, 360), 0)
        ImageDraw.Draw(m).ellipse([0, 0, 360, 360], fill=255)
        im.paste(p, ((W - 360) // 2, 480), m)
    y = 920
    for s in sar(d, ust, font("kalin", 72), W - 160):
        w = d.textlength(s, font=font("kalin", 72))
        d.text(((W - w) / 2, y), s, font=font("kalin", 72), fill="white")
        y += 90
    y += 40
    f = font("kalin", 54)
    t = f"t.me/{k}"
    w = d.textlength(t, font=f)
    d.rounded_rectangle([(W - w) / 2 - 40, y, (W + w) / 2 + 40, y + 100], radius=50, fill="white")
    d.text(((W - w) / 2, y + 20), t, font=f, fill=hex2rgb(RENK[k][0]))
    y += 160
    for s in sar(d, alt, font("normal", 40), W - 200):
        w = d.textlength(s, font=font("normal", 40))
        d.text(((W - w) / 2, y), s, font=font("normal", 40), fill=(230, 235, 250))
        y += 56
    return im


def kaydet(sahneler, hedef):
    """sahneler: [(PIL.Image | callable(t)->Image, saniye)] → mp4 (H.264 + sessiz ses, sosyal medya uyumlu)."""
    p = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         "-c:a", "aac", "-b:a", "64k", str(hedef)], stdin=subprocess.PIPE)
    for sahne, sure in sahneler:
        n = int(sure * FPS)
        sabit = None if callable(sahne) else sahne.tobytes()
        for i in range(n):
            p.stdin.write(sabit if sabit else sahne(i / n).tobytes())
    p.stdin.close()
    p.wait()
    if p.returncode:
        raise RuntimeError(f"ffmpeg hatası: {hedef}")


# ---------- Günün sorusu ----------
def soru_videosu(k, r, hedef):
    soru = r["metin"].strip()
    sec = [s.strip() for s in r["secenekler"].split("|") if s.strip()][:5]
    dogru = int(r["dogru"]) - 1
    aciklama = (r.get("aciklama") or "").strip()
    harf = "ABCDE"

    def soru_karesi(cevap=False, kalan=None):
        im = arkaplan(k)
        ust_bant(im, k, "GÜNÜN SORUSU")
        d = ImageDraw.Draw(im)
        fs = uygun_font(d, soru, "kalin", 64, 44, W - 160, 7)
        y = yaz(d, soru, fs, 80, 480, W - 160, sinir=7) + 40
        fo = uygun_font(d, max(sec, key=len), "orta", 46, 34, W - 300, 2)
        for i, s in enumerate(sec):
            satir = sar(d, s, fo, W - 300)[:2]
            yuk = 50 + len(satir) * int(fo.size * 1.25)
            if cevap and i == dogru:
                kutu, yazi = (46, 160, 90), "white"
            elif cevap:
                kutu, yazi = (255, 255, 255, 0), (210, 215, 230)
            else:
                kutu, yazi = "white", (25, 25, 35)
            if cevap and i != dogru:
                d.rounded_rectangle([80, y, W - 80, y + yuk], radius=28, outline=(210, 215, 230), width=3)
            else:
                d.rounded_rectangle([80, y, W - 80, y + yuk], radius=28, fill=kutu)
            d.text((115, y + 25), harf[i], font=font("kalin", fo.size), fill=yazi)
            yaz(d, "\n".join(satir), fo, 190, y + 25, W - 300, renk=yazi)
            if cevap and i == dogru:
                d.text((W - 160, y + 20), "✓", font=font("kalin", 60), fill="white")
            y += yuk + 22
        if kalan is not None:
            d.rounded_rectangle([80, H - 260, W - 80, H - 230], radius=15, fill=(255, 255, 255), outline="white", width=2)
            d.rounded_rectangle([82, H - 258, W - 82, H - 232], radius=13, fill=hex2rgb(RENK[k][0]))
            d.rounded_rectangle([80, H - 260, 80 + max(30, int((W - 160) * kalan)), H - 230], radius=15, fill="white")
            t = f"Cevabını düşün… {max(1, int(kalan * 5 + 0.999))}"
            d.text((80, H - 340), t, font=font("orta", 44), fill="white")
        elif cevap and aciklama:
            yaz(d, aciklama, font("normal", 38), 80, max(y + 20, H - 470), W - 160,
                renk=(235, 240, 250), sinir=5)
        return im

    kaydet([
        (soru_karesi(), 1.5),
        (lambda t: soru_karesi(kalan=1 - t), 5),
        (soru_karesi(cevap=True), 5),
        (kapanis(k, "Her gün yeni soru", "Telegram'da ücretsiz · çözümlü sorular, konu özetleri ve sınav takvimi"), 3.5),
    ], hedef)
    return (f"Günün sorusu 👇 Cevabını yorumlara yaz!\n\nHer gün yeni soru ve çözümü Telegram kanalımızda: t.me/{k}\n\n"
            + etiketler(k, 4) + " #sınavhazırlık #gününsorusu")


# ---------- Bugünün ilanları ----------
def ilan_videosu(k, ilanlar, hedef, tarih):
    ilanlar = ilanlar[:5]

    def kare(n):
        im = arkaplan(k)
        ust_bant(im, k, f"BUGÜNÜN İLANLARI · {tarih[8:10]}.{tarih[5:7]}")
        d = ImageDraw.Draw(im)
        y = 480
        for i in ilanlar[:n]:
            yer = i["il"] + (f" / {i['ilce']}" if i["ilce"] else "")
            bas = f"{i['pozisyon']}"
            alt = i["firma"] + (f" · {i['maas']}" if i["maas"] else "")
            d.rounded_rectangle([80, y, W - 80, y + 230], radius=30, fill="white")
            d.text((120, y + 25), yer.upper(), font=font("orta", 34), fill=hex2rgb(RENK[k][0]))
            yaz(d, bas, font("kalin", 46), 120, y + 72, W - 240, renk=(25, 25, 35), sinir=1)
            yaz(d, alt, font("normal", 36), 120, y + 140, W - 240, renk=(90, 90, 100), sinir=1)
            y += 255
        return im

    sahneler = [(kare(0), 1.0)] + [(kare(n), 2.2) for n in range(1, len(ilanlar) + 1)]
    sahneler.append((kapanis(k, "Başvuru linkleri Telegram'da", "Her gün yeni ilan · il etiketiyle · reklamsız"), 3.5))
    kaydet(sahneler, hedef)
    iller = " ".join(dict.fromkeys("#" + i["il"] for i in ilanlar))
    return (f"Bugünün {kucuk(KANAL[k][0].split('–')[0].strip())} 👇\n\nBaşvuru linkleri ve daha fazlası Telegram kanalımızda: t.me/{k}\n\n"
            f"{iller} " + etiketler(k, 3) + " #işilanı #iş")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", nargs="+", required=True)
    p.add_argument("--cikti", required=True)
    p.add_argument("--soru", nargs="*", default=[])
    p.add_argument("--ilan", nargs="*", default=[])
    a = p.parse_args()
    cikti = Path(a.cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    satirlar = []
    for yol in a.csv:
        with open(yol, encoding="utf-8-sig") as f:
            satirlar += list(csv.DictReader(f))
    for r in satirlar:
        r["kanal"] = r.get("kanal", "").lstrip("@").lower()
    tarih = min((r["tarih"] for r in satirlar), default="")
    uretilen = []
    for k in a.soru:
        r = next((r for r in satirlar if r["kanal"] == k and r.get("tur") == "quiz" and r.get("dogru")), None)
        if not r or k not in RENK:
            print(f"ATLANDI {k}: quiz yok")
            continue
        hedef = cikti / f"{k}_soru.mp4"
        hedef.with_suffix(".txt").write_text(soru_videosu(k, r, hedef), encoding="utf-8")
        uretilen.append(hedef.name)
    for k in a.ilan:
        ilanlar = [i for i in (ilan_ayristir(r) for r in satirlar if r["kanal"] == k) if i]
        if len(ilanlar) < 2 or k not in RENK:
            print(f"ATLANDI {k}: yeterli ilan yok ({len(ilanlar)})")
            continue
        hedef = cikti / f"{k}_ilanlar.mp4"
        hedef.with_suffix(".txt").write_text(ilan_videosu(k, ilanlar, hedef, tarih), encoding="utf-8")
        uretilen.append(hedef.name)
    print("Üretilen videolar:", ", ".join(uretilen) or "yok")


if __name__ == "__main__":
    main()
