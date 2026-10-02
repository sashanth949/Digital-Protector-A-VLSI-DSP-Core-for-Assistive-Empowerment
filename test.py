from machine import Pin, I2C, ADC, SPI
import sh1106
import time

# ----------------------------
# OLED
# ----------------------------
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=100000)
oled = sh1106.SH1106_I2C(128, 64, i2c)
oled.flip(True)

# ----------------------------
# POTENTIOMETER
# ----------------------------
pot = ADC(26)

# ----------------------------
# NRF PINS
# ----------------------------
ce = Pin(17, Pin.OUT)
csn = Pin(16, Pin.OUT)

spi = SPI(
    0,
    baudrate=1000000,
    polarity=0,
    phase=0,
    sck=Pin(18),
    mosi=Pin(19),
    miso=Pin(20)
)

# ----------------------------
# NRF REGISTER READ
# ----------------------------
def nrf_read_register(reg):
    csn.value(0)
    spi.write(bytearray([reg]))
    data = spi.read(1)
    csn.value(1)
    return data[0]

# ----------------------------
# BOOT SCREEN
# ----------------------------
oled.fill(0)
oled.text("TX SYSTEM BOOT", 0, 0)
oled.text("CHECKING...", 0, 20)
oled.show()
time.sleep(2)

# ----------------------------
# TEST NRF
# ----------------------------
try:
    val = nrf_read_register(0x00)   # CONFIG register
    nrf_ok = True
except:
    nrf_ok = False

# ----------------------------
# MAIN LOOP
# ----------------------------
count = 0

while True:

    # Read pot
    raw = pot.read_u16()
    percent = int(raw * 100 / 65535)

    oled.fill(0)

    # Header
    oled.text("TRANSMITTER", 0, 0)

    # NRF status
    if nrf_ok:
        oled.text("NRF: OK", 0, 12)
    else:
        oled.text("NRF: FAIL", 0, 12)

    # Pot status
    oled.text("NOISE:" + str(percent) + "%", 0, 24)

    # Counter
    oled.text("CNT:" + str(count), 0, 36)

    # Progress bar
    oled.rect(0, 52, 128, 10, 1)
    bar = int(percent * 124 / 100)
    oled.fill_rect(2, 54, bar, 6, 1)

    oled.show()

    count += 1
    time.sleep(0.1)