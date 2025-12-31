#!/usr/bin/python3
# -*- coding:utf-8 -*-
"""
ZivyObraz.eu client for Raspberry Pi with e-paper display.
Ported from ESP32/Arduino implementation.
"""

import io
import logging
import struct
import time
from typing import Optional, Tuple

import requests
from PIL import Image, ImageDraw, ImageFont

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

from waveshare_epd import epd7in5_V2

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants matching ESP32 firmware
HOST = "cdn.zivyobraz.eu"
FIRMWARE = "2.4"
URL_WIKI = "https://wiki.zivyobraz.eu"
DEFAULT_SLEEP_TIME = 120  # seconds
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
COLOR_TYPE = "BW"  # Black/White for epd7in5_V2

# Colors for BW display
COLOR_WHITE = 255
COLOR_BLACK = 0


def get_mac_address() -> str:
    """Get MAC address of the device formatted as XX:XX:XX:XX:XX:XX."""
    # Try to get MAC from wlan0 interface first, then eth0
    for interface in ['wlan0', 'eth0']:
        try:
            with open(f'/sys/class/net/{interface}/address', 'r') as f:
                mac = f.read().strip().upper()
                if mac and mac != '00:00:00:00:00:00':
                    return mac
        except FileNotFoundError:
            continue

    # Fallback: try to find any non-loopback interface
    import os
    try:
        for iface in os.listdir('/sys/class/net/'):
            if iface == 'lo':
                continue
            try:
                with open(f'/sys/class/net/{iface}/address', 'r') as f:
                    mac = f.read().strip().upper()
                    if mac and mac != '00:00:00:00:00:00':
                        return mac
            except BaseException:
                continue
    except BaseException:
        pass

    # Last resort fallback
    return "00:00:00:00:00:00"


def get_hostname() -> str:
    """Get hostname in format INK_XXXXXXXXXXXX (MAC without colons)."""
    mac = get_mac_address()
    return "INK_" + mac.replace(":", "")


class ZivyObrazClient:
    def __init__(self):
        self.epd = epd7in5_V2.EPD()
        self.timestamp = 0
        self.sleep_time = DEFAULT_SLEEP_TIME
        self.rotation = 0
        self.mac_address = get_mac_address()
        self.hostname = get_hostname()
        logger.info(f"MAC Address: {self.mac_address}")
        logger.info(f"Hostname: {self.hostname}")

    def init_display(self):
        """Initialize the e-paper display."""
        logger.info("Initializing display...")
        self.epd.init()

    def sleep_display(self):
        """Put display into sleep mode."""
        logger.info("Display going to sleep...")
        self.epd.sleep()

    def display_image(self, image: Image.Image):
        """Display a PIL Image on the e-paper."""
        # Ensure image is correct size
        if image.size != (DISPLAY_WIDTH, DISPLAY_HEIGHT):
            image = image.resize((DISPLAY_WIDTH, DISPLAY_HEIGHT))

        # Convert to 1-bit
        image = image.convert('1')

        self.epd.display(self.epd.getbuffer(image))

    def display_registration_info(self):
        """Display registration information on the e-paper screen."""
        logger.info("Displaying registration information...")
        logger.info(f"To register this device, go to: {URL_WIKI}")
        logger.info(f"MAC Address: {self.mac_address}")

        self.init_display()

        # Create image
        image = Image.new('1', (DISPLAY_WIDTH, DISPLAY_HEIGHT), COLOR_WHITE)
        draw = ImageDraw.Draw(image)

        # Try to load a font, fall back to default
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except BaseException:
            font_large = ImageFont.load_default()
            font_medium = font_large
            font_small = font_large

        # Draw header bar
        draw.rectangle([0, 0, DISPLAY_WIDTH, 70], fill=COLOR_BLACK)

        # Header text
        header_text = "Device Not Registered"
        bbox = draw.textbbox((0, 0), header_text, font=font_large)
        text_width = bbox[2] - bbox[0]
        draw.text(((DISPLAY_WIDTH - text_width) // 2, 10), header_text, font=font_large, fill=COLOR_WHITE)

        subheader_text = "Register at zivyobraz.eu to display content"
        bbox = draw.textbbox((0, 0), subheader_text, font=font_medium)
        text_width = bbox[2] - bbox[0]
        draw.text(((DISPLAY_WIDTH - text_width) // 2, 42), subheader_text, font=font_medium, fill=COLOR_WHITE)

        # MAC Address section
        y_pos = 100
        mac_label = "MAC Address (use for registration):"
        draw.text((50, y_pos), mac_label, font=font_medium, fill=COLOR_BLACK)

        y_pos += 30
        draw.text((50, y_pos), self.mac_address, font=font_large, fill=COLOR_BLACK)

        # Hostname section
        y_pos += 50
        hostname_label = "Device Hostname:"
        draw.text((50, y_pos), hostname_label, font=font_medium, fill=COLOR_BLACK)

        y_pos += 30
        draw.text((50, y_pos), self.hostname, font=font_large, fill=COLOR_BLACK)

        # Instructions
        y_pos += 60
        instructions = [
            "1. Go to https://zivyobraz.eu",
            "2. Create an account or log in",
            "3. Register this device using the MAC address above",
            "4. Configure your display content",
            "5. The display will update automatically"
        ]

        for instruction in instructions:
            draw.text((50, y_pos), instruction, font=font_small, fill=COLOR_BLACK)
            y_pos += 25

        # QR code for wiki
        if HAS_QRCODE:
            qr = qrcode.QRCode(version=1, box_size=4, border=2)
            qr.add_data(URL_WIKI)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.convert('1')

            # Place QR code on right side
            qr_x = DISPLAY_WIDTH - qr_img.size[0] - 50
            qr_y = 100
            image.paste(qr_img, (qr_x, qr_y))

            # QR label
            qr_label = "Scan for help"
            bbox = draw.textbbox((0, 0), qr_label, font=font_small)
            text_width = bbox[2] - bbox[0]
            draw.text((qr_x + (qr_img.size[0] - text_width) // 2, qr_y + qr_img.size[1] + 5),
                      qr_label, font=font_small, fill=COLOR_BLACK)

        # Footer
        draw.rectangle([0, DISPLAY_HEIGHT - 40, DISPLAY_WIDTH, DISPLAY_HEIGHT], fill=COLOR_BLACK)
        footer_text = f"Documentation: {URL_WIKI}"
        bbox = draw.textbbox((0, 0), footer_text, font=font_small)
        text_width = bbox[2] - bbox[0]
        draw.text(((DISPLAY_WIDTH - text_width) // 2, DISPLAY_HEIGHT - 30),
                  footer_text, font=font_small, fill=COLOR_WHITE)

        self.display_image(image)
        self.sleep_display()

    def check_for_update(self) -> Tuple[bool, int, int]:
        """
        Check server for updates.
        Returns: (needs_update, sleep_time, rotation)
        """
        url = f"http://{HOST}/index.php"
        params = {
            'mac': self.mac_address,
            'timestamp_check': '1',
            'rssi': '-50',  # Placeholder for WiFi signal strength
            'ssid': 'RaspberryPi',
            'v': '5.0',  # Placeholder voltage
            'x': str(DISPLAY_WIDTH),
            'y': str(DISPLAY_HEIGHT),
            'c': COLOR_TYPE,
            'fw': FIRMWARE,
            'ap_retries': '0'
        }

        logger.info(f"Checking for updates at {url}")
        logger.debug(f"Parameters: {params}")

        try:
            response = requests.get(url, params=params, timeout=30)
            logger.info(f"Response status: {response.status_code}")

            if response.status_code != 200:
                logger.warning(f"Server returned status {response.status_code}")
                return False, DEFAULT_SLEEP_TIME, 0

            # Parse headers
            timestamp_now = 0
            sleep_time = DEFAULT_SLEEP_TIME
            rotation = 0

            for header, value in response.headers.items():
                header_lower = header.lower()
                if header_lower == 'timestamp':
                    timestamp_now = int(value)
                    logger.info(f"Timestamp from server: {timestamp_now}")
                elif header_lower == 'sleep':
                    sleep_time = int(value) * 60  # Convert minutes to seconds
                    logger.info(f"Sleep time: {sleep_time} seconds ({value} minutes)")
                elif header_lower == 'sleepseconds':
                    sleep_time = int(value)
                    logger.info(f"Sleep time: {sleep_time} seconds")
                elif header_lower == 'rotate':
                    rotation = int(value)
                    logger.info(f"Rotation: {rotation}")

            # Check if update needed
            if timestamp_now != self.timestamp:
                logger.info(f"Update needed: timestamp changed from {self.timestamp} to {timestamp_now}")
                self.timestamp = timestamp_now
                self.sleep_time = sleep_time
                self.rotation = rotation
                return True, sleep_time, rotation
            else:
                logger.info("No update needed, timestamp unchanged")
                return False, sleep_time, rotation

        except requests.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            return False, DEFAULT_SLEEP_TIME, 0

    def download_and_display_image(self) -> bool:
        """
        Download image from server and display it.
        Returns: True if successful, False otherwise
        """
        url = f"http://{HOST}/index.php"
        params = {
            'mac': self.mac_address,
            'rssi': '-50',
            'ssid': 'RaspberryPi',
            'v': '5.0',
            'x': str(DISPLAY_WIDTH),
            'y': str(DISPLAY_HEIGHT),
            'c': COLOR_TYPE,
            'fw': FIRMWARE,
            'ap_retries': '0'
        }

        logger.info("Downloading image...")

        try:
            response = requests.get(url, params=params, timeout=60, stream=True)

            if response.status_code != 200:
                logger.error(f"Failed to download image: status {response.status_code}")
                return False

            # Read first 2 bytes to determine format
            data = response.content
            if len(data) < 2:
                logger.error("Response too short")
                return False

            header = struct.unpack('<H', data[:2])[0]
            logger.info(f"Image format header: 0x{header:04X}")

            self.init_display()

            if header == 0x4D42:  # BMP signature "BM"
                image = self.decode_bmp(data)
            elif header == 0x315A:  # Z1 format
                image = self.decode_rle_z1(data)
            elif header == 0x325A:  # Z2 format
                image = self.decode_rle_z2(data)
            elif header == 0x335A:  # Z3 format
                image = self.decode_rle_z3(data)
            else:
                logger.error(f"Unknown image format: 0x{header:04X}")
                return False

            if image is None:
                logger.error("Failed to decode image")
                return False

            # Apply rotation if needed
            if self.rotation == 1:
                image = image.rotate(-90, expand=True)
            elif self.rotation == 2:
                image = image.rotate(180)
            elif self.rotation == 3:
                image = image.rotate(90, expand=True)

            self.display_image(image)
            self.sleep_display()

            logger.info("Image displayed successfully")
            return True

        except requests.RequestException as e:
            logger.error(f"Failed to download image: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return False

    def decode_bmp(self, data: bytes) -> Optional[Image.Image]:
        """Decode BMP format image data."""
        logger.info("Decoding BMP image...")

        try:
            # Parse BMP header
            if len(data) < 54:
                logger.error("BMP data too short")
                return None

            # BMP header structure
            signature = struct.unpack('<H', data[0:2])[0]
            if signature != 0x4D42:
                logger.error("Invalid BMP signature")
                return None

            file_size = struct.unpack('<I', data[2:6])[0]
            image_offset = struct.unpack('<I', data[10:14])[0]
            header_size = struct.unpack('<I', data[14:18])[0]
            width = struct.unpack('<I', data[18:22])[0]
            height = struct.unpack('<i', data[22:26])[0]  # Signed for flip detection
            planes = struct.unpack('<H', data[26:28])[0]
            depth = struct.unpack('<H', data[28:30])[0]
            compression = struct.unpack('<I', data[30:34])[0]

            logger.info(f"BMP: {width}x{abs(height)}, {depth}bpp, compression={compression}")

            if planes != 1:
                logger.error(f"Unsupported planes: {planes}")
                return None

            if compression not in (0, 3):  # 0=uncompressed, 3=565
                logger.error(f"Unsupported compression: {compression}")
                return None

            # Handle negative height (top-to-bottom)
            flip = height > 0
            height = abs(height)

            # Create output image
            image = Image.new('L', (width, height), COLOR_WHITE)
            pixels = image.load()

            # Calculate row size (padded to 4-byte boundary)
            if depth < 8:
                row_size = ((width * depth + 31) // 32) * 4
            else:
                row_size = ((width * depth // 8 + 3) // 4) * 4

            # Read palette for indexed images
            palette = []
            if depth <= 8:
                palette_offset = 14 + header_size
                num_colors = 1 << depth
                for i in range(num_colors):
                    idx = palette_offset + i * 4
                    if idx + 4 <= len(data):
                        b, g, r, _ = struct.unpack('BBBB', data[idx:idx + 4])
                        # Convert to grayscale and determine if whitish
                        gray = (r + g + b) // 3
                        palette.append(COLOR_WHITE if gray > 0x80 else COLOR_BLACK)
                    else:
                        palette.append(COLOR_WHITE)

            # Read pixel data
            for row in range(height):
                if flip:
                    y = height - 1 - row
                else:
                    y = row

                row_offset = image_offset + row * row_size

                if depth == 1:
                    for col in range(width):
                        byte_idx = row_offset + col // 8
                        if byte_idx < len(data):
                            bit = 7 - (col % 8)
                            pn = (data[byte_idx] >> bit) & 1
                            pixels[col, y] = palette[pn] if pn < len(palette) else COLOR_WHITE

                elif depth == 4:
                    for col in range(width):
                        byte_idx = row_offset + col // 2
                        if byte_idx < len(data):
                            if col % 2 == 0:
                                pn = (data[byte_idx] >> 4) & 0x0F
                            else:
                                pn = data[byte_idx] & 0x0F
                            pixels[col, y] = palette[pn] if pn < len(palette) else COLOR_WHITE

                elif depth == 8:
                    for col in range(width):
                        byte_idx = row_offset + col
                        if byte_idx < len(data):
                            pn = data[byte_idx]
                            pixels[col, y] = palette[pn] if pn < len(palette) else COLOR_WHITE

                elif depth == 16:
                    for col in range(width):
                        byte_idx = row_offset + col * 2
                        if byte_idx + 1 < len(data):
                            lsb = data[byte_idx]
                            msb = data[byte_idx + 1]
                            if compression == 0:  # 555
                                r = (msb & 0x7C) << 1
                                g = ((msb & 0x03) << 6) | ((lsb & 0xE0) >> 2)
                                b = (lsb & 0x1F) << 3
                            else:  # 565
                                r = msb & 0xF8
                                g = ((msb & 0x07) << 5) | ((lsb & 0xE0) >> 3)
                                b = (lsb & 0x1F) << 3

                            whitish = (r + g + b) > 3 * 0x80
                            pixels[col, y] = COLOR_WHITE if whitish else COLOR_BLACK

                elif depth in (24, 32):
                    bytes_per_pixel = depth // 8
                    for col in range(width):
                        byte_idx = row_offset + col * bytes_per_pixel
                        if byte_idx + 2 < len(data):
                            b = data[byte_idx]
                            g = data[byte_idx + 1]
                            r = data[byte_idx + 2]

                            whitish = (r + g + b) > 3 * 0x80
                            pixels[col, y] = COLOR_WHITE if whitish else COLOR_BLACK

            return image.convert('1')

        except Exception as e:
            logger.error(f"BMP decode error: {e}")
            return None

    def decode_rle_z1(self, data: bytes) -> Optional[Image.Image]:
        """Decode ZivyObraz Z1 RLE format (1 byte color + 1 byte count)."""
        logger.info("Decoding Z1 RLE image...")

        try:
            image = Image.new('L', (DISPLAY_WIDTH, DISPLAY_HEIGHT), COLOR_WHITE)
            pixels = image.load()

            idx = 2  # Skip header
            x, y = 0, 0

            while idx + 1 < len(data) and y < DISPLAY_HEIGHT:
                pixel_color = data[idx]
                count = data[idx + 1]
                idx += 2

                color = self._get_color_from_index(pixel_color)

                for _ in range(count):
                    if x < DISPLAY_WIDTH and y < DISPLAY_HEIGHT:
                        pixels[x, y] = color
                    x += 1
                    if x >= DISPLAY_WIDTH:
                        x = 0
                        y += 1
                        if y >= DISPLAY_HEIGHT:
                            break

            logger.info(f"Z1 decoded: {idx} bytes read")
            return image.convert('1')

        except Exception as e:
            logger.error(f"Z1 decode error: {e}")
            return None

    def decode_rle_z2(self, data: bytes) -> Optional[Image.Image]:
        """Decode ZivyObraz Z2 RLE format (2 bits color + 6 bits count)."""
        logger.info("Decoding Z2 RLE image...")

        try:
            image = Image.new('L', (DISPLAY_WIDTH, DISPLAY_HEIGHT), COLOR_WHITE)
            pixels = image.load()

            idx = 2  # Skip header
            x, y = 0, 0

            while idx < len(data) and y < DISPLAY_HEIGHT:
                compressed = data[idx]
                idx += 1

                count = compressed & 0b00111111
                pixel_color = (compressed & 0b11000000) >> 6

                color = self._get_color_from_index(pixel_color)

                for _ in range(count):
                    if x < DISPLAY_WIDTH and y < DISPLAY_HEIGHT:
                        pixels[x, y] = color
                    x += 1
                    if x >= DISPLAY_WIDTH:
                        x = 0
                        y += 1
                        if y >= DISPLAY_HEIGHT:
                            break

            logger.info(f"Z2 decoded: {idx} bytes read")
            return image.convert('1')

        except Exception as e:
            logger.error(f"Z2 decode error: {e}")
            return None

    def decode_rle_z3(self, data: bytes) -> Optional[Image.Image]:
        """Decode ZivyObraz Z3 RLE format (3 bits color + 5 bits count)."""
        logger.info("Decoding Z3 RLE image...")

        try:
            image = Image.new('L', (DISPLAY_WIDTH, DISPLAY_HEIGHT), COLOR_WHITE)
            pixels = image.load()

            idx = 2  # Skip header
            x, y = 0, 0

            while idx < len(data) and y < DISPLAY_HEIGHT:
                compressed = data[idx]
                idx += 1

                count = compressed & 0b00011111
                pixel_color = (compressed & 0b11100000) >> 5

                color = self._get_color_from_index(pixel_color)

                for _ in range(count):
                    if x < DISPLAY_WIDTH and y < DISPLAY_HEIGHT:
                        pixels[x, y] = color
                    x += 1
                    if x >= DISPLAY_WIDTH:
                        x = 0
                        y += 1
                        if y >= DISPLAY_HEIGHT:
                            break

            logger.info(f"Z3 decoded: {idx} bytes read")
            return image.convert('1')

        except Exception as e:
            logger.error(f"Z3 decode error: {e}")
            return None

    def _get_color_from_index(self, pixel_color: int) -> int:
        """Convert color index to grayscale value for BW display."""
        if pixel_color == 0:
            return COLOR_WHITE
        elif pixel_color == 1:
            return COLOR_BLACK
        else:
            # For color displays (red, yellow, etc.), treat as black on BW display
            return COLOR_BLACK

    def run(self):
        """Main loop."""
        logger.info("Starting ZivyObraz client...")
        logger.info(f"MAC: {self.mac_address}")
        logger.info(f"Display: {DISPLAY_WIDTH}x{DISPLAY_HEIGHT}")

        first_run = True

        while True:
            try:
                needs_update, sleep_time, rotation = self.check_for_update()

                if needs_update:
                    success = self.download_and_display_image()
                    if not success and first_run:
                        # Show registration info on first failure
                        self.display_registration_info()
                    first_run = False
                elif first_run:
                    # First run but no update - might not be registered
                    self.display_registration_info()
                    first_run = False

                logger.info(f"Sleeping for {sleep_time} seconds...")
                time.sleep(sleep_time)

            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                if first_run:
                    try:
                        self.display_registration_info()
                    except BaseException:
                        pass
                    first_run = False
                time.sleep(DEFAULT_SLEEP_TIME)


def main():
    client = ZivyObrazClient()
    client.run()


if __name__ == "__main__":
    main()
