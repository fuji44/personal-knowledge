FROM ghcr.io/basicmachines-co/basic-memory:1.0.0@sha256:cad49f5433bcd8592fea547907a2b967435b3fa60d0f81ebc4d558e2b5cb55a8

LABEL org.opencontainers.image.title="personal-knowledge" \
      org.opencontainers.image.description="Basic Memory MCP server bundled with personal-knowledge backup, verify, and restore scripts" \
      org.opencontainers.image.source="https://github.com/fuji44/personal-knowledge" \
      org.opencontainers.image.licenses="AGPL-3.0-only"

COPY --chmod=0755 scripts/backup.sh scripts/restore.sh scripts/verify-backup.sh /usr/local/bin/

ENV HOME=/data \
    BASIC_MEMORY_HOME=/data

EXPOSE 8000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python3", "-c", "import socket; socket.create_connection(('127.0.0.1', 8000), 3).close()"]

CMD ["basic-memory", "mcp", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
