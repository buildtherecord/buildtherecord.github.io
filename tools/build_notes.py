#!/usr/bin/env python3
"""
Render field notes from notes-src/*.md into notes/*.html, plus a browse index.

Field notes are the universal craft layer — how to capture evidence, what to do
when you didn't, what to understand about the tools. Unlike jurisdiction records
they need no per-state research, so they are publishable immediately with no
crowdsourcing at all.

Markdown subset, deliberately small: frontmatter, ## headings, paragraphs,
- lists, numbered **bold** list items, > blockquotes, **bold**, *italic*, `code`.

Usage:  python3 tools/build_notes.py
"""

import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SRC = os.path.join(SITE, "notes-src")
OUT = os.path.join(SITE, "notes")

CSS = """
:root{--ink:#111;--mut:#555;--soft:#dcdcdc;--wash:#f5f5f5;}
*{box-sizing:border-box;-webkit-text-size-adjust:100%;}
body{font:17.5px/1.68 -apple-system,"Helvetica Neue",Helvetica,Arial,sans-serif;
  color:var(--ink);margin:0;background:#fff;}
a{color:var(--ink);text-underline-offset:2px;}
.wrap{max-width:680px;margin:0 auto;padding:0 20px 80px;}
.crumb{font-size:12px;letter-spacing:.16em;text-transform:uppercase;padding:22px 0 0;}
.mast{border-bottom:2px solid var(--ink);padding:14px 0 22px;margin-bottom:26px;}
h1{font-size:clamp(27px,6.2vw,38px);line-height:1.1;margin:0 0 12px;letter-spacing:-.01em;}
.short{font-size:17px;color:var(--mut);margin:0;}
h2{font-size:19px;line-height:1.28;margin:38px 0 10px;}
p{margin:0 0 16px;}
ul,ol{margin:0 0 16px;padding-left:22px;}
li{margin-bottom:11px;}
blockquote{border-left:3px solid var(--ink);margin:22px 0;padding:2px 0 2px 20px;
  font-size:18px;}
blockquote p:last-child{margin-bottom:0;}
code{background:var(--wash);padding:1px 5px;font-size:.9em;}
strong{font-weight:700;}
.next{border:1px solid var(--ink);padding:18px 20px;margin-top:44px;}
.next b{display:block;font-size:11px;letter-spacing:.14em;text-transform:uppercase;
  margin-bottom:9px;}
.next a{display:block;padding:7px 0;font-size:16px;}
.note{border:1px solid var(--ink);padding:15px 18px;font-size:14.5px;margin-top:30px;}
.note b{display:block;font-size:11px;letter-spacing:.14em;text-transform:uppercase;margin-bottom:5px;}
footer{background:var(--ink);color:#fff;margin-top:56px;}
footer .fw{max-width:680px;margin:0 auto;padding:22px 20px;font-size:13.5px;}
footer a{color:#fff;}
"""


def parse(path):
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", raw, re.S)
    meta, body = {}, raw
    if m:
        for line in m.group(1).split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        body = m.group(2)
    return meta, body.strip()


def inline(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s, flags=re.S)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", s, flags=re.S)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s, flags=re.S)
    return s


def render(body):
    out, buf, items, quote = [], [], [], []
    mode = None  # p | ul | ol | quote

    def flush():
        nonlocal mode
        if mode == "p" and buf:
            out.append("<p>" + inline(" ".join(buf)) + "</p>")
        elif mode in ("ul", "ol") and items:
            tag = mode
            out.append(f"<{tag}>" + "".join(f"<li>{inline(i)}</li>" for i in items) + f"</{tag}>")
        elif mode == "quote" and quote:
            inner = "".join(f"<p>{inline(p)}</p>" for p in quote if p.strip())
            out.append(f"<blockquote>{inner}</blockquote>")
        buf.clear(); items.clear(); quote.clear(); mode = None

    for ln in body.split("\n"):
        t = ln.strip()
        if not t:
            flush()
        elif t.startswith("## "):
            flush(); out.append(f"<h2>{inline(t[3:])}</h2>")
        elif t.startswith("> "):
            # Consecutive "> " lines are ONE paragraph — markdown soft-wraps, and
            # splitting them mid-sentence breaks **bold** spans across paragraphs.
            if mode != "quote":
                flush(); mode = "quote"; quote.append(t[2:])
            elif quote and quote[-1]:
                quote[-1] += " " + t[2:]
            else:
                quote.append(t[2:])
        elif t == ">":
            if mode == "quote":
                quote.append("")   # bare ">" is the paragraph break
        elif re.match(r"^\d+\.\s", t):
            if mode != "ol":
                flush(); mode = "ol"
            items.append(re.sub(r"^\d+\.\s", "", t))
        elif t.startswith("- "):
            if mode != "ul":
                flush(); mode = "ul"
            items.append(t[2:])
        elif mode in ("ul", "ol"):
            items[-1] += " " + t
        elif mode == "quote":
            if quote and quote[-1]:
                quote[-1] += " " + t
            else:
                quote.append(t)
        else:
            mode = "p"; buf.append(t)
    flush()
    # collapse the blank-line marker used to split blockquote paragraphs
    return "\n".join(o for o in out if o and o != "<p></p>")


def page(meta, body_html, others, slug):
    e = html.escape
    nav = "".join(
        f'<a href="/notes/{s}.html">{e(m["title"])}</a>'
        for s, m in others if s != slug)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="canonical" href="https://buildtherecord.org/notes/{slug}.html">
<title>{e(meta['title'])} — Build the Record</title>
<meta name="description" content="{e(meta.get('short',''))}">
<style>{CSS}</style></head><body>
<div class="wrap">
<div class="crumb"><a href="/">Build the Record</a> / <a href="/browse.html">Notes</a></div>
<header class="mast">
<h1>{e(meta['title'])}</h1>
<p class="short">{e(meta.get('short',''))}</p>
</header>
{body_html}
<div class="note"><b>Not legal advice</b>
This is practical guidance on collecting and keeping evidence, not advice about
your case. Rules vary by state. When it matters, bring what you have to a lawyer —
your state bar runs a referral service, and
<a href="https://www.lawhelp.org">lawhelp.org</a> lists free and low-cost help.</div>
<div class="next"><b>Other notes</b>{nav}
<a href="/start.html">&rarr; Start building your record</a></div>
</div>
<footer><div class="fw"><a href="/">buildtherecord.org</a> &middot;
<a href="/browse.html">Everything</a> &middot; Free and open. Volunteer-run.</div></footer>
</body></html>"""


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    notes = []
    for fn in sorted(os.listdir(SRC)):
        if fn.endswith(".md"):
            meta, body = parse(os.path.join(SRC, fn))
            notes.append((fn[:-3], meta, body))
    notes.sort(key=lambda n: int(n[1].get("order", 99)))
    index = [(s, m) for s, m, _ in notes]

    for slug, meta, body in notes:
        p = os.path.join(OUT, f"{slug}.html")
        open(p, "w", encoding="utf-8").write(page(meta, render(body), index, slug))
        print(f"wrote notes/{slug}.html  ({os.path.getsize(p):,} bytes)")
