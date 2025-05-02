FROM python:3.11-slim-bookworm

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     bluetooth bluez libdbus-1-dev build-essential \
  && pip install --no-cache-dir bleak requests \
  && rm -rf /var/lib/apt/lists/*

ENV DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket

WORKDIR /app
COPY scanner.py /app/
CMD ["python3", "scanner.py"]
