install:
	pip install -r requirements.txt

dev:
	uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
