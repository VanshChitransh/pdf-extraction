#!/bin/bash
# Installation script for AI cost estimation dependencies

echo "==========================================="
echo "Installing AI Cost Estimation Dependencies"
echo "==========================================="
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not activated!"
    echo "Please run: source venv/bin/activate"
    echo ""
    exit 1
fi

echo "✓ Virtual environment detected: $VIRTUAL_ENV"
echo ""

echo "Installing dependencies..."
echo ""

# Install with trusted hosts to avoid SSL issues
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org \
    google-generativeai \
    reportlab \
    Pillow \
    python-dotenv \
    tenacity

if [ $? -eq 0 ]; then
    echo ""
    echo "==========================================="
    echo "✓ Installation Complete!"
    echo "==========================================="
    echo ""
    echo "Next steps:"
    echo "  1. Set your API key:"
    echo "     export GEMINI_API_KEY='your_key_here'"
    echo ""
    echo "  2. Run validation:"
    echo "     python validate_implementation.py"
    echo ""
    echo "  3. Run example:"
    echo "     python estimate_example.py"
    echo ""
else
    echo ""
    echo "❌ Installation failed!"
    echo ""
    echo "Try manual installation:"
    echo "  pip install google-generativeai"
    echo "  pip install reportlab"
    echo "  pip install Pillow"
    echo "  pip install python-dotenv"
    echo "  pip install tenacity"
    echo ""
    exit 1
fi

