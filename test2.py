from machine import Pin, I2C
import sh1106

i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
oled = sh1106.SH1106_I2C(128,64,i2c)
oled.flip(True)

oled.fill(0)
oled.text("RX UNIT READY",0,0)
oled.text("OLED WORKING",0,20)
oled.show()