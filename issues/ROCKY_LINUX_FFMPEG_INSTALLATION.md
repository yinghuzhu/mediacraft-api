# Rocky Linux 9 FFmpeg Installation Issue

## 🚨 Problem Description
FFmpeg installation fails on Rocky Linux 9 with dependency resolution errors related to `libavfilter`, `librubberband`, and `ladspa` packages.

## 🔍 Error Details
```bash
sudo yum install ffmpeg
Error:
 Problem: package ffmpeg-5.1.6-2.el9.x86_64 from rpmfusion-free-updates requires libavfilter.so.8()(64bit), but none of the providers can be installed
  - package ffmpeg-5.1.6-2.el9.x86_64 from rpmfusion-free-updates requires libavfilter.so.8(LIBAVFILTER_8)(64bit), but none of the providers can be installed
  - package libavfilter-free-5.1.4-3.el9.x86_64 from epel requires librubberband.so.2()(64bit), but none of the providers can be installed
  - package ffmpeg-libs-5.1.6-2.el9.x86_64 from rpmfusion-free-updates requires librubberband.so.2()(64bit), but none of the providers can be installed
  - conflicting requests
  - nothing provides ladspa needed by rubberband-3.1.3-2.el9.x86_64 from epel
```

## ✅ Solution

### Method 1: Enable Required Repositories and Install Dependencies (Recommended)

```bash
# 1. Enable EPEL repository
sudo dnf install epel-release -y

# 2. Enable PowerTools/CRB repository (required for some dependencies)
sudo dnf config-manager --set-enabled crb

# 3. Enable RPM Fusion repositories
sudo dnf install --nogpgcheck https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
sudo dnf install --nogpgcheck https://mirrors.rpmfusion.org/free/el/rpmfusion-free-release-9.noarch.rpm https://mirrors.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-9.noarch.rpm

# 4. Update package cache
sudo dnf update -y

# 5. Install LADSPA plugins (required dependency)
sudo dnf install ladspa -y

# 6. Install FFmpeg
sudo dnf install ffmpeg ffmpeg-devel -y
```

### Method 2: Install from Flatpak (Alternative)

```bash
# Install Flatpak
sudo dnf install flatpak -y

# Add Flathub repository
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Install FFmpeg via Flatpak
flatpak install flathub org.freedesktop.Platform.ffmpeg-full -y

# Create system-wide symlink
sudo ln -sf /var/lib/flatpak/runtime/org.freedesktop.Platform.ffmpeg-full/x86_64/22.08/active/files/bin/ffmpeg /usr/local/bin/ffmpeg
```

### Method 3: Build from Source (Last Resort)

```bash
# Install build dependencies
sudo dnf groupinstall "Development Tools" -y
sudo dnf install nasm yasm-devel -y

# Download and compile FFmpeg
cd /tmp
wget https://ffmpeg.org/releases/ffmpeg-5.1.4.tar.xz
tar -xf ffmpeg-5.1.4.tar.xz
cd ffmpeg-5.1.4

# Configure and build
./configure --enable-gpl --enable-libx264 --enable-libx265 --enable-libvpx --enable-libfdk-aac --enable-libmp3lame --enable-libopus
make -j$(nproc)
sudo make install

# Update library path
sudo ldconfig
```

## 🔧 Verification

After installation, verify FFmpeg is working:

```bash
ffmpeg -version
which ffmpeg
ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=1 -f null -
```

## 🚀 Production Deployment Notes

- **Method 1** is recommended for production as it uses official repositories
- **Method 2** provides isolation but may have performance overhead
- **Method 3** gives full control but requires maintenance

## ⚠️ Troubleshooting

If you still encounter issues:

1. **Clean package cache**: `sudo dnf clean all`
2. **Check enabled repositories**: `sudo dnf repolist`
3. **Try alternative packages**: `sudo dnf search ffmpeg`
4. **Check for conflicts**: `sudo dnf check`

## 📋 Repository Requirements

Ensure these repositories are enabled:
- `epel` - Extra Packages for Enterprise Linux
- `crb` - CodeReady Builder (PowerTools equivalent)
- `rpmfusion-free` - RPM Fusion Free
- `rpmfusion-nonfree` - RPM Fusion Non-free