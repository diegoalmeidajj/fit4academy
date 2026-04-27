#!/usr/bin/env python3
"""Build BRAND_PLAYBOOK.pdf from BRAND_PLAYBOOK.md using Chrome headless."""

import os
import subprocess
import sys

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD_PATH = os.path.join(ROOT, 'BRAND_PLAYBOOK.md')
HTML_PATH = os.path.join(ROOT, 'BRAND_PLAYBOOK.html')
PDF_PATH = os.path.join(ROOT, 'BRAND_PLAYBOOK.pdf')

CSS = """
@page { size: Letter; margin: 0.7in 0.6in; }
* { box-sizing: border-box; }
html, body {
  font-family: 'DM Sans', -apple-system, system-ui, Helvetica, Arial, sans-serif;
  color: #0f172a;
  font-size: 10.5pt;
  line-height: 1.55;
  margin: 0;
  padding: 0;
  background: #fff;
}
.cover {
  page-break-after: always;
  height: 9.5in;
  background: linear-gradient(160deg, #0f172a 0%, #0a0f1a 60%, #001a10 100%);
  color: #fff;
  padding: 1.5in 1in;
  position: relative;
}
.cover .mark {
  width: 96px; height: 96px; border-radius: 22px;
  background: linear-gradient(135deg, #00DC82, #00B368);
  display: flex; align-items: center; justify-content: center;
  font-family: 'Space Grotesk', -apple-system, system-ui, sans-serif;
  font-weight: 800; font-size: 38px; color: #fff;
  box-shadow: 0 14px 40px rgba(0,220,130,0.35);
  margin-bottom: 36px;
  letter-spacing: -2px;
}
.cover h1 {
  font-family: 'Space Grotesk', -apple-system, system-ui, sans-serif;
  font-size: 56pt; font-weight: 700; letter-spacing: -2px;
  margin: 0 0 12px 0; line-height: 1.0;
}
.cover h1 em {
  font-style: normal;
  background: linear-gradient(135deg, #6ee7b7, #22d3ee);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;
}
.cover .sub {
  font-size: 14pt; color: rgba(255,255,255,0.7);
  margin-bottom: 60px; max-width: 6in; line-height: 1.4;
}
.cover .meta {
  position: absolute; bottom: 1in; left: 1in; right: 1in;
  display: flex; justify-content: space-between; align-items: flex-end;
  font-size: 10pt; color: rgba(255,255,255,0.5);
  border-top: 1px solid rgba(255,255,255,0.1);
  padding-top: 18px;
}
.cover .meta strong { color: #6ee7b7; font-weight: 600; }
.cover .badges { display: flex; gap: 10px; margin-top: 24px; flex-wrap: wrap; }
.cover .badge {
  padding: 6px 14px; border-radius: 999px;
  border: 1px solid rgba(110,231,183,0.4);
  color: #6ee7b7; font-size: 9pt; font-weight: 600;
  letter-spacing: 0.5px;
}

.content { padding: 0.2in 0; }
h1, h2, h3, h4 {
  font-family: 'Space Grotesk', -apple-system, system-ui, sans-serif;
  color: #0f172a;
  letter-spacing: -0.5px;
  page-break-after: avoid;
}
h1 {
  font-size: 28pt; font-weight: 800;
  margin: 0 0 8pt; padding-bottom: 10pt;
  border-bottom: 3px solid #00DC82;
  letter-spacing: -1px;
}
h2 {
  font-size: 20pt; font-weight: 700;
  margin: 0 0 14pt; padding-bottom: 6pt;
  color: #0f172a;
  border-bottom: 1px solid #00DC82;
  break-before: page;
  page-break-after: avoid;
}
h2:first-of-type { page-break-before: avoid; }
h3 {
  font-size: 13pt; font-weight: 700; margin: 18pt 0 6pt;
  color: #00B368;
}
h4 {
  font-size: 11pt; font-weight: 700; margin: 12pt 0 4pt;
  color: #475569; text-transform: uppercase; letter-spacing: 0.6px;
}
p { margin: 0 0 8pt 0; color: #334155; }
strong { color: #0f172a; font-weight: 700; }
em { color: #00B368; font-style: italic; }
ul, ol { margin: 0 0 10pt 0; padding-left: 22px; }
li { margin: 0 0 3pt 0; color: #334155; }
li::marker { color: #00DC82; }

a { color: #00B368; text-decoration: none; font-weight: 600; }
a:hover { text-decoration: underline; }

code {
  font-family: 'SF Mono', Menlo, Monaco, Consolas, monospace;
  background: #f1f5f9;
  color: #0f172a;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 9pt;
  font-weight: 500;
}
pre {
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 10px;
  padding: 14pt 16pt;
  overflow-x: auto;
  margin: 8pt 0 12pt 0;
  font-size: 8.5pt;
  line-height: 1.5;
  page-break-inside: avoid;
}
pre code {
  background: transparent;
  color: inherit;
  padding: 0;
  font-size: inherit;
}

blockquote {
  border-left: 3px solid #00DC82;
  background: rgba(0,220,130,0.05);
  margin: 10pt 0;
  padding: 10pt 14pt;
  color: #475569;
  font-style: italic;
  border-radius: 0 8px 8px 0;
  page-break-inside: avoid;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 8pt 0 12pt 0;
  font-size: 9.5pt;
  page-break-inside: avoid;
}
th {
  background: #0f172a;
  color: #fff;
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700;
  text-align: left;
  padding: 7pt 10pt;
  font-size: 9pt;
  letter-spacing: 0.3px;
}
th:first-child { border-top-left-radius: 6px; }
th:last-child { border-top-right-radius: 6px; }
td {
  padding: 7pt 10pt;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: top;
  color: #334155;
}
tr:nth-child(even) td { background: #f8fafc; }
tr:last-child td { border-bottom: none; }

hr {
  border: none;
  border-top: 1px solid #e2e8f0;
  margin: 22pt 0;
}

.page-break {
  page-break-after: always;
  break-after: page;
  height: 0;
  display: block;
}

/* TOC styling */
ol li a, ul li a { color: #0f172a; }

/* Inline highlights for hex codes */
code:has(+ code) { /* nope, use generic */ }

/* Avoid awkward breaks */
h2 + p, h3 + p, h2 + ul, h3 + ul, h2 + table, h3 + table { page-break-before: avoid; }
"""

COVER_HTML = """
<div class="cover">
  <div class="mark">F4</div>
  <h1>Brand <em>Playbook</em></h1>
  <div class="sub">The complete brand bible for Fit4Academy &mdash; the modern platform to run your martial arts academy.</div>
  <div class="badges">
    <div class="badge">UNITED STATES</div>
    <div class="badge">EN &middot; PT &middot; ES</div>
    <div class="badge">VERSION 1.0</div>
  </div>
  <div class="meta">
    <div>
      <strong>Fit4Academy</strong><br>
      <span style="font-size:9pt;">Run your academy. Not your spreadsheets.</span>
    </div>
    <div style="text-align:right;">
      Version 1.0<br>
      <span style="font-size:9pt;">2026-04-26</span>
    </div>
  </div>
</div>
"""


def build_html():
    with open(MD_PATH, 'r', encoding='utf-8') as f:
        md = f.read()

    body_html = markdown.markdown(
        md,
        extensions=['extra', 'sane_lists', 'tables', 'toc', 'fenced_code', 'admonition'],
    )

    # Inject explicit page-break div before each <h2> (Chrome headless ignores
    # CSS page-break-before reliably; explicit div with break-after works).
    import re
    # Skip the first <h2> (Table of contents stays on the same page as the title)
    h2_count = [0]
    def page_break(match):
        h2_count[0] += 1
        if h2_count[0] == 1:
            return match.group(0)
        return '<div class="page-break"></div>' + match.group(0)
    body_html = re.sub(r'<h2\b', lambda m: m.group(0), body_html)
    body_html = re.sub(r'<h2\b[^>]*>', lambda m: page_break(m), body_html)

    full = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Fit4Academy &mdash; Brand Playbook</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=Space+Grotesk:wght@500;600;700;800&display=swap" rel="stylesheet">
  <style>{CSS}</style>
</head>
<body>
  {COVER_HTML}
  <div class="content">
    {body_html}
  </div>
</body>
</html>
"""
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(full)
    print(f"Wrote HTML: {HTML_PATH}")


def build_pdf():
    chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    if not os.path.exists(chrome):
        print("Chrome not found at expected path.", file=sys.stderr)
        sys.exit(1)
    cmd = [
        chrome,
        '--headless=new',
        '--disable-gpu',
        '--no-sandbox',
        '--no-pdf-header-footer',
        '--run-all-compositor-stages-before-draw',
        '--virtual-time-budget=10000',
        f'--print-to-pdf={PDF_PATH}',
        f'file://{HTML_PATH}',
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if not os.path.exists(PDF_PATH):
        print("PDF generation failed.", file=sys.stderr)
        print("STDOUT:", result.stdout, file=sys.stderr)
        print("STDERR:", result.stderr, file=sys.stderr)
        sys.exit(1)
    size = os.path.getsize(PDF_PATH) / 1024
    print(f"Wrote PDF: {PDF_PATH} ({size:.1f} KB)")


if __name__ == '__main__':
    build_html()
    build_pdf()
