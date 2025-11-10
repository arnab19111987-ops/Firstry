ARG PYVER=3.11
FROM python:${PYVER}-slim

# (optional) set build args to match your local UID:GID for volume mounts
ARG UID=1000
ARG GID=1000

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GITHUB_ACTIONS=true

# deps you actually need; keep minimal
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates curl build-essential \
 && rm -rf /var/lib/apt/lists/*

# create non-root user and writable cache dir
RUN groupadd -g ${GID} app && useradd -m -u ${UID} -g ${GID} app
RUN mkdir -p /cache/pip /work && chown -R app:app /cache /work

# pip config
ENV PIP_CACHE_DIR=/cache/pip \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_INPUT=1 \
    PIP_DEFAULT_TIMEOUT=60

RUN python -m pip install --upgrade pip wheel
WORKDIR /work
USER app
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
