VENV := .venv
PY   := $(VENV)/bin/python

.PHONY: venv install data test app demo lint clean

venv:
	python3 -m venv $(VENV)

install: venv
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet -r requirements.txt

data:
	$(PY) -m src.generate_data

test:
	$(PY) -m pytest -q

app:
	$(VENV)/bin/streamlit run app.py

demo: install data test app

clean:
	rm -rf $(VENV) __pycache__ src/__pycache__ tests/__pycache__ .pytest_cache data/*.csv exports
