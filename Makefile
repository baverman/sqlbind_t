.PHONY: fmt lint all build

fmt:
	ruff check --select I --fix
	ruff format

lint:
	ruff check
	mypy

all: fmt lint

build:
	python -m build -nw .

%.whl:
	TWINE_PASSWORD="$$(pass dev/pypy-tokens/all)" twine upload -u __token__ $@
