.PHONY: install test lint demo serve

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

lint:
	python -m ruff check .

demo:
	python -m joni --ticks 8 --ledger "what's your take on privacy these days?"

serve:
	JONI_RELOAD=1 python -m uvicorn joni.api:app --reload --port 8000
