FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gelbooru_mcp.py .

ENV GELBOORU_API_KEY=""
ENV GELBOORU_USER_ID=""
ENV GELBOORU_CACHE_DIR="/tmp/.gelbooru_cache"
ENV GELBOORU_CACHE_TTL="86400"

CMD ["python", "gelbooru_mcp.py"]
