# Backups and restore

In production (`docker-compose.prod.yml`) the `db-backup` service runs
`pg_dump` once a day and writes compressed dumps to `./backups` on the host:

```
backups/judge_engine-20261001-020000.dump
```

Dumps older than `BACKUP_KEEP_DAYS` (default 14) are deleted. Set
`BACKUP_INTERVAL_SECONDS` to change the schedule (default 86400 = daily).

**A backup on the same disk is not a backup.** Copy `./backups` to another
machine or storage regularly (for example a nightly `rsync` or a synced
school drive).

What is not in the dump: uploaded media (`media_data` volume) and Caddy's
certificates (`caddy_data`, re-issued automatically). Problems, test cases,
users, contests and submissions are all in the database.

## Take a backup now

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec db-backup \
  sh -c 'pg_dump --format=custom --file=/backups/manual-$(date +%Y%m%d-%H%M%S).dump'
```

## Check that backups work

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs db-backup --tail 5
# expect: backup ok: /backups/judge_engine-....dump (…)
```

## Restore

Restoring **replaces the current database**. Take a fresh dump first.

```bash
COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

# 1. Stop everything that writes to the database.
$COMPOSE stop backend worker worker-preview frontend

# 2. Restore (drops and recreates objects from the dump).
$COMPOSE exec db-backup sh -c 'pg_restore --clean --if-exists --no-owner \
  --dbname="$PGDATABASE" /backups/judge_engine-20261001-020000.dump'

# 3. Start again (migrations run on backend start).
$COMPOSE up -d
```

Practise a restore once, on a spare machine or a separate compose project
(`docker compose -p judge-restore-test ...`), before you need it.
