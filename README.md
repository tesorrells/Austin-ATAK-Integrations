# Austin ATAK Integrations

Real-time fire and traffic incident feeds for TAK/ATAK systems, providing Cursor-on-Target (CoT) XML events from Austin/Travis County open data sources.

## Features

- **Real-time Fire Incidents**: Polls Austin Fire Department incident data every 45 seconds
- **Real-time Traffic Incidents**: Polls Austin Police Department traffic incident data every 45 seconds
- **CoT XML Generation**: Converts incident data to Cursor-on-Target XML format
- **TAK Server Integration**: Sends CoT events to TAK Server over TLS
- **Incident Lifecycle Management**: Automatically removes incidents when they're no longer active
- **Deduplication**: Prevents duplicate incident reporting
- **Health Monitoring**: REST API endpoints for health checks and metrics
- **Docker Support**: Containerized deployment with Docker Compose

## Data Sources

- **Fire Incidents**: [Austin Real-Time Fire Incidents](https://data.austintexas.gov/Public-Safety/Real-Time-Fire-Incidents/wpu4-x69d) (Dataset: `wpu4-x69d`)
- **Traffic Incidents**: [Austin Real-Time Traffic Incident Reports](https://data.austintexas.gov/Transportation-and-Mobility/Real-Time-Traffic-Incident-Reports/dx9v-zd7x) (Dataset: `dx9v-zd7x`)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- TAK Server with TLS endpoint
- Client certificate for TAK Server authentication
- Socrata App Token (optional but recommended)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd Austin-ATAK-Integrations
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your settings:

```bash
# Required: TAK Server configuration
COT_URL=tls://your-tak-server.com:8089
PYTAK_TLS_CLIENT_CERT=/certs/client.p12
PYTAK_TLS_CLIENT_CERT_PASSWORD=your_password
PYTAK_TLS_CA=/certs/ca.pem

# Optional: Socrata App Token for higher rate limits
SODA_APP_TOKEN=your_app_token_here
```

### 3. Prepare Certificates

Place your TAK Server client certificates in `/opt/austin-cot/certs/`:

```bash
sudo mkdir -p /opt/austin-cot/certs
sudo cp your-client.p12 /opt/austin-cot/certs/client.p12
sudo cp your-ca.pem /opt/austin-cot/certs/ca.pem
sudo chmod 644 /opt/austin-cot/certs/*
```

### 4. Deploy

```bash
docker-compose up -d
```

### 5. Verify

Check service health:

```bash
curl http://localhost:8080/healthz
curl http://localhost:8080/ready
curl http://localhost:8080/metrics
```

## Configuration

### Environment Variables

| Variable                         | Description             | Default             |
| -------------------------------- | ----------------------- | ------------------- |
| `COT_URL`                        | TAK Server CoT URL      | Required            |
| `PYTAK_TLS_CLIENT_CERT`          | Client certificate path | `/certs/client.p12` |
| `PYTAK_TLS_CLIENT_CERT_PASSWORD` | Certificate password    | Required            |
| `PYTAK_TLS_CA`                   | CA certificate path     | `/certs/ca.pem`     |
| `SODA_APP_TOKEN`                 | Socrata App Token       | Optional            |
| `POLL_SECONDS`                   | Polling interval        | `45`                |
| `COT_STALE_MINUTES`              | CoT stale time          | `10`                |
| `API_PORT`                       | API port                | `8080`              |

### Socrata App Token

To avoid rate limiting, register for a free Socrata App Token:

1. Visit [Socrata Developer Portal](https://dev.socrata.com/register)
2. Create an account and generate an App Token
3. Add the token to your `.env` file

## API Endpoints

- `GET /` - Service information
- `GET /healthz` - Health check
- `GET /ready` - Readiness check
- `GET /metrics` - Prometheus-style metrics
- `GET /stats` - Detailed statistics
- `POST /cleanup?days_old=7` - Clean up old incidents

## CoT Event Format

Each incident generates a CoT XML event with:

- **Type**: `b-e-i` (incident/event)
- **UID**: `austin.fire.{incident_id}` or `austin.traffic.{event_id}`
- **Location**: Latitude/longitude from incident data
- **Contact**: `AFD: {issue}` or `APD: {issue}`
- **Remarks**: Incident details, address, status, publication date
- **Link**: Direct link to source data

### Incident Lifecycle

The system automatically manages incident lifecycle:

- **New Incidents**: Sent with normal stale time (10 minutes)
- **Status Changes**: Detected when incidents change from `ACTIVE` to `ARCHIVED`
- **Closure Events**: Sent with immediate stale time (1 minute) to remove from ATAK
- **Closure Reasons**: `INCIDENT ARCHIVED`, `INCIDENT CLOSED`, `INCIDENT RESOLVED`

Example CoT:

```xml
<event version="2.0" uid="austin.fire.12345" type="b-e-i"
       time="2025-01-10T16:18:30Z" start="2025-01-10T16:18:30Z"
       stale="2025-01-10T16:28:30Z" how="m-g">
  <point lat="30.2714" lon="-97.7420" hae="9999999.0" ce="9999999.0" le="9999999.0"/>
  <detail>
    <contact callsign="AFD: STRUCTURE FIRE"/>
    <link url="https://data.austintexas.gov/resource/wpu4-x69d.json?incident_number=12345"/>
    <remarks>STRUCTURE FIRE @ 1234 E 6TH ST | Units: E11, L1 | Status: Working</remarks>
  </detail>
</event>
```

## Monitoring

### Health Checks

The service provides health and readiness endpoints for monitoring:

```bash
# Basic health check
curl http://localhost:8080/healthz

# Detailed readiness check
curl http://localhost:8080/ready

# Metrics for Prometheus
curl http://localhost:8080/metrics
```

### Logs

View application logs:

```bash
docker-compose logs -f austin-cot
```

### Database

The SQLite database stores incident deduplication data and feed statistics:

```bash
# Access database
docker-compose exec austin-cot sqlite3 /app/app/store/seen.db

# View tables
.tables
.schema seen_incidents
.schema feed_state
```

## Systemd Service (Optional)

For production deployment, create a systemd service:

```bash
sudo tee /etc/systemd/system/austin-cot.service > /dev/null <<EOF
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
EOF

sudo systemctl enable austin-cot
sudo systemctl start austin-cot
```

## Troubleshooting

### Common Issues

1. **Certificate Errors**: Ensure client certificates are properly mounted and readable
2. **Connection Refused**: Verify TAK Server URL and network connectivity
3. **Rate Limiting**: Add Socrata App Token to increase rate limits
4. **No Incidents**: Check if incidents have valid coordinates

### Debug Mode

Enable debug logging:

```bash
# Add to .env
LOG_LEVEL=DEBUG

# Restart service
docker-compose restart
```

### Testing CoT Output

Temporarily use UDP for testing:

```bash
# Change COT_URL in .env
COT_URL=udp://255.255.255.255:6969

# Monitor with Wireshark or tcpdump
sudo tcpdump -i any port 6969
```

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python run_tests.py

# Run locally
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Testing

The project includes comprehensive tests for all core functionality:

```bash
# Run core tests (API endpoints and CoT generation)
python run_tests.py

# Run individual test modules
python tests/test_api_endpoints.py
python tests/test_cot_generation.py
```

Test results are documented in `tests/test_summary.md`.

### Project Structure

```
austin-feeds/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── feeds/
│   │   ├── fire.py          # Fire incidents poller
│   │   └── traffic.py       # Traffic incidents poller
│   ├── cot/
│   │   ├── build.py         # CoT XML builder
│   │   └── sender.py        # PyTAK sender
│   └── store/
│       └── seen.py          # SQLite deduplication store
├── docker/
│   └── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review application logs
3. Open an issue on GitHub
4. Contact the development team
