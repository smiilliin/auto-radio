FROM python:3.13-slim

RUN apt-get update && \
    apt-get install -y ffmpeg git

RUN pip install uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

COPY . .

CMD ["python", "main.py"]