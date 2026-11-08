PYTHON ?= python3
ENV ?= dev
SERVICE ?= accounts

.PHONY: validate fixture-list render conformance

validate:
	$(PYTHON) tools/validate.py

fixture-list:
	@ls tests/fixtures | sed 's/\.json$$//'

render:
	@test -d registry || { echo "render requires a service-generated registry/ fragment; use the central pipeline" >&2; exit 1; }
	bundle -src . -env $(ENV) -service $(SERVICE) -out dist/$(SERVICE)

conformance:
	conformance -bundle dist/$(SERVICE) -fixtures tests/fixtures -service $(SERVICE) -v
