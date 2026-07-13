.PHONY: manifest build test-fast test release clean

manifest:
	python dev/update_manifest.py

build: manifest
	python build.py

test-fast: build
	python dev/run_all_checks.py --skip-build

test: build
	python dev/run_all_checks.py --skip-build --include-browser

release:
	python dev/release_pipeline.py --output-dir release

clean:
	rm -rf dist reports release
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
