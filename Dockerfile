FROM vastai/pytorch:@vastai-automatic-tag

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        ffmpeg && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV PATH="/app/.venv/bin:$PATH"

CMD ["sleep", "infinity"]