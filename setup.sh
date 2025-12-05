#!/bin/bash
echo "╔═══════════════════════════════════════╗"
echo "║   FuzzAI Setup & Installation         ║"
echo "╚═══════════════════════════════════════╝"
echo ""
echo "[1/3] Checking Python version..."
python3 --version
echo ""
echo "[2/3] Installing dependencies..."
pip3 install -r requirements.txt
echo ""
echo "[3/3] Setup complete!"
echo ""
echo "Quick start:"
echo "  python3 fuzzai.py -u https://example.com/FUZZ -ai 'admin pages'"
echo ""
