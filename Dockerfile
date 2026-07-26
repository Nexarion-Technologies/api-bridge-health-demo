FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --gid 10001 bridge && useradd --uid 10001 --gid bridge --create-home bridge
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir .
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=2s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=1)"
CMD ["uvicorn", "api_bridge.main:app", "--host", "0.0.0.0", "--port", "8080"]
