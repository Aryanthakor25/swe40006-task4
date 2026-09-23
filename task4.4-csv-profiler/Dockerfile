# SWE40006 Task 4.4: csvprofiler CLI image
# stdlib only, so there's no pip install step

FROM python:3.12-slim

ARG APP_VERSION=1.0.0

LABEL org.opencontainers.image.title="csvprofiler" \
      org.opencontainers.image.description="CLI tool that profiles CSV files and keeps a run history (SWE40006 Task 4.4)" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.authors="Aryan Thakor <105061154@student.swin.edu.au>" \
      org.opencontainers.image.source="https://github.com/Aryanthakor25/swe40006-task4"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PROFILER_INPUT=/data/input \
    PROFILER_OUTPUT=/data/output \
    PROFILER_DB=/var/lib/csvprofiler/history.db \
    LOG_LEVEL=info

# non-root user; data folders are created and chowned here so a new
# named volume mounted on /var/lib/csvprofiler is writable by this user
RUN groupadd --system --gid 10001 profiler \
 && useradd --system --uid 10001 --gid profiler --no-create-home --shell /usr/sbin/nologin profiler \
 && mkdir -p /data/input /data/output /var/lib/csvprofiler \
 && chown -R profiler:profiler /data /var/lib/csvprofiler

WORKDIR /opt/csvprofiler
COPY --chown=profiler:profiler csvprofiler/ ./csvprofiler/

USER profiler

# /data/input: bind mount with the CSV files (read-only)
# /data/output: bind mount so the reports end up on the host
# /var/lib/csvprofiler: named volume for history.db
VOLUME ["/data/output", "/var/lib/csvprofiler"]

# the image works like the CLI itself, e.g. docker run <image> profile-all
ENTRYPOINT ["python", "-m", "csvprofiler"]
CMD ["--help"]
