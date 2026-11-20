SHELL := /bin/sh

REPO ?= cvsz/ztemplate
PERMISSION ?= pull

.PHONY: help validate-template setup install collaborators protect format lint typecheck build security ci check all

help:
	@printf '%s\n' 'Targets:' \
		'  make install           - Initialize a new repository from this template (preview + validate)' \
		'  make collaborators   - Add GitHub collaborators to a repository (preview; APPLY=1 to apply)' \
		'  make protect         - Apply GitHub branch/secret protection (preview; APPLY=1 to apply)' \
		'  make validate-template - Run repository structure and link validation' \
		'  make setup           - Run new-repository setup (bootstrap preview + validate + protect preview)' \
		'  make format          - Run Python formatter and linter checks' \
		'  make lint            - Run ruff lint on Python and shell scripts' \
		'  make typecheck       - Run mypy static type checking on Python scripts' \
		'  make test            - Run python unit tests' \
		'  make build             - Run compilation check on scripts' \
		'  make security          - Run security and validation checks' \
		'  make ci                - Run full CI validation suite' \
		'  make check             - Dry-run all validations (no mutations)' \
		'  make all               - Run every validation, lint, typecheck, test, build, and security check'

validate-template:
	python3 scripts/validate_repo.py
	python3 -m unittest discover -s tests -v

setup: ## New-repository setup: bootstrap identity preview, validate template, and preview protection
	@echo "==> Step 1: Previewing project identity bootstrap..."
	python3 scripts/bootstrap.py --name "$(NAME)" --owner "$(OWNER)" --codeowner "$(CODEOWNER)" --description '$(DESCRIPTION)'
	@echo "==> Step 2: Validating inherited baseline..."
	make validate-template
	@echo "==> Step 3: Previewing repository protection..."
	make protect

install: ## Initialize project identity for new repo use (dry-run preview + validate)
	@echo "==> Previewing project identity bootstrap..."
	python3 scripts/bootstrap.py --name "$(NAME)" --owner "$(OWNER)" --codeowner "$(CODEOWNER)" --description '$(DESCRIPTION)'
	@echo "==> To apply the identity changes, re-run bootstrap with --apply."
	@echo "==> Validating inherited baseline..."
	make validate-template

collaborators: ## Add GitHub collaborators to a repository (preview; APPLY=1 to apply)
	@if [ -z "$(COLLABORATORS)" ]; then echo 'Usage: make collaborators COLLABORATORS=user1,user2,user3 [REPO=owner/repo] [PERMISSION=pull] [APPLY=1]' >&2; exit 2; fi
	python3 scripts/github_admin.py --repo "$(REPO)" --collaborators "$(COLLABORATORS)" --collaborator-permission "$(PERMISSION)" $(if $(APPLY),--apply,)

protect: ## Apply GitHub branch/secret protection (preview; APPLY=1 to apply)
	python3 scripts/github_admin.py --repo "$(REPO)" $(if $(APPLY),--apply --verify,)

format: ## Run Python formatter check on all Python files
	python3 -m black --check scripts/*.py tests/*.py

lint: ## Run ruff lint on Python files and shellcheck on shell scripts
	python3 -m ruff check scripts/*.py tests/*.py
	shellcheck -s bash scripts/*.sh .github/scripts/*.sh

typecheck: ## Run mypy static type checking on Python scripts
	python3 -m mypy scripts/*.py

test: ## Run python unit tests
	python3 -m unittest discover -s tests -v

build: ## Run compilation check on all Python scripts
	python3 -m py_compile scripts/*.py tests/*.py

security: ## Run security and validation checks
	python3 scripts/validate_repo.py
	@echo "==> Checking for tracked secret-bearing files..."
	@if git ls-files | grep -E '(^|/)(\.env$$|id_rsa|id_ed25519|.*\.pem|.*\.key)$$' | grep -v '^\.env\.example$$'; then \
		echo "ERROR: Potential secret-bearing file is tracked." >&2; \
		exit 1; \
	fi
	@echo "No tracked secret-bearing files found."

ci: ## Run full CI validation suite (validate-template lint typecheck test build security)
	$(MAKE) validate-template lint typecheck test build security

check: ## Dry-run all validations (no mutations)
	$(MAKE) validate-template lint typecheck test build security

all: ## Run every validation, lint, typecheck, test, build, and security check
	$(MAKE) ci
