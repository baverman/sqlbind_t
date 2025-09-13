.PHONY: fmt lint all

fmt:
	ruff check --select I --fix
	ruff format

lint:
	ruff check
	mypy

all: fmt lint
