# Security Policy

## Reporting a Vulnerability

Judge Engine is a school platform. If you discover a security vulnerability, please report it **privately** using GitHub Security Advisories to avoid public disclosure that could compromise active deployments.

### To report:

1. Visit the **Security** tab of this repository
2. Click **Report a vulnerability**
3. Describe the vulnerability in detail (reproducible steps, impact, affected component)
4. Submit the advisory — it will create a private conversation between you and the maintainers

We will:
- Acknowledge receipt within 3 days
- Investigate and develop a fix
- Coordinate a public disclosure date and security release

### Scope

We take the following seriously:
- **Authentication/authorization bypass** (e.g., unprivileged users accessing admin functions or other users' submissions)
- **Data exposure** (e.g., hidden tests leaking to students, database contents exposed)
- **Judge sandbox escape** (arbitrary code running outside the Docker container)
- **Denial of service** (crashing the platform, worker queue exhaustion)
- **Injection attacks** (SQL, code, etc.)

### Out of Scope

- Missing UI validation hints (already validated server-side)
- Requests to features not yet implemented
- Demo/test account password visibility (these are ephemeral dev credentials)
- Performance issues without a clear path to exploitation

## Security Considerations for Deployment

### Before Going Live

1. **Change all default credentials:**
   - Set a strong `BOOTSTRAP_ADMIN_PASSWORD` (50+ random chars)
   - Rotate `POSTGRES_PASSWORD` and `REDIS_URL` tokens
   - Generate a new `DJANGO_SECRET_KEY` (50+ random chars)

2. **Enable HTTPS:**
   - Set `JWT_COOKIE_SECURE=true` (requires HTTPS)
   - Use a reverse proxy (Nginx, Caddy) with valid SSL/TLS certificate
   - Redirect HTTP to HTTPS

3. **Configure JWT securely:**
   - Adjust `JWT_ACCESS_MINUTES` and `JWT_REFRESH_DAYS` for your threat model
   - Keep token lifetimes short for student accounts

4. **Harden judge sandboxing:**
   - Review Docker image updates (`eclipse-temurin:17-jdk-jammy`)
   - Consider additional seccomp/AppArmor profiles if deploying on untrusted hardware
   - Monitor judge logs for crashes or anomalies

5. **Restrict network access:**
   - Database and Redis should only be accessible from backend/worker containers
   - Block direct internet access from the judge sandbox
   - Use firewall rules to limit API endpoints to your school network if possible

6. **Enable audit logging:**
   - Log admin actions (problem creation, user deletion, etc.)
   - Monitor failed auth attempts
   - Archive logs securely

## Dependency Security

### Automated Scanning

- Python: Run `pip-audit` to check backend dependencies
- Node: Run `npm audit` to check frontend dependencies
- Keep Docker base images updated

### Supply Chain

- Pin dependency versions in `requirements.txt` and `package.json` to reproduced builds
- Use dependency verification tools (pip's hash checking, npm lockfiles)
- Review pull requests that update dependencies

## Incident Response

If a vulnerability is discovered after public deployment:

1. **Assess severity** (CVSS or similar)
2. **Prepare a patch** and test on a staging instance
3. **Announce in advance** (if time permits) on your school's channels
4. **Deploy patch** and verify all instances are updated
5. **Post-mortem:** Document the incident and improvements to prevent recurrence
