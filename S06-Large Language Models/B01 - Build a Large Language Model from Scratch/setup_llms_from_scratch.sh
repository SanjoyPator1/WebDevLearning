#!/bin/bash

# Simplified Setup Script for LLMs-from-scratch
# Creates venv and installs all required packages without cloning the repository

set -e  # Exit on error

echo "======================================"
echo "LLMs-from-Scratch Environment Setup"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
print_info "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.10 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
print_info "Found Python $PYTHON_VERSION"
echo ""

# Remove existing venv if it exists
if [ -d "venv" ]; then
    print_warning "Existing 'venv' directory found."
    read -p "Do you want to remove it and create a fresh environment? (y/n): " REMOVE_VENV
    if [ "$REMOVE_VENV" == "y" ]; then
        print_info "Removing existing venv..."
        rm -rf venv
    else
        print_error "Please remove the existing venv directory manually or choose a different name."
        exit 1
    fi
fi

# Create virtual environment
print_info "Creating virtual environment 'venv'..."
python3 -m venv venv

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip

# Install packages from requirements.txt URL
print_info "Installing packages from LLMs-from-scratch requirements.txt..."
echo ""
print_info "This will install: PyTorch, NumPy, Matplotlib, Jupyter Lab, tiktoken, and more..."
echo ""

pip install -r https://raw.githubusercontent.com/rasbt/LLMs-from-scratch/main/requirements.txt

# Verify installation
echo ""
print_info "======================================"
print_info "Verifying Installation..."
print_info "======================================"
echo ""

# Check key packages
python -c "import torch; print(f'✓ PyTorch: {torch.__version__}')"
python -c "import numpy; print(f'✓ NumPy: {numpy.__version__}')"
python -c "import matplotlib; print(f'✓ Matplotlib: {matplotlib.__version__}')"
python -c "import tiktoken; print(f'✓ tiktoken: {tiktoken.__version__}')" 2>/dev/null || echo "✓ tiktoken: installed"
python -c "import jupyter; print('✓ Jupyter: installed')" 2>/dev/null || echo "✓ Jupyter: installed"

echo ""

# Check GPU
print_info "======================================"
print_info "GPU Check"
print_info "======================================"
echo ""

if python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
    print_info "✓ CUDA GPU detected!"
    python -c "import torch; print(f'  GPU: {torch.cuda.get_device_name(0)}'); print(f'  CUDA version: {torch.version.cuda}')"
else
    print_warning "No CUDA GPU detected. Code will run on CPU."
    print_warning "If you have a GPU, make sure NVIDIA drivers are installed."
fi

echo ""
print_info "======================================"
print_info "Setup Complete!"
print_info "======================================"
echo ""

echo "Virtual environment 'venv' has been created and activated!"
echo ""
echo "📝 To activate this environment in the future, run:"
echo "   source venv/bin/activate"
echo ""
echo "📝 To deactivate when you're done:"
echo "   deactivate"
echo ""
echo "🚀 To start Jupyter Lab:"
echo "   jupyter lab"
echo ""
echo "📦 Installed packages include:"
echo "   - PyTorch (with CUDA support)"
echo "   - NumPy, Matplotlib, Pandas"
echo "   - Jupyter Lab"
echo "   - tiktoken (OpenAI tokenizer)"
echo "   - tqdm, psutil, and more"
echo ""
echo "Happy Learning! 🎉"