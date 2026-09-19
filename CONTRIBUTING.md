# Contributing to Judge Engine

Thank you for your interest in Judge Engine! Whether you're fixing a bug, adding a feature, or improving documentation, this guide will help you get started.

## Code of Conduct

Be respectful and constructive. We're building tools for educators and students.

## Getting Started

### Prerequisites

- **Docker Desktop** (Windows, macOS, Linux)
- **Git**
- **Node.js 18+** (for frontend work without Docker)
- **Python 3.10+** (for backend work without Docker)

### Local Development Setup

1. **Clone and enter the repo:**

   ```bash
   git clone https://github.com/jer-hub/judge-engine.git
   cd judge-engine
   ```

2. **Set up environment:**

   ```bash
   copy .env.example .env
   ```

   Edit `.env`:
   - For Windows: `JUDGE_HOST_DATA_DIR=C:/path/to/judge-engine/judge_data`
   - For Linux/macOS: `JUDGE_HOST_DATA_DIR=/path/to/judge-engine/judge_data`

3. **Start Docker Compose (recommended for full stack):**

   ```bash
   mkdir judge_data -Force  # PowerShell on Windows
   docker compose up --build -d
   ```

   Or on bash:
   ```bash
   mkdir -p judge_data
   docker compose up --build -d
   ```

4. **Seed demo data:**

   ```bash
   docker compose exec backend python manage.py seed_demo
   ```

5. **Access:**
   - Frontend: http://localhost:3000
   - Backend/Admin: http://localhost:8000/admin
   - Credentials: `admin` / `JudgeDev-Admin-ChangeMe!` (change this in `.env`)

### Frontend-Only Development

If you want to work on the frontend without running the full stack:

```bash
cd frontend
npm install
npm run dev
```

The frontend will still need a running backend API at `http://localhost:8000` (see above).

### Backend-Only Development

To run the backend locally (requires PostgreSQL + Redis):

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Separately, run Celery worker:

```bash
celery -A config worker --loglevel=info
```

## Testing

### Backend Tests

```bash
docker compose exec backend python manage.py test
```

Or locally:

```bash
cd backend
python manage.py test
```

Coverage:

```bash
docker compose exec backend coverage run --source='.' manage.py test
docker compose exec backend coverage report
```

### Frontend Tests

There is no dedicated frontend unit-test script yet. Prefer TypeScript checks and the [DEMO.md](DEMO.md) smoke flow:

```bash
cd frontend
npx tsc --noEmit
```

## Submission Process

### Branch Naming

Use a clear, descriptive branch name:

```
feature/add-problem-list-pagination
fix/judge-sandbox-memory-leak
docs/clarify-jwt-setup
```

### Commits

Use conventional commit format:

```
feat: add problem search filtering
fix: prevent duplicate submission enqueue
docs: update Docker setup instructions
test: add unit tests for scoreboard ranking
```

### Pull Requests

1. **Push your branch:**

   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a PR** on GitHub with:
   - Clear title and description
   - Reference any related issues (`Fixes #123`)
   - Screenshots or demo links if UI changes
   - Test results (backend tests passed, frontend builds, etc.)

3. **PR Requirements:**
   - All tests pass
   - No breaking changes to the public API (if this is a library)
   - For backend: include relevant migration scripts if DB changes
   - For frontend: works on desktop and tablet (mobile nice-to-have)

4. **Review:**
   - At least one maintainer review before merge
   - Address feedback constructively
   - Re-request review after making changes

## Areas for Contribution

### High Priority

- **Judge sandbox stability:** More Java test cases, edge-case handling
- **Performance:** Scoreboard query optimization, frontend bundle size
- **UX:** Dark mode, mobile responsiveness, accessibility (a11y)
- **Documentation:** Setup guides, troubleshooting, architecture diagrams

### Medium Priority

- **Additional languages:** Support for C++, Python, Go (requires sandbox changes)
- **Contest features:** Multiple contest types, problem categories, practice modes
- **Admin UI:** Bulk problem import, submission review tools

### Low Priority (Nice-to-Have)

- **Internationalization:** Non-English UI support
- **Analytics:** Contest result dashboards
- **API:** GraphQL layer (currently REST)

## Code Style

### Backend (Python/Django)

- Follow [PEP 8](https://pep8.org/)
- Use type hints where reasonable
- Keep models and views focused and testable
- Prefer `django.shortcuts` over raw queries

### Frontend (React/Next.js)

- Use TypeScript
- Prefer functional components and hooks
- Extract shared components to `frontend/components/`
- Use Tailwind CSS for styling; avoid inline styles
- Keep page components in `frontend/app/` organized by route

## Authentication Model

**Important:** Judge Engine is a **school platform with teacher-only admin controls.**

- **No public registration:** Teachers create accounts via Django Admin
- **Roles:** `admin` (teacher), `student`
- **Auth method:** JWT cookies, refreshed in-memory
- **Session lifetime:** Configurable (default 60 min access, 7 day refresh)

**When contributing:**
- Do not add public signup
- Preserve the role-based access control model
- Add admin checks where needed (e.g., `@permission_required('is_admin')`)

## Known Limitations & TODOs

See `TODO` comments in the codebase or open an issue to discuss:

- Java-only judge (extensible to other languages)
- No problem versioning/history tracking
- Admin UI is Django default (no custom interface)
- Submission throttle is per-user, not per-IP (vulnerable to distributed spam)

## Getting Help

- **Questions?** Open a GitHub Discussion
- **Found a bug?** Open an Issue with reproduction steps
- **Security issue?** See [SECURITY.md](SECURITY.md) for private reporting

## Documentation

- **Architecture:** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (if present)
- **Demo walkthrough:** See [DEMO.md](DEMO.md)
- **Setup:** See this file and `README.md`

---

Thank you for contributing! 🎓
