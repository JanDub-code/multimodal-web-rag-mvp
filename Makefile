.PHONY: up down restart build seed logs clean nuke

## Normální spuštění (migrace + seed + start)
up:
	@./scripts/dev-up.sh

## Spuštění s rebuild obrazů
build:
	@./scripts/dev-up.sh --build --force

## Zastavení všeho
down:
	docker compose down

## Restart (bez rebuild)
restart:
	docker rm -f local-mvp-postgres local-mvp-qdrant local-mvp-api local-mvp-frontend 2>/dev/null || true
	docker compose up -d

## Jen migrace + seed (když běží postgres)
seed:
	docker compose --profile tools run --rm migrate
	docker compose --profile tools run --rm migrate python -m scripts.init_db

## Logy jednotlivých služeb
logs:
	docker compose logs -f --tail=50

logs-api:
	docker compose logs -f --tail=100 api

logs-db:
	docker compose logs -f --tail=50 postgres

## Smaže kontejnery a volumes (DATA SE ZTRATÍ!)
clean:
	docker compose down --volumes --remove-orphans

## Kompletní reset včetně Docker cache (DESTRUKTIVNÍ)
nuke:
	docker compose down --volumes --remove-orphans
	docker system prune -f
