.PHONY: install test test-cov lint audit dev-backend dev-frontend load-entities

install:
	pip install -r requirements.txt
	cd frontend && npm install --legacy-peer-deps

test:
	python -m pytest backend/tests/ -v

test-cov:
	python -m pytest backend/tests/ --cov=backend --cov-report=term-missing --cov-report=html -v

lint:
	python -m flake8 backend/ --max-line-length=120 --ignore=E501,W503

audit:
	pip-audit --require-hashes -r requirements.txt || pip-audit -r requirements.txt

dev-backend:
	python -m uvicorn backend.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

load-entities:
	python -c "from backend.ingestors.entity_loader import load_all_entities; r=load_all_entities(); print(r)"

profile:
	python -m backend.services.query_profiler
