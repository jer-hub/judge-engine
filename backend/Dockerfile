FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Every dependency ships wheels (e.g. psycopg[binary]), so no compiler or
# libpq headers in the image; requirements.txt pins every version (pip-tools).
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Non-root by default. The judge workers override this with `user: "0"` in
# compose: they need the Docker socket, which is root-equivalent anyway.
RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R app:app /app
COPY --chown=app:app . .
USER app

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
