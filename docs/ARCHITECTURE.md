# Judge Engine Architecture

## Overview

Judge Engine is a **school-based competitive programming platform** where students write Java code in a browser, receive automated verdicts on hidden test cases, and compete in live contests.

```
┌─────────────┐
│  Next.js    │  (Frontend @ :3000)
│ (Browser)   │
└──────┬──────┘
       │ HTTP + JWT cookies
       ▼
┌─────────────────────────────────────────┐
│  Django REST API (@ :8000/api)          │
│  ├─ Authentication (JWT)                │
│  ├─ Problems (CRUD)                     │
│  ├─ Submissions (POST, status polling)  │
│  ├─ Contests (register, list)           │
│  └─ Scoreboard (rank, ICPC scoring)     │
│                                         │
│  Gunicorn (3 workers) @ :8000           │
└──────┬──────────────────────────────────┘
       │
       ├──────────────┬──────────────┬─────────────┐
       ▼              ▼              ▼             ▼
    PostgreSQL    Redis         Celery Worker  Docker
    (Database)    (Cache)       (Judge Queue)  (Sandbox)
    @ :5432       @ :6379       (async)        (Java)
```

## Technology Stack

| Layer      | Technology         | Version | Purpose                          |
|------------|-------------------|---------|----------------------------------|
| Frontend   | Next.js            | 14      | React server-side rendering      |
| Frontend   | React              | 18      | UI components                    |
| Frontend   | TypeScript         | 5       | Type safety                      |
| Frontend   | Tailwind CSS       | 3       | Styling                          |
| API        | Django             | 4.2     | REST framework                   |
| API        | Django REST        | 3.14    | Serialization + views            |
| API        | PyJWT              | 2       | JWT tokens                       |
| Queue      | Celery             | 5       | Async submission processing      |
| Queue      | Redis              | 7       | Message broker + cache           |
| Database   | PostgreSQL         | 16      | Persistent data                  |
| Sandbox    | Eclipse Temurin    | 17 JDK  | Java execution + isolation       |
| Infra      | Docker             | 27+     | Containerization                 |
| Infra      | Docker Compose     | 2       | Multi-service orchestration      |

## Core Components

### Frontend (`./frontend`)

**Framework:** Next.js 14 (App Router)

**Key Pages:**
- `/` — Homepage / login redirect
- `/login` — JWT cookie-based auth
- `/problems` — Problem list + detail
- `/contests` — Contest list + registration
- `/contest/[id]` — Contest detail + submission
- `/scoreboard` — Live contest rankings (ICPC-style)
- `/admin` — Redirect to Django Admin

**Key Features:**
- Monaco Editor for Java code
- Real-time submission polling (client-side)
- JWT token refresh in background
- Responsive design (desktop + tablet)

### Backend (`./backend`)

**Framework:** Django 4.2 + Django REST Framework (DRF)

**Apps:**
- **`accounts`** — Custom `User` model with `role` field (`admin`/`student`)
- **`problems`** — Problem definitions, samples, hidden tests
- **`submissions`** — Student submissions + verdicts
- **`contests`** — Contest scheduling, registration, rules
- **`scoreboard`** — ICPC-style rankings + penalty scoring
- **`api`** — REST endpoints + JWT authentication

**Key Models:**
```
User (role: admin/student)
  ├─ Problem (title, difficulty, time_limit, memory_limit)
  │  ├─ Sample (in/out)
  │  └─ HiddenTest (in/out — not shown to students)
  ├─ Submission (code, verdict, execution_time)
  ├─ Contest (title, start_time, duration, freeze_time)
  │  └─ ContestProblem (problem, order, visible_after)
  └─ ContestRegistration (student, contest)
```

**Authentication:**
- JWT cookies (access token, refresh token)
- Configurable lifetimes (default: 60 min access, 7 day refresh)
- Token refresh via `/api/auth/refresh/` endpoint

**Admin-Only Operations:**
- Create/edit problems
- Upload hidden tests
- Create contests
- View all submissions
- Manage user roster (no public signup)

### Judge Worker (`./backend/judge/`)

**Framework:** Celery + Docker

**Flow:**
1. Student submits code → API enqueues task to Redis
2. Celery worker picks up task
3. Creates isolated Docker container (Temurin 17 JDK)
4. Compiles Java code (timeout: 10s)
5. Runs against hidden tests (timeout: 2s per test, memory: 256 MB)
6. Captures verdict: `Accepted`, `CompilationError`, `WrongAnswer`, `RuntimeError`, `TimeLimitExceeded`, `MemoryLimitExceeded`
7. Stores result in database
8. Frontend polls for verdict

**Sandboxing:**
- Each test runs in a fresh container
- No network access
- Memory + CPU caps enforced by Docker limits
- Source code size limit: 64 KB (configurable)

**Verdict Determination:**
- `Accepted` — all tests passed
- `WrongAnswer` — output mismatch
- `CompilationError` — `javac` failed
- `RuntimeError` — uncaught exception or non-zero exit
- `TimeLimitExceeded` — execution > 2s
- `MemoryLimitExceeded` — RSS > 256 MB

### Cache & Queue (`Redis`)

**Broker:** Message queue for Celery tasks  
**Backend:** Result storage for submission verdicts  
**Cache:** Scoreboard rankings (precomputed, invalidated on new submission)

**Expiry Policies:**
- Submission results: never (stored in DB)
- Scoreboard cache: 5 minutes (recalculated on contest change)

### Database (`PostgreSQL`)

**Persistence:**
- User accounts + roles
- Problem definitions + test cases (hidden tests have `is_visible=false`)
- Submissions + verdicts
- Contest metadata + registrations
- Django session/token tables

**Access Control:**
- Only the Django backend reads/writes
- Submissions table is write-only from worker (appends verdicts)
- Hidden test cases are never exposed via API

## Authentication & Authorization

### JWT Flow

```
1. POST /api/auth/login/ (username + password)
   ↓ (validated against User)
   ↓ Create JWT access (exp: 60 min) + refresh (exp: 7 days)
   ↓ Return tokens as secure cookies

2. Browser stores cookies (http-only, secure flag in HTTPS)
   ↓ Subsequent browser calls go through Next.js `/api/proxy…`

3. GET /api/problems/ (with cookie)
   ↓ DRF verifies JWT
   ↓ Sets `request.user`
   ↓ View enforces role / object permissions

4. Token expires at T+60min
   ↓ Client detects 401 → POST /api/auth/refresh/ (uses refresh cookie)
   ↓ New access token issued
   ↓ Transparent to user
```

### Role-Based Access Control

| Endpoint          | Admin | Student | Anon |
|-------------------|-------|---------|------|
| `/api/problems/`  | ✓     | ✓       | ✗    |
| `POST /api/problems/` | ✓ | ✗       | ✗    |
| `/api/submissions/` (own) | ✓ | ✓     | ✗    |
| `/api/submissions/` (all) | ✓ | ✗     | ✗    |
| `/api/contests/`  | ✓     | ✓       | ✗    |
| `POST /api/contests/` | ✓ | ✗       | ✗    |
| Django Admin `/admin/` | ✓ | ✗       | ✗    |

## Data Flow: Submission

```
User submits code
    ↓
Frontend: POST /api/submissions/ (contest_id, problem_id, source_code)
    ↓
Backend: Validate user role, contest membership, source size
    ↓
Backend: Create Submission object (status: "pending")
    ↓
Backend: Enqueue Celery task (submission_id)
    ↓
Redis: Task sits in queue
    ↓
[Celery Worker picks up task]
    ↓
Worker: Spawn Docker container with source code
    ↓
Worker: Compile Java (10s timeout)
    ↓
Worker: For each hidden test case:
  - Write test input to stdin
  - Run Java program (2s timeout, 256MB memory limit)
  - Capture stdout
  - Compare to expected output
    ↓
Worker: Determine verdict
    ↓
Worker: Update Submission.status & Submission.verdict
    ↓
[Frontend polls /api/submissions/{id}/ every 1.5 seconds]
    ↓
Frontend: Renders verdict to user
```

## Data Flow: Scoreboard

```
Contest starts
    ↓
[During contest]
    ↓
Student submits
    ↓
Verdict stored in DB
    ↓
[Frontend: GET /api/contests/{id}/scoreboard/]
    ↓
Backend: Check if contest is frozen (freeze_time)
    ↓
If frozen: exclude submissions after freeze_time
    ↓
Compute ICPC scores for each student:
  - Rank by (solved_count, total_penalty_minutes)
  - Penalty = sum of (time_of_solve + 20*failed_attempts)
    ↓
Redis cache score for 5 minutes
    ↓
Frontend: Render table
```

## Deployment

### Development

```bash
docker compose up --build -d
```

Runs all services with hot-reload (volumes mounted).

### Production

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Changes:
- Gunicorn workers increased (3 → 8+)
- `DJANGO_DEBUG=False`
- `DJANGO_SECRET_KEY` randomized
- `JWT_COOKIE_SECURE=True` (requires HTTPS)
- Static files collected (`collectstatic`)
- Celery concurrency increased (2 → 4+)
- Caddy reverse proxy (optional, for HTTPS termination)

**Secrets Management:**
- Rotate `DJANGO_SECRET_KEY` before public deployment
- Use strong `BOOTSTRAP_ADMIN_PASSWORD`
- Store `POSTGRES_PASSWORD` in a secret manager (not `.env`)
- Use HTTPS + secure cookies

## Performance Characteristics

| Operation         | Typical Latency | Bottleneck |
|-------------------|-----------------|-----------|
| Login             | 100 ms          | Django auth                |
| List problems     | 50 ms           | DB query                   |
| List submissions  | 100 ms          | DB join (user + problem)   |
| Submit code       | 50 ms           | Validation                 |
| Judge 1 test      | 2-5 s           | Container spawn + compile  |
| Judge 10 tests    | 20-50 s         | Serial execution           |
| Scoreboard (100 students) | 200 ms  | Redis cache hit            |
| Scoreboard (miss) | 2-5 s           | DB aggregation + sort      |

## Future Extensibility

### Multi-Language Judge

To support Python, C++, etc., extend `./backend/judge/`:
- Detect language from file extension
- Use appropriate base image (e.g., `python:3.11` for Python)
- Adjust compile/run commands per language
- Scale worker concurrency by language resource needs

### Advanced Features

- **Problem versioning:** Track test case changes, old submissions re-judge
- **Plagiarism detection:** MOSS API integration
- **Dynamic scoring:** Per-problem weights in contests
- **Practice modes:** Untimed problem solving with hints
- **Peer review:** Student code annotation + feedback

### Monitoring & Observability

- **Logging:** Structured logs (JSON) to ELK stack
- **Metrics:** Prometheus + Grafana (queue depth, judge latency, verdict distribution)
- **Tracing:** OpenTelemetry + Jaeger (end-to-end request traces)
- **Uptime:** Monitor compose healthchecks (Postgres/Redis) and reverse-proxy probes against the frontend/API

---

**For questions or clarifications, see [CONTRIBUTING.md](../CONTRIBUTING.md).**
