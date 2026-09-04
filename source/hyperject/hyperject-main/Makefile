# hyperject — dev / install / demo tasks
#
#   make install   pipx-install the CLI
#   make dev       editable install (source edits take effect immediately)
#   make test      run the test suite
#   make loop      run the full mock -> run -> detect review loop in ./.demo
#   make lint      byte-compile all sources
#   make clean     remove build artifacts and the demo dir

PKG     := hyperject
PORT    ?= 8080
WORKDIR ?= .demo

.PHONY: install dev uninstall test lint loop clean

install:
	pipx install . --force --pip-args=--no-cache-dir

dev:
	pipx install -e . --force --pip-args=--no-cache-dir

uninstall:
	-pipx uninstall $(PKG)

test:
	pytest -q

lint:
	python3 -m py_compile src/$(PKG)/*.py src/$(PKG)/modules/*.py

# End-to-end review loop: start the safe mock endpoint, send telemetry while
# recording responses, then review what the endpoint accepted.
loop:
	@mkdir -p $(WORKDIR)
	@cd $(WORKDIR) && hyperject init --force >/dev/null
	@cd $(WORKDIR) && ( hyperject mock --port $(PORT) --log ingest.log.jsonl >/dev/null 2>&1 & echo $$! > mock.pid )
	@sleep 1
	@cd $(WORKDIR) && hyperject run --target-base http://127.0.0.1:$(PORT) --delay 0 \
		--save-responses responses.json || true
	@cd $(WORKDIR) && hyperject detect ingest.log.jsonl || true
	@cd $(WORKDIR) && kill `cat mock.pid` 2>/dev/null; rm -f mock.pid
	@echo "review artifacts in $(WORKDIR)/: results.json  responses.json  ingest.log.jsonl"

clean:
	rm -rf build src/*.egg-info $(WORKDIR) .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
