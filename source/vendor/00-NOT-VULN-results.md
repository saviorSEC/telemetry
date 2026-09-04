tested_confirmedNOT_vuln.md

#tested and not vuln to unauth tele injection and or needs futher testing 

- tesla locked down with several layers of 0auth

- Oracle - locked down with several layers of 0auth

- ICS systems locked down for the most part except PI Web API, tested 7 ICS endpoints //inconclusive for now

- amazon for now requires protobuf to send unauthenticated telemetry injection payloads - needs further testing // get live protobuf payload, reverse engineer, send protobuf payload. retest.
