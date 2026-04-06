FROM python:3.12-slim

WORKDIR /claude-code-proxy

# Copy dependency files first (better Docker caching)
COPY pyproject.toml uv.lock ./

RUN pip install --upgrade pip uv \
 && uv sync 

COPY . .

EXPOSE 8232
CMD ["uv", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8232"]
