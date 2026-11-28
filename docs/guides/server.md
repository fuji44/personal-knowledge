# Running the Basic Memory Server

`personal-knowledge` connects to a Basic Memory MCP server over Streamable HTTP (default: `http://localhost:48000/mcp`). Choose the runtime method that best fits your environment.

| Method | Best For | Container Required |
| --- | --- | --- |
| **`uvx`** | Fastest way to try without installing anything | No |
| **`uv tool`** | Daily local use or OS background service without Docker | No |
| **`docker compose`** | Recommended persistent local or home-server runtime | Yes |
| **`docker run`** | Standalone container without cloning this repository | Yes |

## 1. `uv` (No Container)

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/).

### Temporary Run (`uvx`)

Run Basic Memory immediately without permanent installation:

```bash
uvx --prerelease=allow basic-memory mcp --transport streamable-http --host 127.0.0.1 --port 48000
```

### Persistent Tool Install (`uv tool`)

Install `basic-memory` once for daily use:

```bash
uv tool install --prerelease=allow basic-memory
basic-memory mcp --transport streamable-http --host 127.0.0.1 --port 48000
```

- **Data directory**: By default, Basic Memory stores files under your home directory (`~/basic-memory` and `~/.basic-memory`). Set `BASIC_MEMORY_HOME=/path/to/data` before starting the server to use a custom directory.
- **Background service**: For an always-on host, run the `basic-memory mcp ...` command under `systemd --user` (Linux) or `launchd` (macOS).

## 2. `docker compose` (Recommended for Containers)

From the root of this repository:

```bash
docker compose up -d
```

- Binds `127.0.0.1:48000` to container port `8000` (override with `HOST_PORT=<PORT> docker compose up -d`).
- Persists Markdown notes and configuration in the `basic-memory-data` Docker volume.
- To use the prebuilt GHCR image instead of building locally, edit [docker-compose.yml](../../docker-compose.yml) to comment out `build: .` and uncomment `image: ghcr.io/fuji44/personal-knowledge:latest`.

## 3. `docker run` (Standalone Container)

Run the prebuilt image directly without cloning this repository or using Compose:

```bash
docker run -d \
  --name basic-memory \
  --restart unless-stopped \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  -p 127.0.0.1:48000:8000 \
  -v basic-memory-data:/data \
  ghcr.io/fuji44/personal-knowledge:latest
```

## Security Note

Always keep Basic Memory bound to `127.0.0.1`. If you need remote or multi-device access, place an authenticating layer in front of it rather than binding to `0.0.0.0` (see [Local Host + Cloudflare](./cloudflare-remote.md) and [SECURITY.md](../../SECURITY.md)).
