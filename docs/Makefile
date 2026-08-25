MDBOOK := $(shell command -v mdbook 2>/dev/null)
ifeq ($(strip $(MDBOOK)),)
MDBOOK := nix shell nixpkgs\#mdbook --command mdbook
endif

.PHONY: book deploy

book:
	@echo "====> building documentation"
	$(MDBOOK) build .

deploy: book
	@set -eu; \
		echo "====> deploying documentation to github"; \
		git worktree prune; \
		rm -rf /tmp/book; \
		git worktree add -f /tmp/book gh-pages; \
		find /tmp/book -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf -- {} +; \
		cp -a book/. /tmp/book/; \
		cd /tmp/book; \
		git add -A; \
		if git diff --cached --quiet; then \
			echo "====> documentation is already up to date"; \
		else \
			git commit -m "deploy documentation on $$(date) by $${USER:-unknown}"; \
			git push origin gh-pages; \
		fi
