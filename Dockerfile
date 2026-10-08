FROM python:3.12-slim

# Unbuffered output so print() shows up in Railway logs immediately
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install deps first so this layer is cached when only code changes
COPY gazette/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "gazette/run.py"]