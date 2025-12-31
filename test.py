#!/usr/bin/python3
# -*- coding:utf-8 -*-
import logging
from PIL import Image, ImageDraw, ImageFont

from waveshare_epd import epd7in5_V2

epd = epd7in5_V2.EPD()
logging.info("init")

epd.init()
Himage = Image.open('image.png')
epd.display(epd.getbuffer(Himage))
logging.info("Goto Sleep...")
epd.sleep()
