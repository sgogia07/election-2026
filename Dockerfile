FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1 PORT=10000
WORKDIR /srv
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ffmpeg chromium xvfb espeak-ng curl fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY start.sh .
RUN chmod +x ./start.sh
EXPOSE 10000
CMD ["./start.sh"]
