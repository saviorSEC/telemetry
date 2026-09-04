#!/usr/bin/env python3
"""Generate GitHub Pages HTML from the Church of Malware telemetry disclosure markdown."""
import markdown
import html
import re

NAV = """
<nav class="site-nav"><div class="container">
  <a href="index.html">Home</a>
  <a href="whitepaper.html">Whitepaper</a>
  <a href="trust-crisis.html">Trust Crisis</a>
  <a href="endpoints.html">Endpoints</a>
  <a href="galaxy.html">Galaxy</a>
  <a href="threat-map.html">Threat Map</a>
  <a href="master-report.html">Master Report</a>
  <a href="dossiers.html">Dossiers</a>
  <a href="vrp-correspondence.html">Correspondence</a>
  <a href="hyperject.html">Hyperject</a>
  <a href="legal-annex.html">Legal</a>
</div></nav>"""

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="index, follow">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:type" content="article">
<meta property="og:description" content="{desc}">
<link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
{nav}
<main class="container article">
{body}
</main>
<footer class="site-footer"><div class="container">
<p>&copy; 2026 Church of Malware &middot; <a href="https://churchofmalware.org">churchofmalware.org</a> &middot; <a href="index.html">triage home</a></p>
<p class="note">Public-interest disclosure. No exploit code; no instructions enabling harm. TLP:CLEAR.</p>
</div></footer>
</body>
</html>
"""

def gen(src, out, title, desc):
    text = open(src, encoding="utf-8").read()
    # strip markdown H1 (title lives in the template) but keep a styled doc title
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "nl2br"],
    )
    body = re.sub(r"<h1>(.*?)</h1>", r'<div class="doc-title">\1</div>', body, count=1)
    page = TEMPLATE.format(title=title, desc=desc, nav=NAV, body=body)
    open(out, "w", encoding="utf-8").write(page)
    print("wrote", out, len(page), "bytes")

if __name__ == "__main__":
    gen("source/whitepaper-trust-crisis.md", "trust-crisis.html",
        "The Telemetry Trust Crisis — Systemic Architectural Risk Against Data Provenance, AI Training, and Security Operations",
        "Second whitepaper (ek0ms savi0r & k3n): telemetry trust crisis — architectural risk, walkthroughs, vendor impact, mitigations. Public disclosure 2026-09-05.")
    gen("source/whitepaper.md", "whitepaper.html",
        "Whitepaper — Unauthenticated Telemetry Injection and the Collapse of Data Provenance",
        "Church of Malware whitepaper: telemetry provenance, trust boundaries, and unauthenticated ingestion — assessment model and claim boundaries.")
    gen("source/master-report.md", "master-report.html",
        "Master Report — Global Unauthenticated Telemetry Injection Triage",
        "Triage master report: unauthenticated telemetry injection across 80+ endpoints and 10 technology companies — evidence and vendor status.")
    gen("source/legal-annex.md", "legal-annex.html",
        "Legal Annex — Telemetry Integrity: Potential Legal and Regulatory Considerations",
        "Research note on laws, regulations, and standards potentially relevant to unauthenticated, attacker-controlled telemetry.")
