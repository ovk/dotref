
lint:
	flake8 --statistics dotref.py tests/

test:
	coverage run -m unittest discover tests

