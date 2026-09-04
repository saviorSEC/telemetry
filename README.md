# Unauthenticated Telemetry Injection — Triage

Public disclosure site for Church of Malware research: **unauthenticated telemetry
injection** — public-facing telemetry ingestion endpoints that accept unauthenticated
writes.

- **Research lead:** ek0ms savi0r (Church of Malware)
- **Researchers:** k3nundrum, tjnull
- **Embargo lifted:** 2026-09-04
- **Live:** https://saviorSEC.github.io/telemetry (custom domain: `saviorSEC.io/telemetry`)

## Site structure

```
telemetry/
├── index.html            ← disclosure landing (sections staged, awaiting data)
├── assets/css/style.css  ← site theme
├── assets/js/            ← (optional) table rendering / data loader
├── data/                 ← triage data (CSV/JSON) lands here
└── docs/                 ← long-form writeups, per-vendor advisories
```

## Status

Sections in `index.html` are staged with placeholders and are being populated as the
triage data lands. No exploit code on this site — disclosure only.

## Repo conventions

- Public repo — treat every commit as publishable.
- No credentials, no internal case artifacts, no exploit code.
- Vendor names + timelines must match the coordinated-disclosure record.
