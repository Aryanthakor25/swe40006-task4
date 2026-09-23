# SWE40006 Task 4.3: StudyPulse (FastAPI), multi-stage build
# builder stage installs the packages into a venv, runtime stage only copies the venv + code

ARG PYTHON_VERSION=3.12

# ---- builder ----
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# requirements first so this layer stays cached when only the code changes
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# ---- runtime ----
FROM python:${PYTHON_VERSION}-slim AS runtime

ARG APP_VERSION=1.0.0

LABEL org.opencontainers.image.title="studypulse" \
      org.opencontainers.image.description="Study session tracker web app (SWE40006 Task 4.3)" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.authors="Aryan Thakor <105061154@student.swin.edu.au>" \
      org.opencontainers.image.source="https://github.com/Aryanthakor25/swe40006-task4"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_VERSION=${APP_VERSION} \
    APP_ENV=production \
    PORT=8000

# non-root user, fixed uid/gid
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /srv

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app app/ ./app/

USER app

EXPOSE 8000

# slim image has no curl, so the health check uses python's urllib
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

# exec form so uvicorn is PID 1 and gets the SIGTERM from docker stop
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
