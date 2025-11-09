# .firsttry/Dockerfile
ARG PYVER=3.11
FROM python:${PYVER}-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GITHUB_ACTIONS=true

RUN apt-get update && apt-get install -y --no-install-recommends \
            git git-lfs curl ca-certificates \
            build-essential gcc pkg-config \
            libffi-dev libssl-dev \
            zlib1g-dev libbz2-dev liblzma-dev \
            libsqlite3-dev \
            # uncomment if your repo needs rust-backed wheels (e.g., some crypt/compression libs)
            # cargo \
        && rm -rf /var/lib/apt/lists/*

# speed up pip a bit
RUN python -m pip install --upgrade pip wheel

WORKDIR /work
