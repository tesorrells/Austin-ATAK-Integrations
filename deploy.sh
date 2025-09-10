#!/bin/bash
# Simple deployment script for Austin ATAK Integrations
# Run this on your DigitalOcean server

set -e

echo "🚀 Austin ATAK Integrations - Simple Deployment"
echo "==============================================="

# Configuration
DEPLOY_DIR="/opt/austin-atak-integrations"
REPO_URL="https://github.com/tesorrells/Austin-ATAK-Integrations.git"

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

# Check if git is available
if ! command -v git &> /dev/null; then
    log_error "Git is not installed. Please install git first:"
    echo "  apt update && apt install git"
    exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    log_warn "Docker is not installed. You'll need to install it:"
    echo "  curl -fsSL https://get.docker.com -o get-docker.sh"
    echo "  sh get-docker.sh"
    exit 1
fi

log_step "Setting up deployment directory..."

# Remove existing directory if it exists
if [ -d "$DEPLOY_DIR" ]; then
    log_info "Removing existing directory: $DEPLOY_DIR"
    rm -rf "$DEPLOY_DIR"
fi

# Create deployment directory
log_info "Creating deployment directory: $DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

# Clone the repository
log_info "Cloning repository from: $REPO_URL"
git clone "$REPO_URL" .

log_info "Deployment directory setup complete!"
echo ""
echo "📁 Deployment directory: $DEPLOY_DIR"
echo "🎯 Next steps:"
echo "1. Run: ./setup-git-production.sh"
echo "2. Run: ./setup-network.sh"
echo "3. Run: docker-compose up -d"
echo ""
echo "📊 Monitor with:"
echo "   - docker-compose logs -f"
echo "   - curl http://localhost:8080/health"
