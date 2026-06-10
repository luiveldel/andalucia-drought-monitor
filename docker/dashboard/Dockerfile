FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl --retry 5 --retry-delay 3 -fsSL "https://github.com/oven-sh/bun/releases/download/bun-v1.3.13/bun-linux-x64.zip" -o bun.zip \
    && unzip bun.zip \
    && mv bun-linux-x64/bun /usr/local/bin/bun \
    && chmod +x /usr/local/bin/bun \
    && rm -rf bun.zip bun-linux-x64

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 3000
EXPOSE 8000

CMD ["/bin/sh", "-c", "if [ ! -f rxconfig.py ]; then echo '0' | reflex init; fi && reflex run --env dev --backend-host 0.0.0.0"]