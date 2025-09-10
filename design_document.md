Awesome project. Here’s a tight, actionable design doc you can drop into your repo.

# Austin → CoT Feeds for TAK/ATAK

**Targets:** Real-time Fire Incidents + Real-time Traffic Incidents
**Outputs:** Cursor-on-Target (CoT) XML events sent into your TAK Server over TLS
**Runtime:** Python (FastAPI + PyTAK) in Docker on your existing DigitalOcean host

---

## 1) Data Sources & Acquisition

### A. Fire incidents (Austin/Travis County)

* **Dataset:** “Real-Time Fire Incidents”
  Socrata dataset ID: **`wpu4-x69d`** → SODA API endpoint:
  `https://data.austintexas.gov/resource/wpu4-x69d.json`
  Updated about every 5 minutes (per catalog page). ([City of Austin Open Data Portal][1], [Data.gov][2])
* **Notes:** The Open Data “story” page links to the live feed; use the SODA API directly for polling. ([City of Austin Open Data Portal][3], [Austin Texas Services][4])

### B. Traffic incidents (Austin/Travis County)

* **Dataset:** “Real-Time Traffic Incident Reports”
  Socrata dataset ID: **`dx9v-zd7x`** → SODA API endpoint:
  `https://data.austintexas.gov/resource/dx9v-zd7x.json`
  Also updated every \~5 minutes; the legacy QACT page confirms the cadence. ([City of Austin Open Data Portal][5], [Austin Texas Services][6])

### C. Optional: State/TXDOT incidents (future)

* **TXDOT ITS incidents (Austin District):** scrape or integrate if needed:
  `https://its.txdot.gov/its/District/AUS/incidents` (HTML). ([TxDOT][7])

### SODA API access & throttling

* Use an **App Token** (Socrata) to avoid tight rate limits. Add `X-App-Token` header.
* Typical poll: **every 30–60s**, but set **de-dupe** to avoid re-sending existing incidents.

**Example pulls** (with server-side filtering):

```http
# Fire incidents updated in last 10 minutes
GET /resource/wpu4-x69d.json?$select=*&$where=last_update >= dateadd('minute', -10, now())

# Traffic incidents updated in last 10 minutes
GET /resource/dx9v-zd7x.json?$select=*&$where=last_update >= dateadd('minute', -10, now())
```

---

## 2) CoT Modeling (mapping JSON → CoT XML)

We’ll represent each **incident** as a **“point event”** in CoT:

* **Element:** `<event>` (version 2.0)
* **Attributes you must set:**

  * `uid`: stable deterministic key (e.g., `austin.fire.<incident_id>`).
  * `type`: CoT type. For “general incident/event,” use **`b-e-i`** (event/incident).
    (This is common for incidents; you can refine types later if you adopt a catalog.) ([tutorials.techrad.co.za][8])
  * `time`, `start`: current timestamp (ISO8601/UTC).
  * `stale`: now + **5–15 minutes** (fire/traffic cadence suggests 10 min is safe).
  * `how`: “m-g” (machine-generated), or “h-g-i-g-o” depending on local convention.
* **Child `point`**: `lat`, `lon`, `hae="9999999.0"`, `ce="9999999.0"`, `le="9999999.0"`.
* **Child `detail`**: include helpful context:

  * `<contact callsign="AFD: STRUCTURE FIRE" />` (or APD: TRAFFIC, etc.)
  * `<link url="source permalink" />`
  * `<remarks>` short text (address, status, units).
  * Optional `<status readiness="active" />`, incident code, priority, etc.

**Minimal CoT example (incident “b-e-i”):**

```xml
<event version="2.0" uid="austin.fire.12345" type="b-e-i"
       time="2025-09-10T16:18:30Z" start="2025-09-10T16:18:30Z" stale="2025-09-10T16:28:30Z" how="m-g">
  <point lat="30.2714" lon="-97.7420" hae="9999999.0" ce="9999999.0" le="9999999.0"/>
  <detail>
    <contact callsign="AFD: STRUCTURE FIRE"/>
    <link url="https://data.austintexas.gov/resource/wpu4-x69d.json?incident_id=12345"/>
    <remarks>STRUCTURE FIRE @ 1234 E 6TH ST | Units: E11, L1 | Status: Working</remarks>
  </detail>
</event>
```

> Background and field semantics are described in CoT docs and guides; we’ll stick to the minimal, broadly compatible event schema above. ([MITRE][9], [NDIAS Storage][10])

### Field mapping (initial proposal)

| CoT Field                 | Fire dataset                    | Traffic dataset             | Notes                                          |
| ------------------------- | ------------------------------- | --------------------------- | ---------------------------------------------- |
| `uid`                     | `austin.fire.{incident_number}` | `austin.traffic.{event_id}` | Hash if no stable id; keep stable across polls |
| `type`                    | `b-e-i`                         | `b-e-i`                     | Start simple; refine per code/category later   |
| `time/start`              | now (UTC)                       | now (UTC)                   | When you created the CoT                       |
| `stale`                   | now + 10 min                    | now + 10 min                | Align with feed cadence                        |
| `point.lat/lon`           | lat/lon field names in dataset  | lat/lon fields in dataset   | Verify exact field names at ingest             |
| `detail/contact@callsign` | `AFD: {category}`               | `APD: {category}`           | Or “ATC: {category}” depending on source       |
| `detail/remarks`          | brief composed string           | brief composed string       | Include address/intersection, status           |
| `detail/link@url`         | built dataset link              | built dataset link          | Useful for drill-down/debug                    |

---

## 3) Deduplication, Updates & Lifecycle

* **Dedup key:** prefer the feed’s incident ID; otherwise compose a hash of `{type|address|started_at}`.
* **Update behavior:** if an incident’s status/coordinates change, **re-emit** a CoT with the **same UID** (clients will update marker).
* **End-of-life:** when an incident disappears from the feed or status closes, send a **final CoT** with a **short stale** (e.g., +1 min). Some teams also send a status flag in `<detail>` like `<status readiness="inactive"/>`.

---

## 4) Sender: PyTAK gateway

Use **PyTAK** to serialize CoT and send to TAK Server over **TLS** (`tls://host:8089`) using a client cert. PyTAK is designed for this exact use-case, supports TLS, and has clear config patterns. ([PyPI][11], [Python Team Awareness Kit][12], [PyTAK][13])

**Network target (examples)**

* `COT_URL=tls://atak.yourdomain.com:8089`  (TAK Server TLS input)
* Supply client **PKCS12** or PEM keypair, and trusted CA as per your server config.

---

## 5) Service Architecture

```
austin-feeds/
├─ app/
│  ├─ main.py              # FastAPI health/readiness, metrics
│  ├─ feeds/
│  │  ├─ fire.py           # Poll SODA, map → CoT events
│  │  └─ traffic.py        # Poll SODA, map → CoT events
│  ├─ cot/
│  │  ├─ build.py          # JSON→CoT XML serializer
│  │  └─ sender.py         # PyTAK queue + TLS client
│  ├─ store/
│  │  └─ seen.db           # tiny SQLite or Redis for de-dupe and state
│  └─ config.py
├─ docker/
│  └─ Dockerfile
├─ docker-compose.yml
└─ README.md
```

**Key loops (async):**

* `Poller`: every 30–60s → fetch since last watermark → normalize → dedupe → hand to `Sender`.
* `Sender` (PyTAK): takes CoT XML → pushes to `COT_URL` (TLS) using provided certs.
* Health & metrics: `/healthz`, `/metrics` (Prometheus), last poll times, sent counts.

---

## 6) Security & Certificates

* Generate a **client certificate** signed by your TAK Server CA (or use an approved client p12).
* Mount into the container read-only:

  * `/certs/client.p12` (or `/certs/client.pem` + key)
  * `/certs/ca.pem` (server CA)
* PyTAK TLS params: URL + cert paths + passwords; see docs. ([PyTAK][13])

---

## 7) Deployment on your DigitalOcean host

### Docker Compose (single service per feed, or one multi-feed)

* One container that runs both pollers is simplest.

```yaml
version: "3.8"
services:
  austin-cot:
    image: ghcr.io/yourorg/austin-cot:latest
    restart: unless-stopped
    env_file: .env
    environment:
      COT_URL: ${COT_URL}
      SODA_APP_TOKEN: ${SODA_APP_TOKEN}
      FIRE_DATASET: wpu4-x69d
      TRAFFIC_DATASET: dx9v-zd7x
      POLL_SECONDS: "45"
      COT_STALE_MINUTES: "10"
    volumes:
      - /opt/austin-cot/certs:/certs:ro
    ports:
      - "127.0.0.1:8080:8080"  # health/metrics only
```

**.env (example)**

```
COT_URL=tls://atak.yourdomain.com:8089
SODA_APP_TOKEN=xxxxxx
PYTAK_TLS_CLIENT_CERT=/certs/client.p12
PYTAK_TLS_CLIENT_CERT_PASSWORD=changeit
PYTAK_TLS_CA=/certs/ca.pem
```

### System setup

* Put compose file under `/opt/austin-cot/` and create a **systemd** unit:

```
[Unit]
Description=Austin CoT Feeds
After=docker.service
Requires=docker.service

[Service]
WorkingDirectory=/opt/austin-cot
ExecStart=/usr/bin/docker compose up --pull always --no-color
ExecStop=/usr/bin/docker compose down
TimeoutStopSec=30
Restart=always

[Install]
WantedBy=multi-user.target
```

### Networking

* Container **does not need inbound** internet from the world; only outbound to Socrata and **to TAK Server** if on a private network/VPN (Tailscale/DO VPC).
* Keep the health port bound to `127.0.0.1` and scrape with local Prometheus or use SSH tunnel.

---

## 8) Implementation Notes (Python)

**Dependencies**

* `pytak` for network & CoT send. ([PyPI][11])
* `httpx` (async client), `fastapi`, `uvicorn`.
* `orjson` for fast JSON, `pydantic` for schemas.
* `aiosqlite` or `redis` for dedupe state.

**CoT builder (sketch)**

```python
def build_incident_cot(uid, lat, lon, callsign, remarks, link,
                       cot_type="b-e-i", stale_minutes=10, how="m-g") -> str:
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    stale = now + timedelta(minutes=stale_minutes)
    return f"""<event version="2.0" uid="{uid}" type="{cot_type}"
      time="{now.isoformat()}" start="{now.isoformat()}" stale="{stale.isoformat()}" how="{how}">
      <point lat="{lat}" lon="{lon}" hae="9999999.0" ce="9999999.0" le="9999999.0"/>
      <detail>
        <contact callsign="{xml_escape(callsign)}"/>
        <link url="{xml_escape(link)}"/>
        <remarks>{xml_escape(remarks)}</remarks>
      </detail>
    </event>"""
```

**Polling pattern**

* Track a `last_seen_ids` set per feed (persist it).
* Query with `$where=last_update >= dateadd('minute', -10, now())` and **also** `$order=last_update DESC` to keep a waterline.
* Normalize lat/lon: drop records missing coordinates.

---

## 9) Verification & Observability

* **Local test:** temporarily set `COT_URL=udp://255.255.255.255:6969` and sniff CoT with Wireshark, then switch to TLS. (PyTAK supports UDP/TCP/TLS.) ([PyPI][11])
* **Server test:** watch TAK Server “Connections/Traffic” and confirm CoT ingestion; confirm markers appear in ATAK.
* **Metrics to export:** last poll OK timestamp, fetched rows, emitted CoTs, suppressed duplicates, send failures.

---

## 10) Data Quality & Enrichment (Phase 2)

* **Type refinement:** map categories to more specific CoT types (e.g., special incident subtypes). If you adopt a type catalog/library later, apply it here. ([GitHub][14])
* **Symbology:** you can override markers via ATAK style files or CoT `type` choices.
* **Geo-fencing:** filter to City of Austin FPJ or your operational AOI.
* **Linkbacks:** include the dataset permalink in `<link>` so users can tap through.
* **TXDOT ITS merge:** de-dupe against city incidents by proximity + time window.

---

## 11) Governance & Legal

* Respect the City’s Open Data portal **terms of use** and rate limits.
* Avoid PHI/PII: the fire feed explicitly **excludes medical calls** for HIPAA. ([Data.gov][2])

---

## 12) Cutover Plan

1. Stand up the container in **staging** with `udp://` to a test TAK/ATAK client.
2. Validate CoT shape & symbol behavior.
3. Flip to **TLS** with client cert to your production TAK Server.
4. Tune stale durations & poll intervals to avoid “flashing” markers.
5. Add TXDOT incidents (optional), then expand to other city feeds.

---

### References

* Austin Real-Time Fire Incidents (SODA/API): dataset `wpu4-x69d`. ([City of Austin Open Data Portal][1])
* Austin Real-Time Traffic Incident Reports: dataset `dx9v-zd7x`. ([City of Austin Open Data Portal][5])
* Legacy traffic/fire pages (cadence context). ([Austin Texas Services][6])
* PyTAK package & docs (TLS, examples). ([PyPI][11], [PyTAK][15])
* CoT background & field semantics. ([MITRE][9], [NDIAS Storage][10])

---

[1]: https://data.austintexas.gov/Public-Safety/Real-Time-Fire-Incidents/wpu4-x69d?utm_source=chatgpt.com "Real-Time Fire Incidents | Open Data | City of Austin Texas"
[2]: https://catalog.data.gov/dataset/real-time-fire-incidents?utm_source=chatgpt.com "Real-Time Fire Incidents - Dataset - Catalog"
[3]: https://data.austintexas.gov/stories/s/dr26-vqib?utm_source=chatgpt.com "Real-Time Fire Incidents | Open Data | City of Austin Texas"
[4]: https://services.austintexas.gov/fact/default.cfm?utm_source=chatgpt.com "Active Fire Incident Page | AustinTexas. ..."
[5]: https://data.austintexas.gov/Transportation-and-Mobility/Real-Time-Traffic-Incident-Reports/dx9v-zd7x?utm_source=chatgpt.com "Real-Time Traffic Incident Reports | Open Data | City of Austin ..."
[6]: https://services.austintexas.gov/qact/default.cfm?utm_source=chatgpt.com "Austin-Travis County Traffic Report Page"
[7]: https://its.txdot.gov/its/District/AUS/incidents?utm_source=chatgpt.com "Incidents"
[8]: https://tutorials.techrad.co.za/wp-content/uploads/2021/06/The-Developers-Guide-to-Cursor-on-Target-1.pdf?utm_source=chatgpt.com "[PDF] The Developer's Guide to Cursor on Target - Radical Tech Tutorials"
[9]: https://www.mitre.org/sites/default/files/pdf/09_4937.pdf?utm_source=chatgpt.com "[PDF] Cursor-on-Target Message Router User's Guide - MITRE Corporation"
[10]: https://ndiastorage.blob.core.usgovcloudapi.net/ndia/2008/USCG/Wednesday/2NiessenCursorOnTarget.pdf?utm_source=chatgpt.com "[PDF] Cursor on Target"
[11]: https://pypi.org/project/pytak/5.0.3/?utm_source=chatgpt.com "pytak 5.0.3"
[12]: https://pytak.rtfd.io/?utm_source=chatgpt.com "Python Team Awareness Kit (PyTAK)"
[13]: https://pytak.readthedocs.io/en/stable/configuration/?utm_source=chatgpt.com "Configuration - Python Team Awareness Kit (PyTAK)"
[14]: https://github.com/topics/cursor-on-target?utm_source=chatgpt.com "cursor-on-target · GitHub Topics"
[15]: https://pytak.readthedocs.io/en/latest/examples/?utm_source=chatgpt.com "Examples - Python Team Awareness Kit (PyTAK)"
