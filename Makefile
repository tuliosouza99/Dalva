.PHONY: docs-serve docs-build docs-deploy help

help:
	@echo "TrackAI Documentation Commands"
	@echo "==============================="
	@echo "make docs-serve    - Serve documentation locally with live reload"
	@echo "make docs-build    - Build static documentation site"
	@echo "make docs-deploy   - Deploy documentation to GitHub Pages"

docs-serve:
	uv run mkdocs serve

docs-build:
	uv run mkdocs build

docs-deploy:
	uv run mkdocs gh-deploy
