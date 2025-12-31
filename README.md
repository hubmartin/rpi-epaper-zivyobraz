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

## AI prompt for Claude

I am using project http://zivyobraz.eu/ in the file zivyobraz/main.cpp  which  is written in C Arduino ESP32 and loads an image from internet and I want to port it to the Raspberry Pi Python code with epaper hardware.
My raspberry pi code already works and in client/minimal.py is working example.

I would like you to create new python file zivyobraz.py that is working exactly as the zivyobraz/main.cpp. right now, you can support only my display epd7in5_V2.EPD() and ignore others.

Bascially I would like to have working at least configModeCallback to display info to log in to zivyobraz.eu and decoding part readBitmapData to show on the screen.

Get the mac address from the RPI wlan0.