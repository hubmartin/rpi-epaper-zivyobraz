# RPI AP slop clone of zivyobraz client

Instead of ESP32 you can use RPI with e-paper.

## Install service

```
sudo cp zivyobraz.service /etc/systemd/system/
sudo systemctl daemon-reload

sudo systemctl enable zivyobraz.service
sudo systemctl start zivyobraz.service

systemctl status zivyobraz.service

```
