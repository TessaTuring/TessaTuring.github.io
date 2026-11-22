"""Build Tessa's tip site + RSS feed (for Pinterest auto-publish) from the tessa-autopost repo.

Every carousel that actually went out on Instagram becomes a page at /tips/<date>/ with a 2:3 pin
image and an RSS item. Run by .github/workflows/build.yml; safe to re-run (only new pins are drawn).
"""
from __future__ import annotations

import datetime as dt
import html
import io
import json
import os
import re
from email.utils import format_datetime
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

SRC = "TessaTuring/tessa-autopost"
RAW = f"https://raw.githubusercontent.com/{SRC}/main"
SITE = "https://tessaturing.github.io"
STORE = "https://stan.store/tessaturing"
ROOT = Path(__file__).parent
FONTS = ROOT / "assets" / "fonts"
TAGLINE = "Plain-English AI help for real life"
PAPER, INK, ROSE = (252, 250, 248), (43, 36, 32), (190, 84, 110)
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")


def gh(path: str, **params) -> list | dict:
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    r = requests.get(f"https://api.github.com/repos/{SRC}/{path}", headers=headers, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def posted_dates() -> set[str]:
    """Dates whose Instagram carousel really went out (review issue labelled 'posted')."""
    dates, page = set(), 1
    while True:
        batch = gh("issues", state="all", labels="posted", per_page=100, page=page)
        for issue in batch:
            m = re.fullmatch(r"Post for (\d{4}-\d{2}-\d{2}(?:-[a-z])?)", issue["title"])
            if m:
                dates.add(m.group(1))
        if len(batch) < 100:
            return dates
        page += 1


def clean_caption(caption: str) -> list[str]:
    keep = []
    for line in caption.split("\n"):
        line = EMOJI.sub("", line).strip()
        if not line or line.startswith("#") or "link in bio" in line.lower() or "in my bio" in line.lower():
            continue
        keep.append(line)
    return keep


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f"Poppins-{weight}.ttf"), size)


def pin_image(day: str, cover_url: str, out: Path) -> None:
    W, H = 1000, 1500
    img = Image.new("RGB", (W, H), PAPER)
    cover = Image.open(io.BytesIO(requests.get(cover_url, timeout=60).content)).convert("RGB")
    cover = cover.resize((W, round(W * cover.height / cover.width)), Image.LANCZOS)
    img.paste(cover, (0, 0))
    d = ImageDraw.Draw(img)
    top = cover.height
    d.rectangle((0, top, W, H), fill=INK)
    f1, f2 = font("ExtraBold", 54), font("SemiBold", 34)
    t1, t2 = "Free copy-paste AI prompts", "tessaturing.github.io"
    mid = top + (H - top) / 2
    d.text(((W - d.textlength(t1, font=f1)) / 2, mid - 62), t1, font=f1, fill=(255, 255, 255))
    d.text(((W - d.textlength(t2, font=f2)) / 2, mid + 14), t2, font=f2, fill=(247, 222, 226))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=88)


CSS = """
:root{--paper:#fcfaf8;--ink:#2b2420;--soft:#554c46;--rose:#be546e;--blush:#f7dee2;--sky:#dce8f6;--sage:#d6e4d8}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:18px/1.6 Poppins,system-ui,sans-serif}
a{color:var(--rose)}.wrap{max-width:720px;margin:0 auto;padding:24px 16px 64px}
header{display:flex;align-items:center;gap:14px;margin-bottom:24px}header img{width:56px;height:56px;border-radius:50%}
header a{color:var(--ink);text-decoration:none;font-weight:700}header small{display:block;color:var(--soft);font-weight:500}
h1{font-size:34px;line-height:1.2;margin:8px 0 12px}h2{font-size:22px;margin:28px 0 8px}
.kicker{color:var(--rose);font-weight:700;font-size:14px;letter-spacing:.06em;text-transform:uppercase}
.prompt{background:var(--blush);border-radius:14px;padding:16px 18px;margin:10px 0;white-space:pre-wrap}
.cta{background:#fff;border-radius:18px;padding:22px;margin:36px 0;box-shadow:0 2px 14px rgba(43,36,32,.08)}
.btn{display:inline-block;background:var(--ink);color:#fff;text-decoration:none;padding:12px 20px;border-radius:999px;margin:6px 8px 6px 0;font-weight:600}
.btn.alt{background:var(--rose)}.list a{display:flex;gap:14px;align-items:center;text-decoration:none;color:var(--ink);padding:12px 0;border-bottom:1px solid #eee}
.list img{width:84px;height:105px;object-fit:cover;border-radius:10px}.slides img{width:100%;border-radius:14px;margin:8px 0}
footer{color:var(--soft);font-size:14px;margin-top:40px}
"""


def page(title: str, description: str, body: str, canonical: str, image: str | None = None, verify: str = "") -> str:
    og = f'<meta property="og:image" content="{image}">' if image else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(description)}">
<link rel="canonical" href="{canonical}"><meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">{og}{verify}
<link rel="alternate" type="application/rss+xml" title="Tessa Turing tips" href="{SITE}/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css"></head><body><div class="wrap">
<header><img src="/assets/tessa.jpg" alt="Tessa Turing"><div><a href="/">Tessa Turing</a><small>{TAGLINE}</small></div></header>
{body}
<div class="cta"><h2 style="margin-top:0">Want more like this?</h2>
<p>Grab my free <b>10 AI Shortcuts</b> guide, or practice step by step with the large-print <b>AI Made Simple</b> 7-day workbook.</p>
<a class="btn" href="{STORE}">Get the free guide</a><a class="btn alt" href="{STORE}">See the workbook</a></div>
<footer>Follow <a href="https://www.instagram.com/tessa_turing/">@tessa_turing</a> on Instagram and
<a href="https://www.threads.com/@tessa_turing">Threads</a>, and <a href="https://www.facebook.com/tessaturing">on Facebook</a>.
General information only, not legal, financial or medical advice.</footer></div></body></html>
"""


def slide_html(s: dict) -> str:
    out = []
    if s.get("kicker"):
        out.append(f'<div class="kicker">{html.escape(s["kicker"])}</div>')
    if s.get("title"):
        out.append(f"<h2>{html.escape(s['title'])}</h2>")
    if s.get("body"):
        out.append(f"<p>{html.escape(s['body'])}</p>")
    if s.get("prompt"):
        out.append(f'<div class="prompt">{html.escape(s["prompt"])}</div>')
    return "\n".join(out)


def main() -> None:
    verify = (ROOT / "pinterest-verify.txt").read_text().strip() if (ROOT / "pinterest-verify.txt").exists() else ""
    verify_tag = f'<meta name="p:domain_verify" content="{html.escape(verify)}"/>' if verify else ""
    history = requests.get(f"{RAW}/content/history.json", timeout=60).json()
    done = posted_dates()
    entries = []
    for h in history:
        day = h["date"]
        if day not in done:
            continue
        r = requests.get(f"{RAW}/drafts/{day}/post.json", timeout=60)
        if r.status_code != 200:
            continue
        post = r.json()
        lines = clean_caption(post["caption"])
        slides = post.get("slides") or []
        title = (slides[0]["title"] if slides and slides[0].get("title") else (lines[0] if lines else post["topic"]))
        title = title.rstrip("?!. ") + ("?" if title.strip().endswith("?") else "")
        desc = " ".join(lines[:3])[:280]
        pin = ROOT / "pins" / f"{day}.jpg"
        if not pin.exists():
            pin_image(day, f"{RAW}/{post['images'][0]}", pin)
        if slides:
            body = "\n".join(slide_html(s) for s in slides[1:] if s.get("type") != "cta")
        else:
            body = '<div class="slides">' + "".join(
                f'<img src="{RAW}/{p}" alt="Slide {i + 1}" loading="lazy">' for i, p in enumerate(post["images"])) + "</div>"
        body = f"<h1>{html.escape(title)}</h1><p>{html.escape(' '.join(lines[1:4]))}</p>{body}"
        url = f"{SITE}/tips/{day}/"
        out = ROOT / "tips" / day / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(f"{title} | Tessa Turing", desc, body, url, f"{SITE}/pins/{day}.jpg", verify_tag))
        entries.append({"day": day, "title": title, "desc": desc, "url": url, "pin": f"{SITE}/pins/{day}.jpg"})

    entries.sort(key=lambda e: e["day"], reverse=True)
    items = "".join(
        f'<a href="/tips/{e["day"]}/"><img src="/pins/{e["day"]}.jpg" alt="" loading="lazy">'
        f'<span><b>{html.escape(e["title"])}</b><br><small>{html.escape(e["desc"][:110])}</small></span></a>' for e in entries)
    home = (f"<h1>{TAGLINE}</h1><p>Copy-paste AI prompts for letters, bills, family plans and the AI already on "
            f"your phone, explained one step at a time.</p><div class=\"list\">{items}</div>")
    (ROOT / "index.html").write_text(page(f"Tessa Turing | {TAGLINE}", TAGLINE, home, f"{SITE}/", None, verify_tag))
    (ROOT / "style.css").write_text(CSS)

    def rss_date(day: str) -> str:
        return format_datetime(dt.datetime.fromisoformat(day[:10]).replace(hour=14, tzinfo=dt.timezone.utc))

    rss_items = "".join(
        f"<item><title>{html.escape(e['title'])}</title><link>{e['url']}</link><guid>{e['url']}</guid>"
        f"<pubDate>{rss_date(e['day'])}</pubDate><description>{html.escape(e['desc'])}</description>"
        f'<enclosure url="{e["pin"]}" type="image/jpeg" length="0"/>'
        f'<media:content url="{e["pin"]}" medium="image" type="image/jpeg"/></item>' for e in entries[:50])
    (ROOT / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">'
        f"<channel><title>Tessa Turing | AI tips</title><link>{SITE}/</link><description>{TAGLINE}</description>"
        f"{rss_items}</channel></rss>\n")
    print(f"Built {len(entries)} tip pages")


if __name__ == "__main__":
    main()
