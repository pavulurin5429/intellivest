#!/bin/bash
set -e

echo "========================================"
echo " Investment Intelligence Platform Setup"
echo "========================================"

# Backend
echo ""
echo "[1/4] Creating Python virtual environment..."
cd backend
python3 -m venv venv
source venv/bin/activate

echo "[2/4] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "[3/4] Setting up environment file..."
cd ..
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
  echo "IMPORTANT: Edit .env and add your API keys before running!"
else
  echo ".env already exists — skipping"
fi

# Frontend
echo ""
echo "[4/4] Installing frontend dependencies..."
cd frontend
npm install

cd ..
echo ""
echo "========================================"
echo " Setup complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your free API keys:"
echo "     - GROQ_API_KEY     -> console.groq.com (free)"
echo "     - PINECONE_API_KEY -> pinecone.io (free)"
echo "     - SUPABASE_URL/KEY -> supabase.com (free)"
echo "     - ALPACA keys      -> alpaca.markets (free paper)"
echo ""
echo "  2. Start the backend:"
echo "     cd backend && source venv/bin/activate"
echo "     uvicorn main:app --reload --port 8000"
echo ""
echo "  3. Start the frontend (new terminal):"
echo "     cd frontend && npm run dev"
echo ""
echo "  4. Open http://localhost:3000"
echo ""
