# Home hub in a container. Build from the repository root (the hub reads the
# catalog markdown and the music-studio scripts from it):
#   docker build -f app/Dockerfile -t home-hub .
# Not built in the sandbox where it was written — check on the server.
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 hub \
 && mkdir /work && chown hub:hub /work
COPY --chown=hub:hub . /repo
USER hub
WORKDIR /repo/app

ENV HUB_BIND=0.0.0.0 \
    HUB_PORT=8787 \
    HUB_WORKDIR=/work \
    PYTHONUNBUFFERED=1
EXPOSE 8787
HEALTHCHECK --interval=60s --timeout=5s \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/healthz', timeout=4)"
CMD ["python3", "-m", "hub"]
