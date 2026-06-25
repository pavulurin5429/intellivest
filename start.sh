#!/bin/bash
set -e

# Train models if not present (first deploy)
if [ ! -f "backend/ml/models/hmm_regime.joblib" ]; then
  echo "Training ML models (first-time setup)..."
  python -m backend.ml.train_models
fi

# Start FastAPI server
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
