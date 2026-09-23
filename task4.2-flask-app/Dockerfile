# SWE40006 Task 4.2: Flask web app image

FROM python:3.12-slim

# Don't write .pyc files and don't buffer stdout, so `docker logs` shows output straight away
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

# Copy requirements first so the dependency layer is cached between code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the application code
COPY app.py .

# Document the port the app listens on (published with -p at run time)
EXPOSE 5000

CMD ["python", "app.py"]
