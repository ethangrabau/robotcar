.PHONY: test test-unit test-integration test-e2e lint format check-format install-dev clean

# Python interpreter
PYTHON = python3
PIP = pip3

# Directories
SRC_DIR = src
TESTS_DIR = tests
UNIT_TESTS_DIR = $(TESTS_DIR)/unit
INTEGRATION_TESTS_DIR = $(TESTS_DIR)/integration
E2E_TESTS_DIR = $(TESTS_DIR)/e2e

# Test options
TEST_OPTS = -v --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=html

# Install development dependencies
install-dev:
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-cov black flake8 mypy

# Run all tests
test: test-unit test-integration test-e2e

# Run unit tests
test-unit:
	$(PYTHON) -m pytest $(TEST_OPTS) $(UNIT_TESTS_DIR)

# Run integration tests
test-integration:
	$(PYTHON) -m pytest $(TEST_OPTS) $(INTEGRATION_TESTS_DIR)

# Run end-to-end tests
test-e2e:
	$(PYTHON) -m pytest $(TEST_OPTS) $(E2E_TESTS_DIR)

# Lint the code
lint:
	flake8 $(SRC_DIR) $(TESTS_DIR)
	mypy $(SRC_DIR) $(TESTS_DIR)

# Format the code
format:
	black $(SRC_DIR) $(TESTS_DIR)

# Check code formatting
check-format:
	black --check $(SRC_DIR) $(TESTS_DIR)

# Clean up temporary files
clean:
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type f -name '*~' -delete
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/

# Default target
.DEFAULT_GOAL := test
