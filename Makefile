
.PHONY: build up down test lint

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

test:
	docker compose exec dicom-gw pytest

lint:
	docker compose exec dicom-gw flake8
