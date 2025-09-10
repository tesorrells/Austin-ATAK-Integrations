#!/bin/bash
# Git-based deployment script for Austin ATAK Integrations
# Run this on your DigitalOcean server as a regular user

set -e

echo "🚀 Austin ATAK Integrations - Git Deployment"
echo "============================================="

# Configuration
DEPLOY_DIR="$HOME/austin-atak-integrations"
SERVICE_NAME="austin-atak-integrations"

# Check if we're running as root and adjust accordingly
if [ "$EUID" -eq 0 ]; then
    log_warn "Running as root. Using /opt/austin-atak-integrations instead of home directory."
    DEPLOY_DIR="/opt/austin-atak-integrations"
fi

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
    echo "  sudo apt update && sudo apt install git"
    exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    log_warn "Docker is not installed. You'll need to install it:"
    echo "  curl -fsSL https://get.docker.com -o get-docker.sh"
    echo "  sh get-docker.sh"
    echo "  sudo usermod -aG docker \$USER"
    echo "  # Then log out and back in"
    exit 1
fi

# Check if user is in docker group
if ! groups | grep -q docker; then
    log_warn "User is not in docker group. You may need to:"
    echo "  sudo usermod -aG docker \$USER"
    echo "  # Then log out and back in"
    echo ""
    echo "Continuing anyway - you can fix this later..."
fi

log_step "Setting up deployment directory..."

# Create or update deployment directory
if [ -d "$DEPLOY_DIR" ]; then
    log_info "Updating existing deployment directory..."
    cd "$DEPLOY_DIR"
    
    # Check if it's a git repository
    if [ -d ".git" ]; then
        log_info "Pulling latest changes..."
        git pull
    else
        log_warn "Directory exists but is not a git repository"
        log_info "Removing existing directory and starting fresh..."
        cd ..
        rm -rf "$DEPLOY_DIR"
        mkdir -p "$DEPLOY_DIR"
        cd "$DEPLOY_DIR"
        
        # Clone the repository
        REPO_URL="https://github.com/tesorrells/Austin-ATAK-Integrations.git"
        log_info "Cloning repository from: $REPO_URL"
        git clone "$REPO_URL" .
    fi
else
    log_info "Creating new deployment directory..."
    mkdir -p "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
    
    # Clone the repository
    REPO_URL="https://github.com/tesorrells/Austin-ATAK-Integrations.git"
    log_info "Cloning repository from: $REPO_URL"
    git clone "$REPO_URL" .
fi

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
