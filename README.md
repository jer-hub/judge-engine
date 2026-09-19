# Judge Engine

School competitive programming platform: students write **Java** in the browser, submit against hidden tests, and get automated verdicts. Teachers manage content via an admin UI and Django Admin — **admin-created accounts only** (no public registration).

## Features

- Java 17 judge in an isolated Docker sandbox (compile + run per test)
- Problems with rich-text statements, samples, and hidden test cases
- Contests with registration, countdown, freeze, and ICPC-style scoreboard
- Submissions via Monaco editor with live verdict polling
- Admin roster tools (CSV import, contest participant picker)
- JWT cookie auth with admin / student roles

## Stack

```
Next.js 14  →  Django REST (JWT)  →  Redis / Celery  →  Docker Temurin 17 sandbox
                      ↕
                 PostgreSQL
```

## Quick start

### Prerequisites

- Docker Desktop (Engine + Compose)
- Git
- ~2 GB free disk for images and data

### Setup

**Windows (PowerShell)**

```powershell
git clone https://github.com/jer-hub/judge-engine.git
cd judge-engine
copy .env.example .env
# Edit .env — set JUDGE_HOST_DATA_DIR to an absolute path, e.g.
# JUDGE_HOST_DATA_DIR=C:/path/to/judge-engine/judge_data
mkdir judge_data -Force
docker compose up --build -d
docker pull eclipse-temurin:17-jdk-jammy
docker compose exec backend python manage.py seed_demo
```

**macOS / Linux**

```bash
git clone https://github.com/jer-hub/judge-engine.git
cd judge-engine
cp .env.example .env
# Edit .env — set JUDGE_HOST_DATA_DIR to an absolute path, e.g.
# JUDGE_HOST_DATA_DIR=/home/you/judge-engine/judge_data
mkdir -p judge_data
docker compose up --build -d
docker pull eclipse-temurin:17-jdk-jammy
docker compose exec backend python manage.py seed_demo
```

### URLs & demo accounts

| | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Django Admin | http://localhost:8000/admin/ |

| Role | Username | Password |
|------|----------|----------|
| Teacher | `admin` | `JudgeDev-Admin-ChangeMe!` (from `.env`) |
| Students | `alice` / `bob` / `carol` | `demo123` |

Change the admin password after first login. Full classroom walkthrough: [DEMO.md](DEMO.md).

### Smoke test

As `alice`, open **Problems → A Plus B** and submit:

```java
import java.util.*;
public class Solution {
  public static void main(String[] args) {
    Scanner sc = new Scanner(System.in);
    System.out.println(sc.nextInt() + sc.nextInt());
  }
}
```

You should see **Accepted** within a few seconds.

## Configuration

Copy `.env.example` → `.env`. Important variables:

| Variable | Notes |
|----------|--------|
| `DJANGO_SECRET_KEY` | ≥50 random chars when `DJANGO_DEBUG=False` |
| `JUDGE_HOST_DATA_DIR` | Absolute host path (required for reliable sibling containers on Windows) |
| `BOOTSTRAP_ADMIN_PASSWORD` | Initial admin password (compose bootstrap) |
| `JWT_COOKIE_SECURE` | `true` behind HTTPS in production |
| `NEXT_PUBLIC_API_URL` | Browser-facing API origin (default `http://localhost:8000`) |

## Backend tests

```powershell
docker compose exec backend python manage.py test
```

## Production

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Set strong secrets, `DJANGO_DEBUG=False`, and `JWT_COOKIE_SECURE=true` behind HTTPS (Caddy is included in the prod compose overlay). See [SECURITY.md](SECURITY.md).

## Docs

| Doc | Purpose |
|-----|---------|
| [DEMO.md](DEMO.md) | 10-minute classroom demo |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/PUBLISH.md](docs/PUBLISH.md) | GitHub publish checklist |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Dev setup & PRs |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting |
| [LICENSE](LICENSE) | MIT |

## License

MIT — see [LICENSE](LICENSE).
