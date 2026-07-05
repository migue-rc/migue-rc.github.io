.PHONY: publish preview discoverability indexnow

# Regenerate the auto blocks in robots.txt and llms.txt from projects.yml,
# so adding a card is the only manual step when a new project is published.
discoverability:
	python3 scripts/gen_discoverability.py

# Ping IndexNow (Bing/Naver/Seznam/Yandex + shared engines) with every URL
# changed in the last day, across the hub and all project sitemaps.
indexnow:
	python3 scripts/submit_indexnow.py

publish: discoverability
	@echo "==> Publishing site to gh-pages"
	quarto publish gh-pages
	@echo "==> Notifying search engines via IndexNow"
	python3 scripts/submit_indexnow.py

preview:
	quarto preview index.qmd
