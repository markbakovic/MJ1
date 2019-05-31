# Mark's Joystick Number 1 - Research Edition development interface
# Bits of this are probably copyright Mark Bakovic and/or Bakovic Aerospace, 2019
import time
import spidev
import RPi.GPIO as GPIO

### GPIO setup section

# Use BCM GPIO references
# instead of physical pin numbers
GPIO.setmode(GPIO.BCM)

# Define GPIO signals to use for dodgy chip select
# Physical pins 11,13,15,29,31,33,35,37 (i.e. the block of 5 next to 39GND at lower right
# when looking at the board from above and with logos right way up and the three next to the middle 3.3V+)
# XGPIO17,XGPIO27,XGPIO22,GPIO5,GPIO6,GPIO13,GPIO19,GPIO26
CSPins = [5,6,13,19,26] # got rid of 17,27,22 for now

# for now let's say:
# 5 = X/Y axes stick
# 6 = Throttle
# 13 = dials throttle
# 19 = shift registers (buttons and hats) stick
# 26 = shift registers (buttons and 2pos and hat) throttle
# note each MCP3202 ADC is dual channel, so we could use one for both stick axes
# and one for both dials as here (suits pots fine), or use another GPIO pin and have both channels
# serve one axis on seperate ADCs (probably the way to go for hall sensing) 
# select which channel is read via SPI MOSI for the ADCs
# so these variables encode what is where
# [pin, channel/byte]
Xax = [5,0] # X-axis
Yax = [5,1] # Y-axis
Tax = [6,0] # Throttle axis
Rdl = [13,0] # Range dial (but not the clicker)
Adl = [13,1] # Antenna elevation dial
Sbu = [19,0] # All buttons on the stick (5)
Sh1 = [19,1] # H1/H4 (the grey hats on the stick)
Sh2 = [19,2] # H3/H2 (the black hats)

# mouse on the throttle might also just be 2 axes (it is on the cougar TQS, pins 10 and 11 on the gameport...)
# in fact, looks like just cleverly using the gameport is the way to go, there are no
# registers in the TQS

# Set all pins as output
for pin in CSPins:
    print("Setup pins")
    GPIO.setup(pin,GPIO.OUT)
    # check this. CS is often active low on SPI devices
    GPIO.output(pin, True) # seems right for stick and is right for ADCs

### End GPIO setup

### SPI setup section

# We only have SPI bus 0 available to us on the Pi
bus = 0

#Device is the chip select pin. Set to 0 or 1, depending on the connections
# possibly not implemented in my application, or switched via external circuitry
device = 1
# similar-purpose Arduino code uses a general pin for slave select/chip enable, so it whould be fine to use GPIO like I am doing...

# Enable SPI
spi = spidev.SpiDev()

# Open a connection to a specific bus and device (chip select pin)
# consider requirement for tristate buffers on all devices sharing the SPI bus
# as well use spi.cshigh if CS is active high after all, otherwise...
spi.open(bus, device)

# Set SPI speed and mode
spi.max_speed_hz = 500000
# check this. has to do with clock edges and data transitions
spi.mode = 0

# "performs an spi transaction" super clear that...
# msg = [0x76]
# spi.xfer2(msg)
# writes msg, returns the output from the device, probably useful for ADCs at least
# alternatively:
# bla = spi.readbytes(n bytes)
# spi.writebytes(list of bytes)
# though writebytes2 natively supports numpy arrays... otherwise use tolist()

### End SPI setup

### MCP3202 12-bit dual ADC setup
# Start bit is high 0x8
#st = 1
# I want single ended 0x4
#se = 1
# I want to start off reading channel 0, then channel 1 0x2
#ch0 = 0
#ch1 = 1
# I want MSB first 0x1
#msb = 1

# so my messages are:
adc0 = 0x08+0x04+0x01
adc1 = 0x08+0x04+0x02+0x01
ADCchan = [adc0,adc1]

# address the relevant ADC and assign output to xfer([0x0],[adc0/1]) to send a byte properly
### End ADC setup

# collect axis data seperately (since ADCs are activated AND channel selected by MOSI)
def pollCtrlAxis(ctrlSRC):
    GPIO.output(ctrlSRC[0],False)
    ctrlData = spi.xfer([0x0],[ADCchan[ctrlSRC[1]]])
    GPIO.output(ctrlSRC[0],True)
    return ctrlData

# collect button data once per hand (4021 chains clock out on sequential null MOSI)
# e.g. right hand? ctrlPin=19, registers=3
def pollCtrlButt(ctrlPin, registers):
    GPIO.output(ctrlPin,False)
    ctrlData = []
    i = 0
    while i < 3:
        ctrlData.append(spi.xfer([0x00]))
        i++
    GPIO.output(ctrlPin,True)
    return ctrlData
        

# take a string of byte data (eg chars) and plop them in a HID report
# default Flightstick Pro joystick sends 4 bytes (1 byte per axis,
# 4 bits hat direction (only one true), 4 bits for 4 buttons (can all be true))
def write_rep(report):
    with open('/dev/hidg0', 'rb+') as fd:
        fd.write(report.encode())
        
# convenient null byte if needed
nc = 0x00

# some FCLS+TQS data I may use
# axes include the two dials on the TQS
# All 8-bit so far (but my ADCs are 12 bit/channel so we can change later)
num_axes = 5
# pushy buttons not including the touchstick clicker (not sure it can work)
# but yes including the radar range dial clicker. Might add a null bit for padding...
# One-bit reports
num_buttons = 7
# two-position (centre null or 3 pos with centre NC if you like) switches,
# i.e. the dogfight switch, which stays in position either side,
# and the speed brake switch, which is stay-put one way and momentary the other
# Not decided yet, probably 2 bit
num_2pos = 2
# so. many. hats. all are four-way, but two (trim and radar) support dual-value
# (making them effectively 8-way). Note the report descriptor only sees them
# as 4-way, and calls the directions angles so I might have to bodge something
# to get "045" etc. as viable output. We'll see.
# 4 bits each
num_hats = 5

axis_size = 8
button_size = 1
tupos_size = 2
hat_size = 4 #actually it's 57 but never mind...

# some CH Flightstick Pro data for use with the initial version
num_axes = 3
num_buttons = 4
num_2pos = 0
num_hats = 1

# current report order is:
# Throttle/X/Y/Dials/Hats/Buttons(/2pos)
def organise(axes, axsize, buttons, buttsize, tupos, tupsize, hats, hatsize):
    repoutput = []
    #write each list order here!
    # fix this shit
    repaxes = [0x01]*(axes*axsize)
    for ax in repaxes:
        # just to test this out I'm writing null bytes. might as well get the data here eh?
        # ax.append(0x00*axsize)
    
    #repoutput = repaxes + rephats + repbutts + rep2pos
