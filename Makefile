SHELL := /bin/bash

# --- Project metadata --------------------------------------------------------
REPO ?= cvsz/ztemplate
BRANCH ?= main
PERMISSION ?= pull
NAME ?= REPLACE_ME
OWNER ?= REPLACE_ME
CODEOWNER ?= REPLACE_ME
DESCRIPTION ?= REPLACE_ME
APPLY ?= 0
DRY_RUN ?= 1

# --- Tool versions (pin for reproducibility) ---------------------------------
PYTHON := python3
BLACK := $(PYTHON) -m black
RUFF := $(PYTHON) -m ruff
MYPY := $(PYTHON) -m mypy
PYTEST := $(PYTHON) -m pytest
UNITTEST := $(PYTHON) -m unittest
SHELLCHECK := shellcheck
HADOLINT := hadolint

# --- Paths -------------------------------------------------------------------
SCRIPTS_DIR := scripts
TESTS_DIR := tests
GITHUB_DIR := .github
WORKFLOWS_DIR := $(GITHUB_DIR)/workflows
GITHUB_SCRIPTS_DIR := $(GITHUB_DIR)/scripts
DOCS_DIR := docs
TEMPLATES_DIR := templates
SKILLS_DIR := skills
COMPONENTS_DIR := components.d
PLUGINS_DIR := plugins.d

# Python files to check
PY_FILES := $(shell find $(SCRIPTS_DIR) $(TESTS_DIR) src/jarvis -name '*.py' -type f 2>/dev/null | sort)
SH_FILES := $(shell find $(SCRIPTS_DIR) $(GITHUB_SCRIPTS_DIR) -name '*.sh' -type f 2>/dev/null | sort)
YML_FILES := $(shell find $(GITHUB_DIR) -name '*.yml' -o -name '*.yaml' 2>/dev/null | sort)
MD_FILES := $(shell find . -name '*.md' -type f ! -path './.git/*' 2>/dev/null | sort)
DOCKER_FILES := Dockerfile

# --- Colors for output -------------------------------------------------------
BOLD := \033[1m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
BLUE := \033[34m
RESET := \033[0m

# --- Default target ----------------------------------------------------------
.DEFAULT_GOAL := help

# =============================================================================
# HELP
# =============================================================================
.PHONY: help
help: ## Show this help message
	@printf '$(BOLD)ztemplate - GitHub Repository Template Makefile$(RESET)\n\n'
	@printf '$(BOLD)Usage:$(RESET) make <target> [VAR=value]\n\n'
	@printf '$(BOLD)Project Initialization:$(RESET)\n'
	@awk '/^.PHONY:.*install/ {getline; print "  make install           - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*setup/ {getline; print "  make setup             - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*collaborators/ {getline; print "  make collaborators     - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*protect/ {getline; print "  make protect           - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*bootstrap-apply/ {getline; print "  make bootstrap-apply   - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@printf '\n$(BOLD)Code Quality:$(RESET)\n'
	@awk '/^.PHONY:.*format/ {getline; print "  make format            - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*lint/ {getline; print "  make lint              - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*typecheck/ {getline; print "  make typecheck         - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*shellcheck/ {getline; print "  make shellcheck        - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*yamlcheck/ {getline; print "  make yamlcheck         - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*dockerlint/ {getline; print "  make dockerlint        - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@printf '\n$(BOLD)Testing:$(RESET)\n'
	@awk '/^.PHONY:.*test/ {getline; print "  make test              - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*test-verbose/ {getline; print "  make test-verbose      - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*test-coverage/ {getline; print "  make test-coverage     - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@printf '\n$(BOLD)Building:$(RESET)\n'
	@awk '/^.PHONY:.*build/ {getline; print "  make build             - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*docker-build/ {getline; print "  make docker-build      - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*docker-test/ {getline; print "  make docker-test       - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@printf '\n$(BOLD)Security:$(RESET)\n'
	@awk '/^.PHONY:.*security/ {getline; print "  make security          - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*secret-scan/ {getline; print "  make secret-scan       - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*dependency-review/ {getline; print "  make dependency-review - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*codeql/ {getline; print "  make codeql            - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@printf '\n$(BOLD)CI/CD & Validation:$(RESET)\n'
	@awk '/^.PHONY:.*validate/ {getline; print "  make validate          - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*ci/ {getline; print "  make ci                - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*check/ {getline; print "  make check             - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*all/ {getline; print "  make all               - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@printf '\n$(BOLD)Template Sync:$(RESET)\n'
	@awk '/^.PHONY:.*sync/ {getline; print "  make sync              - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*sync-dry/ {getline; print "  make sync-dry          - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@printf '\n$(BOLD)Documentation:$(RESET)\n'
	@awk '/^.PHONY:.*docs-validate/ {getline; print "  make docs-validate     - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*docs-links/ {getline; print "  make docs-links        - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@printf '\n$(BOLD)Release:$(RESET)\n'
	@awk '/^.PHONY:.*version/ {getline; print "  make version           - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*changelog/ {getline; print "  make changelog         - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*tag/ {getline; print "  make tag               - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@printf '\n$(BOLD)Pre-commit:$(RESET)\n'
	@awk '/^.PHONY:.*pre-commit/ {getline; print "  make pre-commit        - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*hooks/ {getline; print "  make hooks             - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@printf '\n$(BOLD)Utilities:$(RESET)\n'
	@awk '/^.PHONY:.*clean/ {getline; print "  make clean             - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*deps/ {getline; print "  make deps              - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*deps-audit/ {getline; print "  make deps-audit        - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@printf '\n$(BOLD)Service Management:$(RESET)\n'
	@awk '/^.PHONY:.*autoloop-start/ {getline; print "  make autoloop-start    - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*autoloop-stop/ {getline; print "  make autoloop-stop     - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*autoloop-restart/ {getline; print "  make autoloop-restart  - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*autoloop-status/ {getline; print "  make autoloop-status   - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*autoloop-enable/ {getline; print "  make autoloop-enable   - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*autoloop-disable/ {getline; print "  make autoloop-disable  - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*autoloop-is-active/ {getline; print "  make autoloop-is-active - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*autoloop-is-enabled/ {getline; print "  make autoloop-is-enabled - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^.PHONY:.*autoloop-live/ {getline; print "  make autoloop-live       - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@awk '/^autoloop: ##/ {print "  make autoloop FLAG=<flag> - " $$0}' $(MAKEFILE_LIST) | sed 's/## / - /'
	@printf '\n$(BOLD)Key Variables:$(RESET)\n'
	@printf '  REPO=%s          - GitHub repo (owner/name)\n' "$(REPO)"
	@printf '  BRANCH=%s        - Default branch\n' "$(BRANCH)"
	@printf '  NAME=%s          - Project name for bootstrap\n' "$(NAME)"
	@printf '  OWNER=%s         - GitHub owner for bootstrap\n' "$(OWNER)"
	@printf '  CODEOWNER=%s     - CODEOWNERS user/team for bootstrap\n' "$(CODEOWNER)"
	@printf '  DESCRIPTION=%s   - One-line description for bootstrap\n' "$(DESCRIPTION)"
	@printf '  APPLY=1          - Apply changes (default: dry-run)\n'
	@printf '  DRY_RUN=1        - Dry-run mode (default: 1)\n'

# =============================================================================
# PROJECT INITIALIZATION
# =============================================================================
.PHONY: install
install: ## Initialize a new repository from this template (dry-run preview + validate)
	@printf '$(BLUE)==> Previewing project identity bootstrap...$(RESET)\n'
	@$(PYTHON) $(SCRIPTS_DIR)/bootstrap.py \
		--name "$(NAME)" \
		--owner "$(OWNER)" \
		--codeowner "$(CODEOWNER)" \
		--description '$(DESCRIPTION)'
	@printf '$(YELLOW)==> To apply the identity changes, run: make bootstrap-apply$(RESET)\n'
	@printf '$(BLUE)==> Validating inherited baseline...$(RESET)\n'
	@$(MAKE) validate

.PHONY: bootstrap-apply
bootstrap-apply: ## Apply bootstrap changes to initialize the repository
	@printf '$(BLUE)==> Applying project identity bootstrap...$(RESET)\n'
	@$(PYTHON) $(SCRIPTS_DIR)/bootstrap.py \
		--name "$(NAME)" \
		--owner "$(OWNER)" \
		--codeowner "$(CODEOWNER)" \
		--description '$(DESCRIPTION)' \
		--apply
	@printf '$(GREEN)==> Bootstrap applied. Verify CODEOWNERS identity has write access.$(RESET)\n'
	@printf '$(YELLOW)==> Next: review LICENSE, SECURITY.md, CI, deployment and IMPLEMENTATION-CHECKLIST.md.$(RESET)\n'

.PHONY: setup
setup: ## New-repository setup: bootstrap preview, validate template, preview protection
	@printf '$(BLUE)==> Step 1: Previewing project identity bootstrap...$(RESET)\n'
	@$(PYTHON) $(SCRIPTS_DIR)/bootstrap.py \
		--name "$(NAME)" \
		--owner "$(OWNER)" \
		--codeowner "$(CODEOWNER)" \
		--description '$(DESCRIPTION)'
	@printf '$(BLUE)==> Step 2: Validating inherited baseline...$(RESET)\n'
	@$(MAKE) validate
	@printf '$(BLUE)==> Step 3: Previewing repository protection...$(RESET)\n'
	@$(MAKE) protect
	@printf '$(GREEN)==> Setup preview complete. Run with APPLY=1 to apply changes.$(RESET)\n'

.PHONY: collaborators
collaborators: ## Add GitHub collaborators (usage: make collaborators COLLABORATORS=user1,user2 [APPLY=1])
	@if [ -z "$(COLLABORATORS)" ]; then \
		printf '$(RED)Usage: make collaborators COLLABORATORS=user1,user2,user3 [REPO=owner/repo] [PERMISSION=pull] [APPLY=1]$(RESET)\n' >&2; \
		exit 2; \
	fi
	@$(PYTHON) $(SCRIPTS_DIR)/github_admin.py \
		--repo "$(REPO)" \
		--collaborators "$(COLLABORATORS)" \
		--collaborator-permission "$(PERMISSION)" \
		$(if $(filter 1,$(APPLY)),--apply,)

.PHONY: protect
protect: ## Apply GitHub branch/secret protection (preview; APPLY=1 to apply)
	@$(PYTHON) $(SCRIPTS_DIR)/github_admin.py \
		--repo "$(REPO)" \
		--branch "$(BRANCH)" \
		$(if $(filter 1,$(APPLY)),--apply --verify,)

# =============================================================================
# CODE QUALITY
# =============================================================================
.PHONY: format
format: ## Run Python formatter check on all Python files (black --check)
	@printf '$(BLUE)==> Checking Python formatting with black...$(RESET)\n'
	@$(BLACK) --check $(PY_FILES)

.PHONY: format-fix
format-fix: ## Auto-fix Python formatting with black
	@printf '$(BLUE)==> Formatting Python files with black...$(RESET)\n'
	@$(BLACK) $(PY_FILES)

.PHONY: lint
lint: ## Run ruff lint on Python files
	@printf '$(BLUE)==> Linting Python files with ruff...$(RESET)\n'
	@$(RUFF) check $(PY_FILES)

.PHONY: lint-fix
lint-fix: ## Auto-fix ruff lint issues
	@printf '$(BLUE)==> Auto-fixing Python lint issues with ruff...$(RESET)\n'
	@$(RUFF) check --fix $(PY_FILES)

.PHONY: typecheck
typecheck: ## Run mypy static type checking on Python scripts
	@printf '$(BLUE)==> Type-checking Python files with mypy...$(RESET)\n'
	@$(MYPY) --explicit-package-bases $(PY_FILES)

.PHONY: shellcheck
shellcheck: ## Run shellcheck on all shell scripts
	@printf '$(BLUE)==> Checking shell script syntax with shellcheck...$(RESET)\n'
	@if [ -n "$(SH_FILES)" ]; then \
		$(SHELLCHECK) -s bash $(SH_FILES); \
	else \
		printf '$(YELLOW)No shell scripts found$(RESET)\n'; \
	fi

.PHONY: yamlcheck
yamlcheck: ## Validate YAML syntax in .github/
	@printf '$(BLUE)==> Validating YAML syntax...$(RESET)\n'
	@if [ -n "$(YML_FILES)" ]; then \
		$(PYTHON) -c "import yaml, sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]" $(YML_FILES); \
		printf '$(GREEN)All YAML files valid$(RESET)\n'; \
	else \
		printf '$(YELLOW)No YAML files found$(RESET)\n'; \
	fi

.PHONY: dockerlint
dockerlint: ## Lint Dockerfile with hadolint
	@printf '$(BLUE)==> Linting Dockerfile with hadolint...$(RESET)\n'
	@if command -v $(HADOLINT) >/dev/null 2>&1; then \
		$(HADOLINT) --failure-threshold=error $(DOCKER_FILES); \
	else \
		printf '$(YELLOW)hadolint not installed, skipping$(RESET)\n'; \
	fi

# =============================================================================
# TESTING
# =============================================================================
.PHONY: test
test: ## Run Python unit tests
	@printf '$(BLUE)==> Running unit tests...$(RESET)\n'
	@$(UNITTEST) discover -s $(TESTS_DIR) -v

.PHONY: test-verbose
test-verbose: ## Run Python unit tests with maximum verbosity
	@printf '$(BLUE)==> Running unit tests (verbose)...$(RESET)\n'
	@$(UNITTEST) discover -s $(TESTS_DIR) -v 2>&1 | head -200

.PHONY: test-coverage
test-coverage: ## Run tests with coverage (requires pytest-cov)
	@printf '$(BLUE)==> Running tests with coverage...$(RESET)\n'
	@if $(PYTHON) -c "import pytest_cov" 2>/dev/null; then \
		$(PYTEST) $(TESTS_DIR) --cov=$(SCRIPTS_DIR) --cov-report=term-missing; \
	else \
		printf '$(YELLOW)pytest-cov not installed, running standard tests$(RESET)\n'; \
		$(MAKE) test; \
	fi

# =============================================================================
# BUILDING
# =============================================================================
.PHONY: build
build: ## Run compilation check on all Python scripts
	@printf '$(BLUE)==> Compiling Python scripts...$(RESET)\n'
	@$(PYTHON) -m py_compile $(PY_FILES)
	@printf '$(GREEN)All Python files compile successfully$(RESET)\n'

.PHONY: docker-build
docker-build: ## Build Docker image
	@printf '$(BLUE)==> Building Docker image...$(RESET)\n'
	@docker build -t ztemplate:local .
	@printf '$(GREEN)Docker image built: ztemplate:local$(RESET)\n'

.PHONY: docker-test
docker-test: docker-build ## Build and test Docker image
	@printf '$(BLUE)==> Testing Docker image...$(RESET)\n'
	@docker run --rm ztemplate:local
	@printf '$(GREEN)Docker test passed$(RESET)\n'

# =============================================================================
# SECURITY
# =============================================================================
.PHONY: security
security: ## Run security and validation checks
	@printf '$(BLUE)==> Running security validation...$(RESET)\n'
	@$(PYTHON) $(SCRIPTS_DIR)/validate_repo.py
	@printf '$(BLUE)==> Checking for tracked secret-bearing files...$(RESET)\n'
	@if git ls-files | grep -E '(^|/)(\.env$$|id_rsa|id_ed25519|.*\.pem|.*\.key)$$' | grep -v '^\.env\.example$$'; then \
		printf '$(RED)ERROR: Potential secret-bearing file is tracked.$(RESET)\n' >&2; \
		exit 1; \
	fi
	@printf '$(GREEN)No tracked secret-bearing files found.$(RESET)\n'

.PHONY: secret-scan
secret-scan: ## Scan for hardcoded secrets in source files (uses validate_repo.py)
	@printf '$(BLUE)==> Scanning for hardcoded secrets...$(RESET)\n'
	@$(PYTHON) $(SCRIPTS_DIR)/validate_repo.py 2>&1 | grep -E "(secret|ERROR|hardcoded)" || true
	@printf '$(GREEN)Secret scan complete$(RESET)\n'

.PHONY: dependency-review
dependency-review: ## Run GitHub Actions dependency review (local simulation)
	@printf '$(BLUE)==> Running dependency review...$(RESET)\n'
	@if command -v gh >/dev/null 2>&1; then \
		gh api /repos/$(REPO)/dependency-graph/sbom 2>/dev/null | head -50 || printf '$(YELLOW)Dependency graph not available locally$(RESET)\n'; \
	else \
		printf '$(YELLOW)gh CLI not available$(RESET)\n'; \
	fi

.PHONY: codeql
codeql: ## Run CodeQL analysis (requires CodeQL CLI)
	@printf '$(BLUE)==> Running CodeQL analysis...$(RESET)\n'
	@if command -v codeql >/dev/null 2>&1; then \
		codeql database create /tmp/ztemplate-db --language=python --source-root=. --overwrite 2>/dev/null && \
		codeql database analyze /tmp/ztemplate-db --format=sarif-latest --output=/tmp/ztemplate-results.sarif 2>/dev/null && \
		printf '$(GREEN)CodeQL analysis complete$(RESET)\n'; \
	else \
		printf '$(YELLOW)CodeQL CLI not installed, skipping$(RESET)\n'; \
	fi

# =============================================================================
# VALIDATION
# =============================================================================
.PHONY: validate
validate: ## Run full repository validation (structure, links, syntax, security)
	@printf '$(BLUE)==> Validating repository structure, links, syntax, and security...$(RESET)\n'
	@$(PYTHON) $(SCRIPTS_DIR)/validate_repo.py
	@printf '$(GREEN)Validation passed$(RESET)\n'

.PHONY: validate-structure
validate-structure: ## Validate required repository structure
	@printf '$(BLUE)==> Validating required paths...$(RESET)\n'
	@$(PYTHON) $(SCRIPTS_DIR)/validate_repo.py 2>&1 | grep -E "missing required path" || printf '$(GREEN)All required paths present.$(RESET)\n'

.PHONY: validate-links
validate-links: ## Validate local Markdown links
	@printf '$(BLUE)==> Validating Markdown links...$(RESET)\n'
	@$(PYTHON) $(SCRIPTS_DIR)/validate_repo.py 2>&1 | grep -E "broken local link|link escapes repository" || printf '$(GREEN)All Markdown links valid.$(RESET)\n'

.PHONY: validate-syntax
validate-syntax: ## Validate Python, shell, and YAML syntax
	@printf '$(BLUE)==> Validating Python syntax...$(RESET)\n'
	@$(PYTHON) -m py_compile $(PY_FILES)
	@printf '$(BLUE)==> Validating shell syntax...$(RESET)\n'
	@if [ -n "$(SH_FILES)" ]; then \
		for sh in $(SH_FILES); do bash -n "$$sh"; done; \
	fi
	@printf '$(BLUE)==> Validating YAML syntax...$(RESET)\n'
	@$(MAKE) yamlcheck
	@printf '$(GREEN)All syntax checks passed$(RESET)\n'

# =============================================================================
# CI/CD SIMULATION
# =============================================================================
.PHONY: ci
ci: ## Run full CI validation suite (validate lint typecheck test build security)
	@printf '$(BOLD)$(BLUE)==> Running full CI validation suite...$(RESET)\n'
	@$(MAKE) validate
	@$(MAKE) lint
	@$(MAKE) typecheck
	@$(MAKE) test
	@$(MAKE) build
	@$(MAKE) security
	@printf '$(BOLD)$(GREEN)==> All CI checks passed!$(RESET)\n'

.PHONY: check
check: ## Dry-run all validations (no mutations)
	@printf '$(BOLD)$(BLUE)==> Running dry-run validation suite...$(RESET)\n'
	@$(MAKE) validate
	@$(MAKE) lint
	@$(MAKE) typecheck
	@$(MAKE) test
	@$(MAKE) build
	@$(MAKE) security
	@printf '$(BOLD)$(GREEN)==> All checks passed (dry-run)!$(RESET)\n'

.PHONY: all
all: ## Run every validation, lint, typecheck, test, build, and security check
	@$(MAKE) ci
	@$(MAKE) shellcheck
	@$(MAKE) dockerlint
	@printf '$(BOLD)$(GREEN)==> Complete validation suite passed!$(RESET)\n'

# =============================================================================
# TEMPLATE SYNC
# =============================================================================
.PHONY: sync
sync: ## Sync upstream template updates (requires gh CLI auth)
	@printf '$(BLUE)==> Syncing upstream template updates...$(RESET)\n'
	@$(PYTHON) $(SCRIPTS_DIR)/sync_template.py
	@$(MAKE) validate
	@$(MAKE) test

.PHONY: sync-dry
sync-dry: ## Dry-run template sync
	@printf '$(BLUE)==> Dry-running template sync...$(RESET)\n'
	@$(PYTHON) $(SCRIPTS_DIR)/sync_template.py --dry-run

.PHONY: sync-state
sync-state: ## Show template sync state
	@if [ -f .github/template-sync-state.json ]; then \
		cat .github/template-sync-state.json; \
	else \
		printf '$(YELLOW)No sync state file found$(RESET)\n'; \
	fi

# =============================================================================
# DOCUMENTATION
# =============================================================================
.PHONY: docs-validate
docs-validate: validate-structure validate-links ## Validate documentation structure and links

.PHONY: docs-links
docs-links: validate-links ## Alias for validate-links

.PHONY: docs-spellcheck
docs-spellcheck: ## Spell-check documentation (requires codespell)
	@printf '$(BLUE)==> Spell-checking documentation...$(RESET)\n'
	@if command -v codespell >/dev/null 2>&1; then \
		codespell $(MD_FILES) --skip=".git,__pycache__,*.pyc" --ignore-words=.codespell-ignore 2>/dev/null || true; \
	else \
		printf '$(YELLOW)codespell not installed, skipping$(RESET)\n'; \
	fi

# =============================================================================
# RELEASE
# =============================================================================
.PHONY: version
version: ## Show current version from CHANGELOG
	@if [ -f CHANGELOG.md ]; then \
		grep -E '^## \[.*\]' CHANGELOG.md | head -1 | sed 's/## \[\(.*\)\].*/\1/'; \
	else \
		printf '$(YELLOW)No CHANGELOG.md found$(RESET)\n'; \
	fi

.PHONY: changelog
changelog: ## Validate CHANGELOG.md format
	@printf '$(BLUE)==> Validating CHANGELOG.md...$(RESET)\n'
	@if [ -f CHANGELOG.md ]; then \
		$(PYTHON) -c "import re; f=open('CHANGELOG.md'); c=f.read(); f.close(); [print('WARNING: Missing \"# Changelog\" header') for _ in [1] if not re.search(r'^# Changelog', c, re.MULTILINE)]; [print('WARNING: No version entries found') for _ in [1] if not re.search(r'^## \[.*\]', c, re.MULTILINE)]; print('CHANGELOG.md structure validated.')"; \
	else \
		printf '$(RED)CHANGELOG.md not found$(RESET)\n'; \
		exit 1; \
	fi

.PHONY: tag
tag: ## Create and push a git tag (usage: make tag VERSION=v1.0.0)
	@if [ -z "$(VERSION)" ]; then \
		printf '$(RED)Usage: make tag VERSION=v1.0.0$(RESET)\n' >&2; \
		exit 2; \
	fi
	@printf '$(BLUE)==> Creating tag $(VERSION)...$(RESET)\n'
	@git tag -a "$(VERSION)" -m "Release $(VERSION)"
	@printf '$(GREEN)Tag created. Push with: git push origin $(VERSION)$(RESET)\n'

# =============================================================================
# PRE-COMMIT
# =============================================================================
.PHONY: pre-commit
pre-commit: ## Install and run pre-commit hooks
	@printf '$(BLUE)==> Running pre-commit hooks...$(RESET)\n'
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit run --all-files; \
	else \
		printf '$(YELLOW)pre-commit not installed, running manual checks$(RESET)\n'; \
		$(MAKE) format lint typecheck shellcheck yamlcheck validate-syntax; \
	fi

.PHONY: hooks
hooks: pre-commit ## Alias for pre-commit

# =============================================================================
# DEPENDENCIES
# =============================================================================
.PHONY: deps
deps: ## Install/update Python development dependencies
	@printf '$(BLUE)==> Installing development dependencies...$(RESET)\n'
	@$(PYTHON) -m pip install --upgrade pip
	@$(PYTHON) -m pip install black ruff mypy pytest pytest-cov shellcheck pygments codespell
	@printf '$(GREEN)Dependencies installed$(RESET)\n'

.PHONY: deps-audit
deps-audit: ## Audit Python dependencies for vulnerabilities (requires pip-audit)
	@printf '$(BLUE)==> Auditing dependencies...$(RESET)\n'
	@if $(PYTHON) -c "import pip_audit" 2>/dev/null; then \
		$(PYTHON) -m pip_audit; \
	else \
		printf '$(YELLOW)pip-audit not installed, run: pip install pip-audit$(RESET)\n'; \
	fi

# =============================================================================
# UTILITIES
# =============================================================================
.PHONY: clean
clean: ## Clean build artifacts and caches
	@printf '$(BLUE)==> Cleaning build artifacts...$(RESET)\n'
	@find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name '*.pyc' -delete 2>/dev/null || true
	@find . -type f -name '.coverage' -delete 2>/dev/null || true
	@find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name '.mypy_cache' -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name '.ruff_cache' -exec rm -rf {} + 2>/dev/null || true
	@rm -rf /tmp/ztemplate-db /tmp/ztemplate-results.sarif 2>/dev/null || true
	@printf '$(GREEN)Clean complete$(RESET)\n'

.PHONY: doctor
doctor: ## Check development environment
	@printf '$(BOLD)Development Environment Check$(RESET)\n'
	@printf 'Python: ' && $(PYTHON) --version
	@printf 'Git: ' && git --version
	@printf 'Docker: ' && docker --version 2>/dev/null || printf 'not installed\n'
	@printf 'gh CLI: ' && gh --version 2>/dev/null | head -1 || printf 'not installed\n'
	@printf 'black: ' && $(BLACK) --version 2>/dev/null || printf 'not installed\n'
	@printf 'ruff: ' && $(RUFF) --version 2>/dev/null || printf 'not installed\n'
	@printf 'mypy: ' && $(MYPY) --version 2>/dev/null || printf 'not installed\n'
	@printf 'shellcheck: ' && $(SHELLCHECK) --version 2>/dev/null | head -1 || printf 'not installed\n'
	@printf 'hadolint: ' && $(HADOLINT) --version 2>/dev/null || printf 'not installed\n'
	@printf 'pre-commit: ' && pre-commit --version 2>/dev/null || printf 'not installed\n'
	@printf 'codespell: ' && codespell --version 2>/dev/null || printf 'not installed\n'

.PHONY: list-targets
list-targets: ## List all Makefile targets
	@awk '/^.PHONY:/ {for(i=2;i<=NF;i++) print $$i}' $(MAKEFILE_LIST) | sort -u

# =============================================================================
# SERVICE MANAGEMENT
# =============================================================================
.PHONY: autoloop
autoloop: ## Run zjavis-run.service via systemctl --user (usage: make autoloop FLAG=start|stop|restart|status|enable|disable|is-active|is-enabled)
	@if [ -z "$(FLAG)" ]; then \
		printf '$(RED)Usage: make autoloop FLAG=<systemctl flag> [FLAG_ARGS=...]$(RESET)\n' >&2; \
		printf '  Example: make autoloop FLAG=start\n' >&2; \
		printf '  Example: make autoloop FLAG=status\n' >&2; \
		exit 2; \
	fi
	@printf '$(BLUE)==> Running: systemctl --user %s zjavis-run.service$(RESET)\n' "$(FLAG)"
	@systemctl --user "$(FLAG)" zjavis-run.service $(FLAG_ARGS)

.PHONY: autoloop-start
autoloop-start: ## Start zjavis-run.service (user systemd)
	@$(MAKE) autoloop FLAG=start

.PHONY: autoloop-stop
autoloop-stop: ## Stop zjavis-run.service (user systemd)
	@$(MAKE) autoloop FLAG=stop

.PHONY: autoloop-restart
autoloop-restart: ## Restart zjavis-run.service (user systemd)
	@$(MAKE) autoloop FLAG=restart

.PHONY: autoloop-status
autoloop-status: ## Show zjavis-run.service status (user systemd)
	@$(MAKE) autoloop FLAG=status

.PHONY: autoloop-enable
autoloop-enable: ## Enable zjavis-run.service on login (user systemd)
	@$(MAKE) autoloop FLAG=enable

.PHONY: autoloop-disable
autoloop-disable: ## Disable zjavis-run.service on login (user systemd)
	@$(MAKE) autoloop FLAG=disable

.PHONY: autoloop-is-active
autoloop-is-active: ## Check if zjavis-run.service is active
	@$(MAKE) autoloop FLAG=is-active

.PHONY: autoloop-is-enabled
autoloop-is-enabled: ## Check if zjavis-run.service is enabled
	@$(MAKE) autoloop FLAG=is-enabled

.PHONY: autoloop-live
autoloop-live: ## Stream live logs of zjavis-run.service (user systemd journal)
	@printf '$(BLUE)==> Streaming live logs for zjavis-run.service (Ctrl-C to stop)...$(RESET)\n'
	@journalctl --user -u zjavis-run.service -f

# =============================================================================
# META
# =============================================================================
.PHONY: makefile-test
makefile-test: ## Test that Makefile parses correctly
	@$(MAKE) -n help >/dev/null && printf '$(GREEN)Makefile syntax OK$(RESET)\n'