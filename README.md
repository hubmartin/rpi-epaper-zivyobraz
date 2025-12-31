# Clone of zivyobraz for RPI + e-paper

**AI slop clone**

Instead of ESP32 you can use RPI with e-paper.

[zivyobraz.eu](http://zivyobraz.eu/)
[original github repo](https://github.com/MultiTricker/zivyobraz-fw)

## Install service

```
sudo cp zivyobraz.service /etc/systemd/system/
sudo systemctl daemon-reload

sudo systemctl enable zivyobraz.service
sudo systemctl start zivyobraz.service

systemctl status zivyobraz.service

```
