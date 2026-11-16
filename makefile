MAIN = main.py
MAP ?= maps/easy/01_linear_path.txt

install:
	pip install -r requirements.txt

run:
	python3 $(MAIN) $(MAP)

debug:
	python3 -m pdb $(MAIN) $(MAP)

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .mypy_cache
	rm -rf dist

lint:
	flake8 .
	mypy --exclude '^github/' --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs .

lint-strict:
	flake8 .
	mypy --exclude '^github/' --strict --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs .

.PHONY: install run debug clean lint lint-strict