// TELEMETRY TRIAGE GALAXY — data (Church of Malware, ek0ms savi0r)
// House engine format: zones (vendors) + services (endpoints) + links (data flow)
const NET_INT = {
  "zones": [
    {"id":"z-ms","name":"MICROSOFT","color":"#00e5ff","note":"App Insights (eastus-8 /v2.1/track) + OneCollector/1DS (browser.events, vortex, 7 regional) — NO_AUTH injection. MSRC VULN-193698/121314 (closed Low, source maps fixed), VULN-200045/125992 (closed Low/dup), VULN-202543 (Complete-NA). RE-VERIFIED 2026-09-04: App Insights still accepts (200 itemsAccepted:1); OneCollector now 401 InvalidTenantToken."},
    {"id":"z-google","name":"GOOGLE / ANDROID","color":"#ffb020","note":"android.googleapis.com/checkin — bootstrap accepts unauthenticated device-identity fields. VRP: Google asserts by-design + server-side segregation; corrected report requests canary trace. GA4 /g/collect accepts unauth Measurement Protocol events."},
    {"id":"z-apple","name":"APPLE","color":"#94a3b8","note":"metrics.icloud.com/metrics + diagnostics.apple.com/telemetry — unauthenticated JSON/text/binary accepted. Apple Security Bounty OE110716814418 — under review."},
    {"id":"z-meta","name":"META","color":"#7c5cff","note":"facebook.com/tr (pixel) + /log + /metrics + Ray-Ban Meta DAT (5 app IDs). Bug bounty 122102502879389843 — closed not-qualifying (working-as-intended per Meta, 2026-07-15)."},
    {"id":"z-linkedin","name":"LINKEDIN","color":"#00d0ff","note":"px/dc/ads.linkedin.com — 39+ telemetry endpoints. Submitted security@linkedin.com."},
    {"id":"z-baidu","name":"BAIDU","color":"#ff3d81","note":"hm.baidu.com/hm.gif + nsclick.baidu.com tracking family (7). Reported BSRC international."},
    {"id":"z-cnzz","name":"CNZZ / UMENG (ALIBABA)","color":"#4ade80","note":"cnzz.mmstat.com + s9/s4/s19.cnzz.com z_stat.php (4). Reported Alibaba security."},
    {"id":"z-tencent","name":"TENCENT","color":"#a78bfa","note":"h.trace.qq.com/kv — trace telemetry. Reported TSRC."},
    {"id":"z-matomo","name":"MATOMO","color":"#ffd166","note":"matomo.php — self-hosted analytics class (1M+ instances). Reported."},
    {"id":"z-flock","name":"FLOCK SAFETY","color":"#f472b6","note":"api.segment.io/v1/track via exposed client-side write key — Segment-backed pipeline. Reported security@flocksafety.com."}
  ],
  "services": [
    {"id":"s-ai","name":"eastus-8.in.applicationinsights.azure.com","zone":"z-ms","role":"APP INSIGHTS /v2.1/track","note":"Unauth POST 200 itemsAccepted:1. VULN-193698. RE-VERIFIED OPEN 2026-09-04.","endpoints":["/v2.1/track"],"keys":[],"cert":null},
    {"id":"s-oc-browser","name":"browser.events.data.microsoft.com","zone":"z-ms","role":"ONECOLLECTOR /1DS","note":"NO_AUTH client-id. July 204 -> Sept 401 InvalidTenantToken. VULN-200045/202543.","endpoints":["/OneCollector/1.0/"],"keys":[],"cert":null},
    {"id":"s-oc-vortex","name":"vortex.data.microsoft.com","zone":"z-ms","role":"ONECOLLECTOR /1DS","note":"Same as browser.events. 401 as of 2026-09-04.","endpoints":["/OneCollector/1.0/"],"keys":[],"cert":null},
    {"id":"s-gateway","name":"gatewayadminportal*.azure.* (12 portals)","zone":"z-ms","role":"SOURCE-MAP EXPOSURE (FIXED)","note":"16MB bundle.js.map, 1,390 TS files. MSRC confirmed fix (removed at build time) — findings 1-3.","endpoints":["/static/js/bundle.js.map"],"keys":[],"cert":null},
    {"id":"s-checkin","name":"android.googleapis.com","zone":"z-google","role":"CHECK-IN /checkin","note":"Unauth bootstrap accepts android_id/security_token/device_info. stats_ok:true. VRP corrected report = provenance questions + canary trace request.","endpoints":["/checkin"],"keys":[],"cert":null},
    {"id":"s-ga4","name":"www.google-analytics.com","zone":"z-google","role":"GA4 MEASUREMENT","note":"/g/collect unauth measurement protocol. 204.","endpoints":["/g/collect"],"keys":[],"cert":null},
    {"id":"s-icloud","name":"metrics.icloud.com","zone":"z-apple","role":"ICLOUD METRICS","note":"/metrics unauth POST. Under review.","endpoints":["/metrics"],"keys":[],"cert":null},
    {"id":"s-diag","name":"diagnostics.apple.com","zone":"z-apple","role":"DIAGNOSTICS TELEMETRY","note":"/telemetry unauth POST. Under review.","endpoints":["/telemetry"],"keys":[],"cert":null},
    {"id":"s-pixel","name":"www.facebook.com/tr","zone":"z-meta","role":"PIXEL CONVERSION","note":"Unauth GET/POST. Closed not-qualifying by Meta.","endpoints":["/tr"],"keys":[],"cert":null},
    {"id":"s-mlog","name":"www.facebook.com /log /metrics","zone":"z-meta","role":"INTERNAL LOG/METRICS","note":"Unauth POST accepted. Meta: working-as-intended per disposition.","endpoints":["/log","/metrics"],"keys":[],"cert":null},
    {"id":"s-dat","name":"Ray-Ban Meta DAT (5 app IDs)","zone":"z-meta","role":"WEARABLES TELEMETRY","note":"Glasses event types accepted. Same bounty thread.","endpoints":[],"keys":[],"cert":null},
    {"id":"s-li","name":"px/dc/ads.linkedin.com","zone":"z-linkedin","role":"AD + ANALYTICS TELEMETRY","note":"39+ endpoints, 200 OK. x-li-uuid + x-li-fabric prod-lor1 observed.","endpoints":["/collect","/track","/convert","/pixel","/event","/events","/analytics","/beacon","/ping","/log","/metrics"],"keys":[],"cert":null},
    {"id":"s-baidu","name":"hm.baidu.com + nsclick.baidu.com","zone":"z-baidu","role":"ANALYTICS + CLICK TRACKING","note":"hm.gif 43-byte GIF; t/click/u/v/s/d.gif family. Reported BSRC.","endpoints":["/hm.gif","/t.gif","/click.gif","/u.gif","/v.gif","/s.gif","/d.gif"],"keys":[],"cert":null},
    {"id":"s-cnzz","name":"cnzz.mmstat.com + s9/s4/s19.cnzz.com","zone":"z-cnzz","role":"CNZZ ANALYTICS","note":"z_stat.php family, CORS *. Reported Alibaba.","endpoints":["/z_stat.php"],"keys":[],"cert":null},
    {"id":"s-qq","name":"h.trace.qq.com","zone":"z-tencent","role":"TRACE /kv","note":"Unauth POST/GET key-value traces. Reported TSRC.","endpoints":["/kv"],"keys":[],"cert":null},
    {"id":"s-matomo","name":"demo.matomo.org (self-hosted class)","zone":"z-matomo","role":"MATOMO TRACKER","note":"matomo.php unauth. 1M+ self-hosted instances affected class.","endpoints":["/matomo.php"],"keys":[],"cert":null},
    {"id":"s-segment","name":"api.segment.io (Flock write key)","zone":"z-flock","role":"SEGMENT TRACK","note":"Write key exposed in client JS. Unauth /v1/track 200. Reported Flock Safety.","endpoints":["/v1/track"],"keys":[],"cert":null}
  ],
  "ipPools": [],
  "links": [
    ["s-ai","s-oc-browser"],
    ["s-ai","s-oc-vortex"],
    ["s-oc-browser","s-oc-vortex"],
    ["s-gateway","s-ai"],
    ["s-checkin","s-ga4"],
    ["s-pixel","s-mlog"],
    ["s-mlog","s-dat"],
    ["s-baidu","s-cnzz"],
    ["s-segment","s-li"]
  ]
};
