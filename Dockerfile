FROM vastai/base-image:cuda-13.0.2-cudnn-devel-ubuntu24.04-py313

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN . /venv/main/bin/activate && \
    uv sync --frozen --no-dev

COPY . .

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-u", "/app/main.py"]