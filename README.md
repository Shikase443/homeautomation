<h2>ADRSZIRS</h2>
Raspberry Pi Zero 2 WH(64bit Raspbian)でビットトレードワンのIRリモコンHATを操作するコンテナイメージです。

Build & run
```
podman build -t remocon_srv .
podman run -d --restart=always --name remocon_srv --privileged --device /dev/i2c-1:/dev/i2c-1 -p 5000:5000 remocon_srv:latest
```

IR学習
```
curl http://localhost:5000/read
```

IR送信
```
curl -X POST -H "Content-Type: application/json" -d '{"data": "5B0018002E001800....."}' http://localhost:5000/write
```
