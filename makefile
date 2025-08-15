.PHONY: migrate


migrate:
	docker compose exec tinyshop_web uv run python manage.py migrate