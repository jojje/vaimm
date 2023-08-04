
test:
	pytest

lint:
	flake8 --max-line-length 120 --ignore E226,E227,E231,E252

dist: clean
	pip wheel --no-deps --no-index --no-build-isolation --wheel-dir dist .

clean:
	rm -rf build dist *.egg-info *.pstats *.pdf .pytest_cache
