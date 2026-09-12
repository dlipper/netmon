#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=================================================="
echo "    NetMon - Installation & Service Setup         "
echo "=================================================="

# 0. Check prerequisites
if ! python3 -c "import venv" >/dev/null 2>&1; then
    echo "Error: Python 3 'venv' module is not installed."
    echo "On Debian/Raspberry Pi OS/Ubuntu, run: sudo apt install -y python3-venv"
    exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
    echo "Error: 'curl' is required but not installed."
    echo "Please install it with: sudo apt install -y curl"
    exit 1
fi

# 1. Setup Python virtual environment
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$PROJECT_DIR/venv"
fi

echo "Installing/updating Python dependencies..."
"$PROJECT_DIR/venv/bin/pip" install --quiet --upgrade pip
"$PROJECT_DIR/venv/bin/pip" install --quiet -r "$PROJECT_DIR/requirements.txt"

# 2. Download native Ookla Speedtest CLI binary if not present
mkdir -p "$PROJECT_DIR/bin"
if [ ! -f "$PROJECT_DIR/bin/speedtest-ookla" ]; then
    ARCH=$(uname -m)
    echo "Detected architecture: $ARCH"
    OOKLA_URL=""
    if [ "$ARCH" = "aarch64" ]; then
        OOKLA_URL="https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-linux-aarch64.tgz"
    elif [ "$ARCH" = "x86_64" ]; then
        OOKLA_URL="https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-linux-x86_64.tgz"
    elif [ "$ARCH" = "armv7l" ] || [ "$ARCH" = "armhf" ]; then
        OOKLA_URL="https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-linux-armhf.tgz"
    else
        echo "Unsupported architecture for prebuilt binary: $ARCH. Please install Ookla CLI manually."
    fi

    if [ -n "$OOKLA_URL" ]; then
        echo "Downloading official Ookla Speedtest binary..."
        curl -sSL "$OOKLA_URL" -o /tmp/ookla-speedtest.tgz
        tar -xzf /tmp/ookla-speedtest.tgz -C "$PROJECT_DIR/bin"
        mv "$PROJECT_DIR/bin/speedtest" "$PROJECT_DIR/bin/speedtest-ookla"
        rm -f /tmp/ookla-speedtest.tgz "$PROJECT_DIR/bin/speedtest.5" "$PROJECT_DIR/bin/speedtest.md"
        chmod +x "$PROJECT_DIR/bin/speedtest-ookla"
        echo "✓ Ookla speedtest binary installed to bin/speedtest-ookla"
    fi
fi

chmod +x "$PROJECT_DIR/bin/speedtest-cli" "$PROJECT_DIR/app/cli.py"

# 3. Setup CLI command symlinks
echo "Setting up 'speedtest' command..."
mkdir -p ~/.local/bin
ln -sf "$PROJECT_DIR/bin/speedtest-cli" ~/.local/bin/speedtest
echo "✓ Symlinked ~/.local/bin/speedtest"

if command -v sudo >/dev/null 2>&1; then
    sudo ln -sf "$PROJECT_DIR/bin/speedtest-cli" /usr/local/bin/speedtest 2>/dev/null || true
    echo "✓ Symlinked /usr/local/bin/speedtest"

    # 4. Install systemd service
    CURRENT_USER="${SUDO_USER:-$USER}"
    CURRENT_GROUP="$(id -gn "$CURRENT_USER" 2>/dev/null || echo "$CURRENT_USER")"

    echo "Configuring systemd service (/etc/systemd/system/netmon.service) for user '$CURRENT_USER'..."
    sed -e "s|%USER%|$CURRENT_USER|g" \
        -e "s|%GROUP%|$CURRENT_GROUP|g" \
        -e "s|%PROJECT_DIR%|$PROJECT_DIR|g" \
        "$PROJECT_DIR/netmon.service" | sudo tee /etc/systemd/system/netmon.service >/dev/null

    sudo systemctl daemon-reload
    sudo systemctl enable netmon.service
    sudo systemctl restart netmon.service
    echo "✓ netmon.service configured, enabled, and started on port 80!"
    echo ""
    sudo systemctl status netmon.service --no-pager
else
    echo "Notice: sudo not available or password required. To run manually:"
    echo "  $PROJECT_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080"
fi

echo ""
echo "=================================================="
echo "Installation complete!"
echo "Web Dashboard: http://localhost or http://$(hostname -I | awk '{print $1}')"
echo "CLI Command  : speedtest"
echo "=================================================="
