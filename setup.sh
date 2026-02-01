#!/bin/bash
# =============================================================================
# NotebookLM MCP - One-Click Installer for Antigravity IDE
# =============================================================================
set -e

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     NotebookLM MCP Server - Antigravity One-Click Installer      ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Step 1: Check Python
echo -e "${BLUE}[1/5]${NC} Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "      ${GREEN}✓${NC} $PYTHON_VERSION"
else
    echo -e "      ${RED}✗ Python3 not found. Please install Python 3.11+${NC}"
    exit 1
fi

# Step 2: Install Python dependencies
echo -e "${BLUE}[2/5]${NC} Installing Python dependencies..."
if command -v uv &> /dev/null; then
    uv pip install -e . --quiet
elif command -v pip3 &> /dev/null; then
    pip3 install -e . --quiet
else
    pip install -e . --quiet
fi
echo -e "      ${GREEN}✓${NC} Dependencies installed"

# Step 3: Install Patchright browser
echo -e "${BLUE}[3/5]${NC} Installing browser engine..."
mkdir -p .tmp .browsers
TMPDIR=$(pwd)/.tmp PLAYWRIGHT_BROWSERS_PATH=$(pwd)/.browsers python3 -m patchright install chromium --quiet 2>/dev/null || \
TMPDIR=$(pwd)/.tmp PLAYWRIGHT_BROWSERS_PATH=$(pwd)/.browsers python3 -m patchright install chromium
echo -e "      ${GREEN}✓${NC} Browser engine ready"

# Step 4: Google OAuth Authentication
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}[4/5]${NC} ${YELLOW}Google 계정 로그인${NC}"
echo ""
echo "      브라우저가 열립니다. Google 계정으로 로그인하세요."
echo "      로그인 후 자동으로 인증이 완료됩니다."
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
read -p "      준비되면 Enter를 누르세요..."

python3 -m notebooklm_mcp.auth || {
    echo -e "      ${RED}✗ 인증 실패. 다시 시도하려면: notebooklm-mcp-auth${NC}"
    exit 1
}

# Step 5: Register with Antigravity
echo ""
echo -e "${BLUE}[5/5]${NC} Antigravity IDE에 등록 중..."
python3 install.py --json > /tmp/notebooklm_install_result.json 2>/dev/null

INSTALL_STATUS=$(python3 -c "import json; print(json.load(open('/tmp/notebooklm_install_result.json'))['status'])" 2>/dev/null || echo "unknown")

if [ "$INSTALL_STATUS" = "success" ] || [ "$INSTALL_STATUS" = "already_installed" ]; then
    echo -e "      ${GREEN}✓${NC} Antigravity 설정 완료!"
else
    echo -e "      ${YELLOW}!${NC} 자동 등록 실패 - 수동으로 설정이 필요할 수 있습니다."
fi

# Done!
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    🎉 설치 완료!                                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  다음 단계:"
echo "  1. Antigravity IDE를 재시작하세요"
echo "  2. Settings → Manage MCP Servers 에서 'notebooklm-mcp' 확인"
echo "  3. 에이전트에게 \"List my NotebookLM notebooks\" 요청"
echo ""
echo "  문제가 있으면:"
echo "  • 재인증: notebooklm-mcp-auth"
echo "  • 수동 등록: python install.py"
echo ""
