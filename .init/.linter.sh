#!/bin/bash
cd /home/kavia/workspace/code-generation/app-metrics-dashboard-f6d66a19/backend_fastapi
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

