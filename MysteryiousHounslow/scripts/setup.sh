#!/bin/bash

# Matchgorithm Development Setup Script
# Sets up complete development environment with UV package management

set -e

echo "🚀 Matchgorithm Development Environment Setup"
echo "=============================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if tool is installed
check_tool() {
    local tool=$1
    local install_cmd=$2

    if command -v "$tool" &> /dev/null; then
        echo -e "${GREEN}✅ $tool found${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  $tool not found${NC}"
        echo -e "${BLUE}Install with: $install_cmd${NC}"
        return 1
    fi
}

# Function to install UV
install_uv() {
    echo -e "\n${BLUE}Installing UV package manager...${NC}"
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        echo -e "${GREEN}✅ UV installed successfully${NC}"
        export PATH="$HOME/.local/bin:$PATH"
        return 0
    else
        echo -e "${RED}❌ UV installation failed${NC}"
        return 1
    fi
}

# Check system requirements
echo "🔍 Checking system requirements..."
echo "-----------------------------------"

# Check Rust
if check_tool "cargo" "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"; then
    echo "Checking Rust version..."
    cargo --version
fi

# Check Python
if check_tool "python3" "apt install python3"; then
    echo "Checking Python version..."
    python3 --version
fi

# Check Podman
check_tool "podman" "apt install podman"

# Check UV
if ! check_tool "uv" "curl -LsSf https://astral.sh/uv/install.sh | sh"; then
    if install_uv; then
        # Re-check after installation
        check_tool "uv" "curl -LsSf https://astral.sh/uv/install.sh | sh"
    fi
fi

echo -e "\n${BLUE}Setting up Python environment with UV...${NC}"
echo "---------------------------------------------"

# Setup FastAPI environment
if [ -d "fastapi_xgboost_optimizer" ]; then
    cd fastapi_xgboost_optimizer

    echo "Installing Python dependencies..."
    if uv pip install -e .; then
        echo -e "${GREEN}✅ Python dependencies installed${NC}"
    else
        echo -e "${RED}❌ Python dependency installation failed${NC}"
        exit 1
    fi

    echo "Installing development dependencies..."
    if uv pip install -e ".[dev]"; then
        echo -e "${GREEN}✅ Development dependencies installed${NC}"
    else
        echo -e "${YELLOW}⚠️  Development dependencies optional${NC}"
    fi

    cd ..
else
    echo -e "${YELLOW}⚠️  FastAPI directory not found${NC}"
fi

echo -e "\n${BLUE}Setting up Rust environment...${NC}"
echo "----------------------------------"

# Check if Rust project is valid
if [ -f "Cargo.toml" ]; then
    echo "Checking Rust dependencies..."
    if cargo check; then
        echo -e "${GREEN}✅ Rust dependencies OK${NC}"
    else
        echo -e "${RED}❌ Rust dependency check failed${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Cargo.toml not found${NC}"
fi

echo -e "\n${BLUE}Setting up container environment...${NC}"
echo "----------------------------------------"

# Check Podman networks
echo "Checking Podman networks..."
if podman network exists edge-net 2>/dev/null && \
   podman network exists auth-net 2>/dev/null && \
   podman network exists db-net 2>/dev/null; then
    echo -e "${GREEN}✅ Podman networks configured${NC}"
else
    echo -e "${YELLOW}⚠️  Podman networks not configured${NC}"
    echo -e "${BLUE}Run: podman network create --subnet=10.0.1.0/24 edge-net${NC}"
    echo -e "${BLUE}      podman network create --subnet=10.0.2.0/24 --internal auth-net${NC}"
    echo -e "${BLUE}      podman network create --subnet=10.0.3.0/24 --internal db-net${NC}"
fi

echo -e "\n${BLUE}Running security checks...${NC}"
echo "-------------------------------"

# Run security scan if script exists
if [ -f "scripts/security_scan.sh" ]; then
    echo "Running security scan..."
    if ./scripts/security_scan.sh; then
        echo -e "${GREEN}✅ Security scan passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Security scan had warnings (check output above)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Security scan script not found${NC}"
fi

echo -e "\n${GREEN}🎉 Development environment setup complete!${NC}"
echo ""
echo "📋 Next steps:"
echo "1. Start services: podman-compose up -d"
echo "2. Check health: curl http://localhost/api/health"
echo "3. View docs: open docs/README.md"
echo ""
echo "🛠️  Available commands:"
echo "   - Rust development: cargo run"
echo "   - Python development: cd fastapi_xgboost_optimizer && uv run uvicorn app.main:app --reload"
echo "   - Security scan: ./scripts/security_scan.sh"
echo "   - Network check: ./scripts/verify_network.sh"
echo ""
echo "📚 Documentation:"
echo "   - docs/network_setup.md - Network configuration"
echo "   - docs/devsecops_implementation.md - Security practices"
echo "   - docs/deployment.md - Production deployment"
echo ""
echo "🚀 Happy coding!"