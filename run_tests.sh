#!/bin/bash
# Test runner script for the robot project

# Exit on error
set -e

echo "=== Running Unit Tests ==="
python -m pytest tests/unit/ -v --cov=src --cov-report=term-missing

echo -e "\n=== Running Integration Tests ==="
python -m pytest tests/integration/ -v

echo -e "\n=== Running End-to-End Tests ==="
python -m pytest tests/e2e/ -v

echo -e "\n=== Running Static Code Analysis ==="
flake8 src/ tests/
mypy src/ tests/

echo -e "\n=== All tests completed successfully! ==="
