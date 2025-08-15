FROM python:3.12

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg2 \
    apt-transport-https \
    ca-certificates \
    libnss3 \
    libgdk-pixbuf-2.0-0 \
    libgbm1 \
    libasound2 \
    fonts-liberation \
    xdg-utils \
    wget \
    curl \
    redis-tools && \
    rm -rf /var/lib/apt/lists/*


# Add PostgreSQL repository
RUN echo "deb http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    wget -qO - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    apt-get update && \
    apt-get install -y postgresql-client-17 && \
    rm -rf /var/lib/apt/lists/*

# Install uv package manager
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

WORKDIR /app
COPY . ./

ENV PATH="/app/.venv/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT="/.venv"
ENV UV_LINK_MODE=copy

RUN uv venv
RUN uv sync
RUN chmod +x /app/entrypoint.sh