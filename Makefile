lint:
	flake8 --statistics dotref/ tests/

test:
	coverage run -m unittest discover tests

