#!/bin/bash
# Git-based production setup script for Austin ATAK Integrations
# Run this after deploy-git.sh

set -e

# Configuration
DEPLOY_DIR="$HOME/austin-atak-integrations"
SERVICE_NAME="austin-atak-integrations"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    log_error "docker-compose.yml not found. Please run this script from the deployment directory."
    exit 1
fi

log_step "Setting up production environment..."

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    log_info "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Create production environment file
log_step "Creating production environment configuration..."
cat > .env << EOF
# TAK Server Configuration (TCP - no certificates needed)
COT_URL=tcp://tak-server-tak-1:8087

# Socrata API Configuration (optional - improves rate limits)
SODA_APP_TOKEN=

# Polling Configuration
POLL_SECONDS=45
COT_STALE_MINUTES=10

# FastAPI Application Configuration
API_PORT=8080
EOF

# Create Docker Compose file
log_step "Creating Docker Compose configuration..."
cat > docker-compose.yml << EOF
services:
  austin-atak-integrations:
    build: .
    container_name: austin-atak-integrations
    restart: unless-stopped
    environment:
      - COT_URL=tcp://tak-server-tak-1:8087
      - SODA_APP_TOKEN=
      - POLL_SECONDS=45
      - COT_STALE_MINUTES=10
      - API_PORT=8080
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    ports:
      - "8080:8080"
    networks:
      - tak-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  tak-network:
    external: true
EOF

# Create network setup script
log_step "Creating network setup script..."
cat > setup-network.sh << 'EOF'
#!/bin/bash
# Network setup script

echo "🌐 Setting up Docker network for TAK Server connection"
echo "======================================================"

# Check if TAK Server is running
if ! docker ps | grep -q "tak-server-tak-1"; then
    echo "❌ TAK Server container not found. Please ensure TAK Server is running."
    exit 1
fi

echo "✅ TAK Server container found:"
docker ps | grep "tak-server-tak-1"

# Check if tak-network exists
if ! docker network ls | grep -q "tak-network"; then
    echo "⚠️  tak-network not found. Creating it..."
    docker network create tak-network
    echo "✅ Created tak-network"
else
    echo "✅ tak-network already exists"
fi

# Connect TAK Server to network if not already connected
if ! docker network inspect tak-network | grep -q "tak-server-tak-1"; then
    echo "🔗 Connecting TAK Server to tak-network..."
    docker network connect tak-network tak-server-tak-1
    echo "✅ Connected TAK Server to tak-network"
else
    echo "✅ TAK Server already connected to tak-network"
fi

echo ""
echo "✅ Network setup complete!"
echo "📝 TAK Server TCP connection: tcp://tak-server-tak-1:8087"
echo "📝 No certificates needed - using anonymous authentication"
EOF

chmod +x setup-network.sh

# Create user systemd service file
log_step "Creating user systemd service..."
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/austin-atak-integrations.service << EOF
[Unit]
Description=Austin ATAK Integrations Service
Requires=docker.service
After=docker.service
StartLimitInterval=0

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$DEPLOY_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=default.target
EOF

# Create update script
log_step "Creating update script..."
cat > update.sh << 'EOF'
#!/bin/bash
# Update script for Austin ATAK Integrations

echo "🔄 Updating Austin ATAK Integrations"
echo "===================================="

# Pull latest changes
echo "📥 Pulling latest changes..."
git pull

# Rebuild and restart
echo "🔨 Rebuilding and restarting..."
docker-compose down
docker-compose build --no-cache
docker-compose up -d

echo "✅ Update complete!"
echo "📊 Check status: docker-compose ps"
echo "📋 Check logs: docker-compose logs -f"
EOF

chmod +x update.sh

# Create data and logs directories
mkdir -p data logs

log_info "Production setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Run: ./setup-network.sh"
echo "2. Run: docker-compose up -d"
echo "3. Enable user service: systemctl --user enable austin-atak-integrations"
echo "4. Start user service: systemctl --user start austin-atak-integrations"
echo ""
echo "📊 Monitor the service:"
echo "   - Health: curl http://localhost:8080/health"
echo "   - Stats: curl http://localhost:8080/stats"
echo "   - Logs: docker-compose logs -f"
echo "   - Status: docker-compose ps"
echo ""
echo "🔄 Update the service:"
echo "   - Run: ./update.sh"
echo ""
echo "🔗 TAK Server Connection:"
echo "   - Protocol: TCP (no certificates needed)"
echo "   - Address: tcp://tak-server-tak-1:8087"
echo "   - Authentication: Anonymous"
