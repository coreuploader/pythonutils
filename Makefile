PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON = $(VENV)/bin/python
TEST_FILES := $(wildcard tests/test_*.py)

# Default target executed when you run 'make' without arguments
.DEFAULT_GOAL := help

.PHONY: venv activate source test clean help

# Only create the environment when it is missing; package changes are explicit.
$(VENV)/bin/activate:
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv "$(VENV)"

venv: $(VENV)/bin/activate ## Create the virtual environment if missing

# Bash sources the activation script on startup; exit returns to the parent shell.
activate: venv ## Open an activated Bash shell (use exit to leave)
	bash --rcfile "$(VENV)/bin/activate" -i

source: activate ## Alias for activate

test: venv ## Run tests using the standard-library unittest runner
ifneq ($(strip $(TEST_FILES)),)
	"$(VENV_PYTHON)" -m unittest discover -s tests -v
else
	@echo "No test modules yet."
endif

clean: ## Remove virtual environment and cached Python files
	rm -rf -- "$(VENV)"
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
