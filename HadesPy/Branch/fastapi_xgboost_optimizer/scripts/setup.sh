#!/bin/bash

# Setup script for FastAPI XGBoost Optimizer
# This script helps set up the development environment

set -e

echo "🚀 Setting up FastAPI XGBoost Optimizer..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.11+ is installed
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        REQUIRED_VERSION="3.11"
        
        if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
            print_status "Python $PYTHON_VERSION is installed ✓"
        else
            print_error "Python 3.11+ is required. Current version: $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 is not installed"
        exit 1
    fi
}

# Check if Docker and Docker Compose are installed
check_docker() {
    if command -v docker &> /dev/null; then
        print_status "Docker is installed ✓"
    else
        print_warning "Docker is not installed. You'll need it for PostgreSQL and Hasura."
    fi
    
    if command -v docker-compose &> /dev/null; then
        print_status "Docker Compose is installed ✓"
    else
        print_warning "Docker Compose is not installed. You'll need it for running services."
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p models/xgboost
    mkdir -p config
    mkdir -p data
    
    print_status "Directories created ✓"
}

# Setup Python virtual environment
setup_virtual_env() {
    print_status "Setting up Python virtual environment..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_status "Virtual environment created ✓"
    else
        print_status "Virtual environment already exists ✓"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    print_status "Virtual environment activated ✓"
}

# Install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    
    # Install base requirements
    pip install -r requirements/base.txt
    
    # Install development requirements
    pip install -r requirements/dev.txt
    
    print_status "Dependencies installed ✓"
}

# Setup environment file
setup_env_file() {
    if [ ! -f ".env" ]; then
        print_status "Creating .env file..."
        cp .env.example .env
        print_warning "Please edit .env file with your configuration"
    else
        print_status ".env file already exists ✓"
    fi
}

# Setup pre-commit hooks
setup_precommit() {
    print_status "Setting up pre-commit hooks..."
    
    if command -v pre-commit &> /dev/null; then
        pre-commit install
        print_status "Pre-commit hooks installed ✓"
    else
        print_warning "pre-commit is not installed. Skipping hook setup."
    fi
}

# Setup database (if PostgreSQL is running)
setup_database() {
    print_status "Setting up database..."
    
    # Check if PostgreSQL is running
    if docker-compose ps postgres | grep -q "Up"; then
        print_status "PostgreSQL is running, setting up database..."
        
        # Wait for PostgreSQL to be ready
        print_status "Waiting for PostgreSQL to be ready..."
        sleep 10
        
        # Run migrations
        if command -v alembic &> /dev/null; then
            alembic upgrade head
            print_status "Database migrations completed ✓"
        else
            print_warning "Alembic not found. Skipping database migrations."
        fi
    else
        print_warning "PostgreSQL is not running. Please start it with: docker-compose up -d postgres"
    fi
}

# Create initial models
create_initial_models() {
    print_status "Creating initial models..."
    
    # Create a simple script to generate initial XGBoost models
    cat > create_initial_models.py << 'EOF'
import os
import numpy as np
import xgboost as xgb
from pathlib import Path

# Create models directory
models_dir = Path("models/xgboost")
models_dir.mkdir(parents=True, exist_ok=True)

# Create dummy scoring model
print("Creating initial XGBoost scoring model...")
scoring_model = xgb.XGBRegressor(
    n_estimators=50,
    max_depth=3,
    learning_rate=0.1,
    random_state=42,
)

# Train on dummy data
dummy_X = np.random.rand(100, 10)
dummy_y = np.random.rand(100)
scoring_model.fit(dummy_X, dummy_y)

# Save model
scoring_model.save_model(str(models_dir / "scoring_model.json"))
print("Initial scoring model created ✓")

print("Initial models created successfully!")
EOF

    python3 create_initial_models.py
    rm create_initial_models.py
    
    print_status "Initial models created ✓"
}

# Main setup function
main() {
    print_status "Starting setup for FastAPI XGBoost Optimizer..."
    
    # Run all setup steps
    check_python
    check_docker
    create_directories
    setup_virtual_env
    install_dependencies
    setup_env_file
    setup_precommit
    create_initial_models
    
    print_status "Setup completed successfully! 🎉"
    print_status ""
    print_status "Next steps:"
    print_status "1. Edit .env file with your configuration"
    print_status "2. Start PostgreSQL and Hasura: docker-compose up -d postgres hasura"
    print_status "3. Run database setup: ./scripts/setup.sh"
    print_status "4. Start the application: uvicorn app.main:app --reload"
    print_status ""
    print_status "For development, you can also use:"
    print_status "- pytest: Run the test suite"
    print_status "- black: Format code"
    print_status "- flake8: Lint code"
    print_status "- mypy: Type checking"
}

# Run main function
main "$@"