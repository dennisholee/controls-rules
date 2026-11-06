PYTHON ?= python3

.PHONY: validate fixture-list

validate:
	$(PYTHON) tools/validate.py

fixture-list:
	@ls tests/fixtures | sed 's/\.json$$//'
