# Deployment Guide - Git-Based Setup

This guide shows how to deploy Austin ATAK Integrations to your DigitalOcean server using git, without requiring root access.

## Prerequisites

- DigitalOcean server with your TAK Server running
- Regular user account (not root)
- Git installed on the server
- Docker and Docker Compose installed

## Step 1: Prepare Your Repository

First, push your code to a git repository (GitHub, GitLab, etc.):

```bash
# On your local machine
git add .
git commit -m "Initial deployment ready"
git push origin main
```

## Step 2: Deploy on Your Server

SSH to your server and run the deployment:

```bash
# SSH to your server
ssh youruser@142.93.48.114

# Run the git-based deployment
curl -fsSL https://raw.githubusercontent.com/yourusername/Austin-ATAK-Integrations/main/deploy-git.sh | bash
```

Or manually:

```bash
# Download and run the deployment script
wget https://raw.githubusercontent.com/yourusername/Austin-ATAK-Integrations/main/deploy-git.sh
chmod +x deploy-git.sh
./deploy-git.sh
```

## Step 3: Set Up Production Environment

```bash
cd ~/austin-atak-integrations
./setup-git-production.sh
```

## Step 4: Configure Network

```bash
./setup-network.sh
```

## Step 5: Start the Service

```bash
docker-compose up -d
```

## Step 6: Enable Auto-Start (Optional)

To start the service automatically on boot:

```bash
# Enable user systemd service
systemctl --user enable austin-atak-integrations
systemctl --user start austin-atak-integrations
```

## Monitoring

### Check Service Status

```bash
docker-compose ps
```

### View Logs

```bash
docker-compose logs -f
```

### Health Check

```bash
curl http://localhost:8080/health
```

### Statistics

```bash
curl http://localhost:8080/stats
```

## Updating the Service

To update to the latest version:

```bash
./update.sh
```

This will:

1. Pull the latest changes from git
2. Rebuild the Docker container
3. Restart the service

## Configuration

The service is configured via the `.env` file:

```bash
# TAK Server Configuration (TCP - no certificates needed)
COT_URL=tcp://tak-server-tak-1:8087

# Socrata API Configuration (optional - improves rate limits)
SODA_APP_TOKEN=

# Polling Configuration
POLL_SECONDS=45
COT_STALE_MINUTES=10

# FastAPI Application Configuration
API_PORT=8080
```

## Troubleshooting

### Docker Permission Issues

If you get permission errors with Docker:

```bash
sudo usermod -aG docker $USER
# Then log out and back in
```

### TAK Server Connection Issues

Check if TAK Server is running:

```bash
docker ps | grep tak-server
```

Check network connectivity:

```bash
docker network ls
docker network inspect tak-network
```

### Service Not Starting

Check logs for errors:

```bash
docker-compose logs austin-atak-integrations
```

### Port Conflicts

If port 8080 is already in use, change it in `.env`:

```bash
API_PORT=8081
```

Then restart:

```bash
docker-compose down
docker-compose up -d
```

## File Structure

```
~/austin-atak-integrations/
├── app/                    # Application code
├── data/                   # SQLite database
├── logs/                   # Application logs
├── .env                    # Environment configuration
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile             # Docker build instructions
├── setup-network.sh       # Network setup script
├── update.sh              # Update script
└── README.md              # Documentation
```

## Security Notes

- The service runs as a regular user (not root)
- Uses Docker's internal networking for TAK Server communication
- No certificates required (uses TCP with anonymous authentication)
- API endpoints are only accessible locally (port 8080)

## Support

If you encounter issues:

1. Check the logs: `docker-compose logs -f`
2. Verify TAK Server is running: `docker ps`
3. Check network connectivity: `docker network inspect tak-network`
4. Verify configuration: `cat .env`
