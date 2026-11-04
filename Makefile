.PHONY: ci ci-local
ci:
	bash scripts/ci/run.sh
ci-local:
	bash scripts/ci/local-ci.sh
