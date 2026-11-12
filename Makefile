.PHONY: setup doctor run demo test evaluate check container container-stop terraform-check
setup:
	uv sync --frozen --extra aws
	npm ci
doctor:
	uv run runbookops preflight
run:
	uv run runbookops --mode offline serve --demo-auth --port 8002
demo:
	uv run runbookops demo
test:
	uv run --extra aws pytest --cov=runbookops --cov-branch --cov-report=term-missing --cov-report=json:artifacts/coverage/python.json -q
	npm run test:coverage
evaluate:
	uv run runbookops evaluate
check:
	uv run ruff check src examples scripts tests deploy
	uv run ruff format --check src
	uv run python scripts/verify_docs.py
	$(MAKE) test evaluate
container:
	docker compose up --build -d --wait
container-stop:
	docker compose down
terraform-check:
	terraform fmt -check -recursive infra/terraform
	terraform -chdir=infra/terraform/presenter init -backend=false -input=false
	terraform -chdir=infra/terraform/presenter validate
	terraform -chdir=infra/terraform/presenter test
	terraform -chdir=infra/terraform/bootstrap init -backend=false -input=false
	terraform -chdir=infra/terraform/bootstrap validate
	terraform -chdir=infra/terraform/logs init -backend=false -input=false
	terraform -chdir=infra/terraform/logs validate
