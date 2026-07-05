.PHONY: publish preview discoverability

# Regenerate the auto blocks in robots.txt and llms.txt from projects.yml,
# so adding a card is the only manual step when a new project is published.
discoverability:
	python3 scripts/gen_discoverability.py

publish: discoverability
	quarto publish gh-pages

preview:
	quarto preview index.qmd
