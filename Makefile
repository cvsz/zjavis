SHELL := /bin/sh

REPO ?= cvsz/ztemplate
PERMISSION ?= pull

.PHONY: help validate-template setup install collaborators protect format lint test build security ci

help:
	@printf '%s\n' 'Targets:' \
		'  make install           - Initialize a new repository from this template (preview + validate)' \
		'  make collaborators   - Add GitHub collaborators to a repository (preview; APPLY=1 to apply)' \
		'  make protect         - Apply GitHub branch/secret protection (preview; APPLY=1 to apply)' \
		'  make validate-template - Run repository structure and link validation' \
		'  make test              - Run python unit tests' \
		'  make lint              - Run python syntax and structure checks' \
		'  make build             - Run compilation check on scripts' \
		'  make security          - Run security and validation checks' \
		'  make ci                - Run full CI validation suite'

validate-template:
	python3 scripts/validate_repo.py
	python3 -m unittest discover -s tests -v

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

format:
	python3 -m py_compile scripts/*.py tests/*.py

lint:
	python3 -m py_compile scripts/*.py tests/*.py
	python3 scripts/validate_repo.py

test:
	python3 -m unittest discover -s tests -v

build:
	python3 -m py_compile scripts/*.py

security:
	python3 scripts/validate_repo.py

ci: validate-template lint test build security
