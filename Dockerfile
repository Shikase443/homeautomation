FROM docker.io/python:3.9-alpine

RUN apk update && apk add --no-cache \
    i2c-tools

RUN pip install --no-cache-dir \
    flask \
    smbus2

WORKDIR /app
COPY remocon_srv.py /app/remocon_srv.py

CMD ["python", "remocon_srv.py"]
