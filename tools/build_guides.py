#!/usr/bin/env python3
"""
Generate phone-first step guides from the method repos' prompt files.

Reads ../<repo>/prompts/*.md and emits guide/<slug>.html — one mobile-first page
per method, each step with a large copy button and the full prompt inline.

Design constraints (deliberate, see DECISIONS.md D015):
  * NO deep links carrying the prompt in a URL. Verified 2026-08-16: a phone user
    with the ChatGPT app installed lands in an EMPTY app; Copilot strips ?q= at
    the edge; Gemini never supported it; Claude's web ?q= is undocumented and has
    broken before. Copy-to-clipboard is the only path that never silently fails.
  * Assistant links are plain homepage links. They cannot break.
  * No build-time dependency beyond the stdlib. No runtime JS framework.

Usage:  python3 tools/build_guides.py
"""

import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
REPOS = os.path.dirname(SITE)          # .../org  -> we need one more up
ROOT = os.path.dirname(REPOS)          # .../repo  (holds the three method repos)
OUT = os.path.join(SITE, "guide")

# ---------------------------------------------------------------- methods ----

METHODS = [
    {
        "slug": "car",
        "repo": "lemon-case-file",
        "title": "Car or truck that keeps breaking",
        "short": "Vehicle defects &amp; lemon law",
        "who": "You bought or leased a vehicle, something keeps going wrong, and "
               "the dealer or manufacturer has not fixed it.",
        "demo": "/lemon-case-file/",
        "steps": {
            "01": ("Make a list of everything you have",
                   "Photos, videos, receipts, texts, emails, repair orders — one catalogue, nothing renamed."),
            "02": ("Put it all on a timeline",
                   "Every event in date order, in one file the rest of the work is built from."),
            "03": ("Track every repair attempt",
                   "What broke, what they said they did, and how many times it came back."),
            "04": ("Rebuild your call history",
                   "Who you called, when, and what was said — from records you actually have."),
            "05": ("Ask them for their own records",
                   "Manufacturers keep diagnostic logs. Request them before you argue with them."),
            "06": ("Build a private evidence website",
                   "Optional and technical. A password-protected site you can share with one link."),
            "07": ("Make the printable case file",
                   "One PDF with a numbered index of every exhibit."),
            "08": ("Attack your own case before they do",
                   "Have the assistant argue the other side, then fix what it finds."),
            "09": ("Remove private information",
                   "Scrub anything personal before a document leaves your hands."),
            "10": ("Write the email that sends it",
                   "Short cover message, and how to tell whether anyone read it."),
        },
    },
    {
        "slug": "insurance",
        "repo": "health-insurance-case-file",
        "title": "Health insurance denied your claim",
        "short": "Health-insurance denials",
        "who": "Your insurer refused to pay for care, or refused to approve it in "
               "advance, and you want to appeal.",
        "demo": "/health-insurance-case-file/",
        "urgent": "Appeals have hard deadlines — often 180 days, sometimes much less. "
                  "Start at step 2 if a letter arrived recently.",
        "steps": {
            "01": ("Make a list of every document",
                   "Letters, EOBs, portal downloads, bills — with the decisive line quoted."),
            "02": ("Find your deadlines — do this first",
                   "What kind of plan you have, and exactly how many days you have left."),
            "03": ("Understand exactly why they said no",
                   "Pull apart the denial letter and find what standard they actually applied."),
            "04": ("Ask for their file on you",
                   "The claim file shows how the decision was made. Request it before appealing."),
            "05": ("Build the appeal",
                   "The packet: what you are appealing, why, and every document that proves it."),
            "06": ("Take it to an outside reviewer",
                   "If the internal appeal fails, an independent reviewer can overturn them."),
            "07": ("Involve the regulator",
                   "Who oversees your plan, and what they can actually do."),
            "08": ("Attack your own appeal first",
                   "Have the assistant argue the insurer's side, then fix what it finds."),
            "09": ("Make the printable packet",
                   "One PDF, properly indexed, ready to send."),
            "10": ("Prove you sent it, track what happens",
                   "Delivery proof and a record of every response."),
        },
    },
    {
        "slug": "contractor",
        "repo": "contractor-case-file",
        "title": "Contractor took your money",
        "short": "Contractor disputes",
        "who": "You hired someone for work on your home, paid them, and the work is "
               "unfinished, defective, or never started.",
        "demo": "/contractor-case-file/",
        "steps": {
            "01": ("Read the contract for what is missing",
                   "Many home-repair contracts are missing terms the law requires."),
            "02": ("Compare what you paid to what you got",
                   "Money out versus work actually completed, line by line."),
            "03": ("Track every promise and when it broke",
                   "Each date they gave you, and what happened on that date."),
            "04": ("Document the actual work",
                   "Photos and their own words about the state of the job."),
            "05": ("Pull the public permit record",
                   "Permits and inspections are public. They often contradict the story."),
            "06": ("Write the demand letter",
                   "A factual letter stating what you paid, what you got, and what you want."),
            "07": ("Build the packet",
                   "Two versions — a short one to send, a complete one for a lawyer."),
            "08": ("Attack your own case first",
                   "Have the assistant argue the contractor's side, then fix what it finds."),
            "09": ("Know your escalation options",
                   "Licensing board, bond claim, small claims — what each can actually do."),
            "10": ("Build a private evidence website",
                   "Optional and technical. Rarely needed."),
        },
    },
]

# ------------------------------------------------------------------ parse ----


def parse_prompt(path):
    """Return (copyable_prompt, afterward) from a prompt markdown file."""
    raw = open(path, encoding="utf-8").read()

    # Strip the H1 title line.
    body = re.sub(r"\A#\s+[^\n]*\n", "", raw)

    # The copyable prompt is the block fenced by the first pair of '---' lines.
    parts = re.split(r"^---\s*$", body, flags=re.M)
    if len(parts) >= 3:
        prompt = parts[1].strip()
        tail = "---".join(parts[2:])
    else:
        prompt = body.strip()
        tail = ""

    # Trailing guidance appears under several headings across the repos:
    # "Afterward", "Checklist for you afterward", "Sending mechanics", "Why", etc.
    # Take everything from the first H2 in the tail; stop at any later H2 so a
    # single note stays short enough to read on a phone.
    after = ""
    m = re.search(r"^##\s+([^\n]+)\n(.*?)(?=^##\s|\Z)", tail, flags=re.M | re.S)
    if m:
        heading, body = m.group(1).strip(), m.group(2).strip()
        after = body
        # Keep a non-generic heading as a lead-in so the note reads correctly.
        if not re.match(r"^(afterward|checklist for you afterward)$", heading, re.I):
            after = f"**{heading}.** {body}"
    return prompt, after


def ground_rules(path):
    """Pull the blockquoted ground-rules block out of 00-START-HERE.md."""
    raw = open(path, encoding="utf-8").read()
    lines, block, grabbing = raw.split("\n"), [], False
    for ln in lines:
        if ln.startswith(">"):
            grabbing = True
            block.append(re.sub(r"^>\s?", "", ln))
        elif grabbing:
            break
    return "\n".join(block).strip()


def md_inline(s):
    """Minimal markdown -> HTML for prose we control: **bold**, `code`."""
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s, flags=re.S)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s, flags=re.S)
    return s


def md_block(s):
    """Paragraphs + bullet lists, honouring wrapped continuation lines.

    Markdown soft-wraps: a bullet's text may continue on the following indented
    (or merely non-empty) line. Treat any non-empty line that is not itself a new
    bullet as a continuation of whatever is currently open.
    """
    out, buf, items = [], [], []
    mode = None  # 'p' | 'ul'

    def flush():
        nonlocal mode
        if mode == "p" and buf:
            out.append("<p>" + md_inline(" ".join(buf)) + "</p>")
        elif mode == "ul" and items:
            out.append("<ul>" + "".join(f"<li>{md_inline(i)}</li>" for i in items) + "</ul>")
        buf.clear(); items.clear(); mode = None

    for ln in s.split("\n"):
        t = ln.strip()
        if not t:
            flush()
        elif re.match(r"^[-*]\s+", t):
            if mode != "ul":
                flush(); mode = "ul"
            items.append(re.sub(r"^[-*]\s+", "", t))
        elif mode == "ul":
            items[-1] += " " + t          # continuation of the open bullet
        else:
            mode = "p"; buf.append(t)
    flush()
    return "\n".join(out)


# ------------------------------------------------------------------- CSS -----

CSS = """
:root{--ink:#111;--mut:#555;--hair:#111;--soft:#dcdcdc;--wash:#f4f4f4;}
*{box-sizing:border-box;-webkit-text-size-adjust:100%;}
body{font:17px/1.6 -apple-system,"Helvetica Neue",Helvetica,Arial,sans-serif;
  color:var(--ink);margin:0;background:#fff;}
a{color:var(--ink);text-underline-offset:2px;}
.wrap{max-width:720px;margin:0 auto;padding:0 20px 80px;}
.crumb{font-size:12px;letter-spacing:.16em;text-transform:uppercase;padding:22px 0 0;}
.mast{border-bottom:2px solid var(--hair);padding:14px 0 22px;margin-bottom:8px;}
.mast h1{font-size:clamp(26px,6.5vw,38px);line-height:1.1;margin:0 0 10px;
  letter-spacing:-.01em;text-transform:uppercase;}
.who{font-size:16px;color:var(--mut);margin:0;}
.urgent{border:2px solid var(--ink);padding:14px 16px;margin:24px 0 0;font-size:15.5px;}
.urgent b{text-transform:uppercase;font-size:12px;letter-spacing:.14em;display:block;margin-bottom:5px;}
.sec{margin-top:38px;}
.sec>h2{font-size:12px;letter-spacing:.18em;text-transform:uppercase;margin:0 0 4px;font-weight:700;}
.rule{border:0;border-top:1px solid var(--hair);margin:0 0 18px;}
.lede{font-size:16.5px;max-width:620px;}
ol.plain{padding-left:20px;margin:0;}
ol.plain li{margin-bottom:10px;}
.step{border:1px solid var(--hair);margin:0 0 18px;}
.step-h{display:flex;gap:14px;padding:16px 16px 12px;align-items:baseline;}
.step-n{font:700 13px/1 ui-monospace,SFMono-Regular,Menlo,monospace;
  border:1px solid var(--ink);padding:6px 8px;flex:none;}
.step-t{margin:0;font-size:18px;line-height:1.3;}
.step-d{color:var(--mut);font-size:14.5px;margin:2px 0 0;}
.step-b{padding:0 16px 16px;}
.btn{display:block;width:100%;border:2px solid var(--ink);background:var(--ink);color:#fff;
  font:700 15px/1 inherit;letter-spacing:.06em;text-transform:uppercase;
  padding:16px;cursor:pointer;text-align:center;border-radius:0;
  -webkit-appearance:none;min-height:52px;}
.btn:active{background:#fff;color:var(--ink);}
.btn.sec2{background:#fff;color:var(--ink);margin-top:9px;}
.btn.sec2:active{background:var(--ink);color:#fff;}
.said{font-size:13.5px;color:var(--mut);text-align:center;margin:9px 0 0;min-height:19px;}
details{margin-top:12px;border-top:1px solid var(--soft);padding-top:11px;}
summary{font-size:13px;letter-spacing:.1em;text-transform:uppercase;font-weight:700;
  cursor:pointer;padding:13px 0;min-height:44px;display:flex;align-items:center;}
pre{white-space:pre-wrap;word-wrap:break-word;overflow-wrap:break-word;background:var(--wash);
  border:1px solid var(--soft);padding:14px;font:14px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;
  margin:10px 0 0;}
.after{background:var(--wash);border-left:3px solid var(--ink);padding:11px 14px;margin-top:12px;font-size:14.5px;}
.after b{text-transform:uppercase;font-size:11px;letter-spacing:.14em;display:block;margin-bottom:4px;}
.after p{margin:0 0 8px;} .after p:last-child{margin:0;}
.after ul{margin:0;padding-left:18px;}
.tools{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px;}
.tool{border:1px solid var(--hair);padding:14px 10px;text-align:center;font-size:14px;
  text-decoration:none;font-weight:700;min-height:50px;display:flex;align-items:center;justify-content:center;}
.tool:active{background:var(--ink);color:#fff;}
.note{border:1px solid var(--hair);padding:15px 17px;font-size:14.5px;}
.note b{font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;display:block;margin-bottom:5px;}
footer{background:var(--ink);color:#fff;margin-top:56px;}
footer .fw{max-width:720px;margin:0 auto;padding:22px 20px;font-size:13.5px;}
footer a{color:#fff;}
code{background:var(--wash);padding:1px 4px;font-size:.92em;}
@media(min-width:620px){ .tools{grid-template-columns:repeat(4,1fr);} }
"""

JS = """
function copyStep(id, btn){
  var el = document.getElementById(id);
  var txt = el.textContent;
  var note = document.getElementById('said-' + id);
  function ok(){ note.textContent = 'Copied. Now open your assistant below and paste.';
                 btn.textContent = 'Copied \\u2713'; setTimeout(function(){
                 btn.textContent = btn.getAttribute('data-label'); }, 2600); }
  function fail(){ note.textContent = 'Could not copy automatically \\u2014 open the prompt below, then press and hold to select it.'; }
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(txt).then(ok, function(){ legacy(); });
  } else { legacy(); }
  function legacy(){
    try{
      var ta = document.createElement('textarea');
      ta.value = txt; ta.setAttribute('readonly','');
      ta.style.position='fixed'; ta.style.top='0'; ta.style.opacity='0';
      document.body.appendChild(ta); ta.select(); ta.setSelectionRange(0, 999999);
      var good = document.execCommand('copy'); document.body.removeChild(ta);
      good ? ok() : fail();
    } catch(e){ fail(); }
  }
}
"""

TOOLS = [
    ("Claude", "https://claude.ai/"),
    ("ChatGPT", "https://chatgpt.com/"),
    ("Gemini", "https://gemini.google.com/"),
    ("Perplexity", "https://www.perplexity.ai/"),
]


def tools_html():
    return ('<div class="tools">'
            + "".join(f'<a class="tool" href="{u}" target="_blank" rel="noopener">{n}</a>'
                      for n, u in TOOLS)
            + "</div>")


# ------------------------------------------------------------------ build ----


def build(m):
    repo = os.path.join(ROOT, m["repo"])
    pdir = os.path.join(repo, "prompts")
    rules = ground_rules(os.path.join(pdir, "00-START-HERE.md"))

    out = [f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="canonical" href="https://buildtherecord.org/guide/{m['slug']}.html">
<title>{m['title']} — Build the Record</title>
<meta name="description" content="Step-by-step, on your phone. {html.escape(m['who'])}">
<style>{CSS}</style></head><body>
<div class="wrap">
<div class="crumb"><a href="/">Build the Record</a> / <a href="/start.html">Start</a></div>
<header class="mast">
<h1>{m['title']}</h1>
<p class="who">{m['who']}</p>
</header>
"""]

    if m.get("urgent"):
        out.append(f'<div class="urgent"><b>If a deadline is near</b>{m["urgent"]}</div>')

    out.append(f"""
<section class="sec">
<h2>How this works</h2><hr class="rule">
<ol class="plain">
<li><strong>Open an AI assistant</strong> in another tab or app. Claude, ChatGPT,
Gemini and Perplexity all have free versions. Any of them works.</li>
<li><strong>Copy step 0 below and paste it in.</strong> That sets the rules.</li>
<li><strong>Work through the steps in order.</strong> Copy, paste, then answer its
questions and give it your documents when it asks.</li>
</ol>
<p class="lede" style="margin-top:14px">Each step builds on the one before it, so
order matters. You do not have to finish in one sitting — the assistant can pick up
where you left off if you tell it what you already did. Expect several hours across
several days, not minutes.</p>
{tools_html()}
</section>

<section class="sec">
<h2>Step 0 — the rules</h2><hr class="rule">
<div class="step">
<div class="step-h"><span class="step-n">0</span>
<div><h3 class="step-t">Paste this first, before anything else</h3>
<p class="step-d">Tells the assistant how to behave: no invented facts, no guessing, quote things exactly.</p></div></div>
<div class="step-b">
<button class="btn" data-label="Copy step 0" onclick="copyStep('p-00', this)">Copy step 0</button>
<p class="said" id="said-p-00"></p>
<details><summary>Show the text</summary><pre id="p-00">{html.escape(rules)}</pre></details>
</div></div>
</section>

<section class="sec">
<h2>The steps</h2><hr class="rule">
""")

    for fn in sorted(os.listdir(pdir)):
        if not re.match(r"^\d\d-", fn) or fn.startswith("00-"):
            continue
        num = fn[:2]
        if num not in m["steps"]:
            continue
        title, desc = m["steps"][num]
        prompt, after = parse_prompt(os.path.join(pdir, fn))
        pid = f"p-{num}"
        label = f"Copy step {int(num)}"

        out.append(f"""<div class="step">
<div class="step-h"><span class="step-n">{int(num)}</span>
<div><h3 class="step-t">{html.escape(title)}</h3>
<p class="step-d">{html.escape(desc)}</p></div></div>
<div class="step-b">
<button class="btn" data-label="{label}" onclick="copyStep('{pid}', this)">{label}</button>
<p class="said" id="said-{pid}"></p>
<details><summary>Show the text</summary><pre id="{pid}">{html.escape(prompt)}</pre></details>
""")
        if after:
            out.append(f'<div class="after"><b>After this step</b>{md_block(after)}</div>')
        out.append("</div></div>\n")

    out.append(f"""</section>

<section class="sec">
<h2>What a finished one looks like</h2><hr class="rule">
<p class="lede" style="margin-top:0">There is a complete demonstration case file —
made up, but the real shape of the result.</p>
<p style="margin-top:12px"><a class="tool" style="display:inline-flex;padding:14px 20px"
href="{m['demo']}">See the example</a></p>
</section>

<section class="sec">
<div class="note"><b>Not legal advice</b>
This is a method for organizing your own evidence. It is not a lawyer and cannot
tell you whether you will win. Deadlines are real and they vary by state — never
take one from here, always check it against the official source. If what you are
facing is serious, bring the record you build to a lawyer. That is half of what it
is for. Your state bar association and <a href="https://www.lawhelp.org">lawhelp.org</a>
can point you to free and low-cost help.</div>
</section>

</div>
<footer><div class="fw">
<a href="/">buildtherecord.org</a> &middot; <a href="/start.html">Start over</a>
&middot; Free and open. Volunteer-run.
</div></footer>
<script>{JS}</script>
</body></html>""")

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{m['slug']}.html")
    open(path, "w", encoding="utf-8").write("".join(out))
    return path


if __name__ == "__main__":
    for m in METHODS:
        p = build(m)
        print(f"wrote {os.path.relpath(p, SITE)}  ({os.path.getsize(p):,} bytes)")
