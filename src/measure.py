import time
from machine import SoftI2C, Pin
from bmp280 import *

bmp = BMP280(SoftI2C(scl=Pin(16), sda=Pin(18)))

while not time.sleep(1):
    print(bmp.temperature)
