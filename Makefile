# SpoofVane — reproducible build/demo/verify targets (review §V9-5).
.PHONY: bootstrap test depth demo verify sbom console-check clean

bootstrap:
	pip install -r requirements.txt --break-system-packages

test:
	SPOOFVANE_BD_MODE=replay python -m pytest --ignore=tests/e2e -q

depth:
	SPOOFVANE_BD_MODE=replay python -m pytest tests/depth -q

demo:
	SPOOFVANE_BD_MODE=replay python -m src.discovery.run_once --help

sbom:
	@echo "SBOM at supply-chain/sbom.cyclonedx.json"
	@python -c "import json;d=json.load(open('supply-chain/sbom.cyclonedx.json'));print(len(d['components']),'components')"

console-check:
	cd console && npm install --silent && npx tsc -p tsconfig.json

# verify = the reviewer's one-command gate (review §V9-5). Runs credential-free.
verify: test depth sbom
	@echo "SpoofVane verify complete — replay-mode, credential-free."
	@echo "BLOCKED-ENV (need live env): BD 24h-green, SLSA-L3 signing, Playwright pixel-diff."

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache console/node_modules
