.PHONY: migrate


migrate:
	docker compose exec tinyshop-web uv run python manage.py migrate