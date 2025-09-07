#!/bin/bash
# FFmpeg Installation Script for Rocky Linux 9
# Resolves dependency issues and installs FFmpeg properly

set -e

echo "🎬 FFmpeg Installation for Rocky Linux 9"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please run this script as a regular user with sudo privileges"
    exit 1
fi

# Check OS version
if ! grep -q "Rocky Linux release 9" /etc/redhat-release 2>/dev/null; then
    print_warning "This script is optimized for Rocky Linux 9"
    print_warning "It may work on other RHEL 9 derivatives but is not tested"
fi

echo "🔍 Step 1: Enabling required repositories..."

# Install EPEL repository
echo "Installing EPEL repository..."
sudo dnf install epel-release -y

# Enable CodeReady Builder (CRB) repository
echo "Enabling CRB repository..."
sudo dnf config-manager --set-enabled crb

# Install RPM Fusion repositories
echo "Installing RPM Fusion repositories..."
sudo dnf install --nogpgcheck \
    https://mirrors.rpmfusion.org/free/el/rpmfusion-free-release-9.noarch.rpm \
    https://mirrors.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-9.noarch.rpm -y

print_success "Repositories configured"

echo "🔄 Step 2: Updating package cache..."
sudo dnf update -y

echo "📦 Step 3: Installing dependencies..."
# Install LADSPA plugins (required dependency that was missing)
sudo dnf install ladspa -y

# Install additional audio libraries
sudo dnf install alsa-lib-devel -y

print_success "Dependencies installed"

echo "🎥 Step 4: Installing FFmpeg..."
sudo dnf install ffmpeg ffmpeg-devel -y

print_success "FFmpeg installation completed"

echo "🔍 Step 5: Verifying installation..."

if command -v ffmpeg >/dev/null 2>&1; then
    print_success "FFmpeg is available in PATH"
    
    # Get version
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n1)
    echo "Version: $FFMPEG_VERSION"
    
    # Test basic functionality
    echo "Testing basic functionality..."
    if ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=1 -f null - >/dev/null 2>&1; then
        print_success "FFmpeg functionality test passed"
    else
        print_warning "FFmpeg basic test failed, but binary is installed"
    fi
else
    print_error "FFmpeg installation failed"
    exit 1
fi

echo ""
echo "🎉 FFmpeg installation completed successfully!"
echo "You can now run MediaCraft video processing features."
echo ""
echo "📋 Next steps:"
echo "1. Restart your MediaCraft backend service"
echo "2. Test video merge functionality"
echo "3. Check application logs for any remaining issues"