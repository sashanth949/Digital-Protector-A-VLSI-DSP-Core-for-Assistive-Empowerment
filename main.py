from machine import Pin, I2C
import sh1106
import uselect, sys, time, math, random

# OLED
i2c = I2C(0, scl=Pin(5), sda=Pin(4))
oled = sh1106.SH1106_I2C(128,64,i2c)
oled.flip(True)

# Serial input poll
poll = uselect.poll()
poll.register(sys.stdin, uselect.POLLIN)

# Defaults
mode = "AUTO"
flt = "AVG"
noise = 0
phase = 0

while True:

    # -------------------------
    # Read serial from laptop
    # Format:
    # RX,AUTO,AVG,72
    # -------------------------
    if poll.poll(1):
        line = sys.stdin.readline().strip()

        parts = line.split(",")

        if len(parts) >= 4:
            mode = parts[1]
            flt = parts[2]
            noise = int(parts[3])

    oled.fill(0)

    oled.text("MODE:"+mode,0,0)
    oled.text("FLT:"+flt,0,10)
    oled.text("QUAL:"+str(max(0,100-noise))+"%",0,20)

    oled.hline(0,30,128,1)

    # -------------------------
    # Draw filtered waveform
    # -------------------------
    prev1 = 47
    prev2 = 47
    prev3 = 47

    for x in range(128):

        # Base signal + noise
        y = 47 + 9 * math.sin((x + phase) * 0.18)

        amp = int(noise / 10)
        y += random.randint(-amp, amp)

        # FILTERS
        if flt == "AVG":
            y = (y + prev1 + prev2) / 3

        elif flt == "MEDIAN":
            vals = [y, prev1, prev2]
            vals.sort()
            y = vals[1]


        elif flt == "LOWPASS":
            y = 0.2 * y + 0.8 * prev1

        y = int(max(32, min(63, y)))

        oled.pixel(x, y, 1)

        prev3 = prev2
        prev2 = prev1
        prev1 = y

    oled.show()

    phase += 2
    time.sleep(0.08)