#!/usr/bin/env python3
"""Build the multi-vendor VRP correspondence hub page."""
import pathlib, html as H, datetime

NAV = '''<nav class="site-nav"><div class="container">
  <a href="index.html">Home</a> <a href="whitepaper.html">Whitepaper</a>
  <a href="endpoints.html">Endpoints</a> <a href="galaxy.html">Galaxy</a>
  <a href="threat-map.html">Threat Map</a> <a href="master-report.html">Master Report</a>
  <a href="dossiers.html">Dossiers</a> <a href="vrp-correspondence.html">Correspondence</a>
  <a href="legal-annex.html">Legal</a>
</div></nav>'''

CSS = '<link rel="stylesheet" href="assets/css/style.css">'

vendors = [
    {
        "id": "google", "name": "Google / Android VRP", "color": "#ffb020", "icon": "G",
        "case": "Android Check-In — related prior 533164589",
        "status": "Open position: Google states unauthenticated bootstrap is intentional and "
                  "server-side segregation controls exist. Corrected report requests a canary "
                  "trace + durable untrusted-provenance confirmation. (2026-07)",
        "threads": [
            ("Corrected VRP report — provenance questions", "vrp-correspondence.html#google"),
            ("Reply / impact rebuttal (my_reply)", "dossier-google.html"),
            ("Android VRP report (full filing)", "dossier-google.html"),
        ],
        "notes": "Aggressive Waymo/BigQuery/ML claims from earlier drafts were withdrawn from "
                 "the formal report as not externally verifiable — see corrected report.",
    },
    {
        "id": "microsoft", "name": "Microsoft MSRC", "color": "#00e5ff", "icon": "MS",
        "case": "VULN-193698 / Case 121314 · VULN-200045 / Case 125992 · VULN-202543",
        "status": "All three closed. 121314: Low severity, closed 2026-08-25 — source-map "
                  "exposure fixed (findings 1–3); telemetry element assessed Low/by-design. "
                  "125992: Low, closed as duplicate 2026-08-17. 202543: Complete-NA (non-MSRC) "
                  "2026-07-17. Re-verified 2026-09-04: App Insights still accepts.",
        "threads": [
            ("Case 121314 / VULN-193698 (full transcript)", "source/raw/msrc-case-121314-vuln-193698.txt"),
            ("Case 125992 / VULN-200045 (full transcript)", "source/raw/msrc-case-125992-vuln-200045.txt"),
            ("VULN-202543 reassessment record", "source/raw/msrc-case-vuln-202543-onecollector-reassessment.md"),
            ("MSRC dossier (both-0day brief)", "dossier-microsoft.html"),
        ],
        "notes": "Closure letters reproduced in transcripts. Re-verification evidence in "
                 "docs/reverification-2026-09-04.md.",
    },
    {
        "id": "meta", "name": "Meta Bug Bounty", "color": "#7c5cff", "icon": "",
        "case": "Reports 122102502879389843 · 122104644987389843",
        "status": "2026-07-15: first report closed — does not qualify (working-as-intended / "
                  "out of scope / no demonstrated impact per Meta). Second report filed on "
                  "Pixel provenance; Meta security confirmed receipt 2026-07-13.",
        "threads": [
            ("Meta BB disposition letter (2026-07-15)", "source/raw/meta-bugbounty-response-20260715.txt"),
            ("Second report communications", "source/vendor/meta--meta_2ndreport_communications.md"),
            ("Meta dossier", "dossier-meta.html"),
        ],
        "notes": "Meta declines to detail decision rationale; re-review invited.",
    },
    {
        "id": "flock", "name": "Flock Safety PSIRT", "color": "#f472b6", "icon": "",
        "case": "Reference teal-lynx",
        "status": "PSIRT follow-up (Segment + Datadog RUM) sent with 10 provenance questions; "
                  "awaiting reproduction + security-impact analysis. Planned CERT/CC "
                  "coordination date 2026-09-05.",
        "threads": [
            ("PSIRT follow-up (teal-lynx)", "source/raw/flock-psirt-followup-teal-lynx-2026.md"),
            ("Segment report", "source/vendor/flock--flock_segment_report.md"),
            ("Flock dossier", "dossier-flock.html"),
        ],
        "notes": "Live write keys redacted in public copies.",
    },
    {
        "id": "linkedin", "name": "LinkedIn Security", "color": "#00d0ff", "icon": "",
        "case": "— (email to security@linkedin.com)",
        "status": "Submitted 2026-07-12 via security@linkedin.com; no further public "
                  "disposition in the record.",
        "threads": [
            ("Disclosure email (2026-07-12)", "source/raw/linkedin-disclosure-2026-07-12.md"),
            ("LinkedIn report", "source/vendor/linkedin--report.md"),
            ("LinkedIn dossier", "dossier-linkedin.html"),
        ],
        "notes": "As-reported severity table reproduced in dossier; downstream claims flagged "
                 "as requiring LinkedIn-side confirmation per whitepaper boundaries.",
    },
    {
        "id": "apple", "name": "Apple Security Bounty", "color": "#94a3b8", "icon": "",
        "case": "OE110716814418",
        "status": "Under review per correspondence (2026-07).",
        "threads": [
            ("Apple submission", "source/vendor/apple--submission.md"),
            ("Report details", "source/vendor/apple--report_details.md"),
            ("Apple dossier", "dossier-apple.html"),
        ],
        "notes": "metrics.icloud.com/metrics + diagnostics.apple.com/telemetry.",
    },
    {
        "id": "tencent", "name": "Tencent TSRC", "color": "#a78bfa", "icon": "",
        "case": "— (TSRC)",
        "status": "Report prepared; submission per TSRC process.",
        "threads": [("Tencent report", "source/vendor/tencent--tencent.md"),
                    ("Tencent dossier", "dossier-tencent.html")],
        "notes": "h.trace.qq.com/kv.",
    },
    {
        "id": "amazon", "name": "Amazon VRP", "color": "#ff9900", "icon": "",
        "case": "— (VRP)",
        "status": "Report filed; protobuf-format injection requires further testing per "
                  "NOT-VULN notes (inconclusive).",
        "threads": [("Amazon VRP report", "source/vendor/amazon--amazon_vrp.md"),
                    ("Amazon dossier", "dossier-amazon.html"),
                    ("Negative results", "dossiers.html#negative")],
        "notes": "Inconclusive — no confirmed injection claimed.",
    },
    {
        "id": "baidu", "name": "Baidu / CNZZ / Umeng", "color": "#ff3d81", "icon": "",
        "case": "— (BSRC / Alibaba)",
        "status": "Reports prepared for BSRC (Baidu) + Alibaba security (CNZZ/Umeng).",
        "threads": [],
        "notes": "Documented in master report + endpoints registry.",
    },
    {
        "id": "matomo", "name": "Matomo", "color": "#ffd166", "icon": "",
        "case": "—",
        "status": "Open-source tracker class; report prepared.",
        "threads": [],
        "notes": "demo.matomo.org + self-hosted class (1M+ instances).",
    },
]

def esc(s): return H.escape(s or '')

sections = []
for v in vendors:
    threads = ''.join(f'<li><a href="{t[1]}">{esc(t[0])}</a></li>' for t in v["threads"]) or '<li class="note">—</li>'
    sections.append(f'''
    <section class="card" id="v-{v["id"]}">
      <h2><span class="dot" style="background:{v["color"]};display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:.5rem"></span>{esc(v["name"])}</h2>
      <p class="note" style="margin-bottom:.4rem"><strong>Case:</strong> {esc(v["case"])}</p>
      <p style="margin-bottom:.6rem">{esc(v["status"])}</p>
      <p class="note" style="margin-bottom:.6rem">{esc(v["notes"])}</p>
      <h3 style="font-size:.85rem;margin:.6rem 0 .3rem;color:var(--accent)">Records</h3>
      <ul style="margin-left:1.1rem">{threads}</ul>
    </section>''')

html_doc = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="index, follow">
<title>Vendor Correspondence — Telemetry Triage</title>
<meta name="description" content="Coordinated-disclosure correspondence with every vendor — MSRC, Google VRP, Meta, Flock PSIRT, LinkedIn, Apple, TSRC and more.">
{CSS}</head><body>
{NAV}
<header class="site-header"><div class="container">
  <div class="kicker">Church of Malware · Coordinated Disclosure</div>
  <h1>Vendor Correspondence</h1>
  <p class="subtitle">Every disclosure thread, vendor position, and case disposition — reproduced
  faithfully. Ingestion acceptance is confirmed externally; downstream claims follow the
  <a href="whitepaper.html">whitepaper's</a> claim boundaries. Live credentials redacted.</p>
  <div class="badge-row"><span class="badge badge-warn">Embargo lifted 2026-09-04</span>
  <span class="badge badge-accent">TLP:CLEAR</span>
  <span class="badge">Publication record · 2026</span></div>
</div></header>
<main class="container">
  <div class="card"><h2>At a glance</h2>
  <table><thead><tr><th>Vendor</th><th>Case / ref</th><th>Disposition</th></tr></thead><tbody>
  {''.join(f'<tr><td><a href="#v-{v["id"]}">{esc(v["name"])}</a></td><td>{esc(v["case"])}</td><td>{esc(v["status"].split(".")[0])}.</td></tr>' for v in vendors)}
  </tbody></table></div>
  {''.join(sections)}
  <div class="card"><h2>Re-verification &amp; negative results</h2>
  <ul><li><a href="docs/reverification-2026-09-04.md">Post-disclosure re-verification (2026-09-04)</a></li>
  <li><a href="dossiers.html">Negative results — tested, not vulnerable (Tesla / Oracle / ICS / Amazon)</a></li></ul></div>
</main>
<footer class="site-footer"><div class="container">
<p>© 2026 Church of Malware · <a href="https://churchofmalware.org">churchofmalware.org</a></p>
<p class="note">Public-interest disclosure. No exploit code; no instructions enabling harm. TLP:CLEAR.</p>
</div></footer>
</body></html>'''

pathlib.Path('vrp-correspondence.html').write_text(html_doc)
print('vrp-correspondence.html written:', len(html_doc), 'bytes,', len(vendors), 'vendors')
