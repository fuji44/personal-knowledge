# Security Policy

## Reporting a Vulnerability

Please **do not** report security vulnerabilities through public GitHub issues.

Instead, report them privately using **GitHub Private Vulnerability Reporting** under this repository's **Security** tab (`Advisories` → `Report a vulnerability`).

## Operational Security Guidelines

- **Never commit secrets or private notes**: Keep API tokens, OAuth credentials, `.env` files, and personal/client knowledge bases out of this repository.
- **Bind localhost by default**: The default `docker-compose.yml` binds port `48000` to `127.0.0.1` (`127.0.0.1:${HOST_PORT:-48000}:8000`). If you expose `basic-memory` beyond `localhost`, place it behind an authenticating reverse proxy or Zero Trust Access layer (e.g., Cloudflare Access with OAuth 2.1) rather than exposing an unauthenticated HTTP endpoint directly.
- **Scope isolation**: Follow [AGENTS.md](AGENTS.md) and [plugins/personal-knowledge/rules/AGENTS.md](plugins/personal-knowledge/rules/AGENTS.md) to keep work engagement data isolated from general-purpose or personal projects.
