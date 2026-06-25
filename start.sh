#!/bin/bash
set -e

# Railway uses python3, not python
PYTHON=$(which python3 || which python)

# Train models if not present (first deploy)
if [ ! -f "backend/ml/models/hmm_regime.joblib" ]; then
  echo "Training ML models (first-time setup)..."
  $PYTHON -m backend.ml.train_models
fi

# Start FastAPI server
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
