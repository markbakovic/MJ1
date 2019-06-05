# Mark's Joystick Number 1 - Research Edition development interface
# Bits of this are probably copyright Mark Bakovic and/or Bakovic Aerospace, 2019
# but I'm happy for any non-commercial use, just credit me.
# Otherwise email me: my full name @ google's email and we can talk ;)

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
# 19 = touchstick (mouse) on throttle
# 26 = shift registers (buttons and hats) stick
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
Tmx = [19,0] # Touchstick X
Tmy = [19,1] # Touchstick Y
#Sbu = [26,0] # All buttons on the stick (5)
#Sh1 = [26,1] # H1/H4 (the grey hats on the stick)
#Sh2 = [26,2] # H3/H2 (the black hats)

# mouse on the throttle might also just be 2 axes (it is on the cougar TQS, pins 10 and 11 on the gameport...)
# in fact, looks like just cleverly using the gameport is the way to go, there are no
# registers in the TQS

# Set all pins as output
for pin in CSPins:
    print("Setup CS pins")
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

# collect button from the stick (4021 chains clock out on sequential null MOSI)
# currently ctrlPin=26, registers=3
def pollCtrlStickButt(ctrlPin, registers):
    GPIO.output(ctrlPin,False)
    ctrlData = []
    i = 0
    while i < registers:
        ctrlData.append([spi.xfer([0x00]]))
        i+=1
    GPIO.output(ctrlPin,True)
    return ctrlData

# TQS is different to stick, uses button matrix. Poll pins (gameport 2,3,4 => P2/P3/P4 here)
# normally held high, low to poll. Sense pins are pulled up by resist, pulled
# down by low poll pin through any closed switch (=pressed button).
# Poll 4,2,3,4 to debounce momentaries (T1/T6 both on P4 => S7/S6 resp.)
# So: need to define 7 GPIO pins to handle TQS buttons. Using other side (and other 3.3V)
# i.e. Pi17=SPI3.3V/Pi25=SPIGND while Pi01=TQSButt3.3V etc.
# TQSButt GPIO 23,24,25,12,16,20,21 = Pi 16,18,22,32,36,38,40
# and i might make the last 3 (because they're all together in the header) the
# poll pins so:
# [21,P2], [20,P3], [16,P4], [12,S6], [25,S7], [24,S8], [23,S9]
TPpins = [16,20,21]
TSpins = [23,24,25,12]

for pin in TPPins:
    print("Setup TP pins")
    GPIO.setup(pin,GPIO.OUT)
    GPIO.output(pin, True)
    
for pin in TSPins:
    print("Setup TS pins")
    GPIO.setup(pin,GPIO.IN)

def pollCtrlThrotButt():
    ctrlData = []
    #poll P4 first here if debounce needed
    for poll in TPpins:
        GPIO.output(poll, False)
        for sense in TSpins:
            ctrlData.append(not GPIO.input(sense))
        GPIO.output(poll, True)
    return ctrlData

That = [T2,T5,T3,T4]
Df = [T7,T8]
Sb = [T9,T10]
Rk = T6
Cur = T1

TBits = That+Df+Sb+Rk+Cur

# take a string of byte data (eg chars) and plop them in a HID report
# default Flightstick Pro joystick sends 4 bytes (1 byte per axis,
# 4 bits hat direction (only one true), 4 bits for 4 buttons (can all be true))
def write_rep(report):
    with open('/dev/hidg0', 'rb+') as fd:
        fd.write(report.encode())
        
# convenient null byte if needed
nc = 0x00

# some FCLS+TQS data I may use
# axes include the two dials and the thumbstick on the TQS
# my ADCs are 12 bit/channel
num_axes = 7
# pushy buttons including the touchstick clicker (T1)
# but yes including the radar range dial clicker. Might add a null bit for padding...
# One-bit reports
num_buttons = 8
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

axis_size = 12
button_size = 1
tupos_size = 2
hat_size = 4 #actually it's 57 but never mind...

# some CH Flightstick Pro data for use with the initial version
num_axes = 3
num_buttons = 4
num_2pos = 0
num_hats = 1

# stuff it, let's hold everything in memory
X = [False]*axis_size #stick X
Y = [False]*axis_size
T = [False]*axis_size #14 throttle
R = [False]*axis_size #13 range knob
A = [False]*axis_size #12 antenna elevation
x = [False]*axis_size #touchstick X 10
y = [False]*axis_size #11
H1 = [False]*hat_size #trim DRUL R2x80,40,20,10
H2 = [False]*hat_size #tms DRUL R3x08,04,02,01
H3 = [False]*hat_size #dms ULDR R3x80,40,20,10
H4 = [False]*hat_size #cms DRUL R2x08,04,02,01
HT = [False]*hat_size #rad ULDR T2,T5,T3,T4
S3 = False #pinky R1x80
TG1 = False #Trigger stage 1 R1x40
TG2 = False #Trigger stage 2 R1x20
S1 = False #index R1x10
S4 = False #paddle R1x08
S2 = False #thumb/weaprel R1x04
DF = [False]*tupos_size #dogfight T7,8
SB = [False]*tupos_size #speedbrake T9,10
RK = False #range knob clicker T6
MC = False #touchstick selector T1

Axes = [[Xax,X], [Yax,Y], [Tax,T], [Rdl,R], [Adl,A], [Tmx,x], [Tmy,y]]

def poll():
    for ax in Axes:
        ax[1] = pollCtrlAxis(ax[0])
    data = pollCtrlThrotButt()
    i=0
    for rad in HT:
        rad = data[i]
        i+=1
    for dog in DF:
        dog = data[i]
        i+=1
    for brake in SB:
        brake = data[i]
        i+=1
    RK = data[i]
    MC = data[i+1]
    i=0
    data = pollCtrlStickButt(26,3)
    a = data[0]
    S3 = 0x80==0x80&a
    TG1 = 0x40==0x40&a
    TG2 = 0x20==0x20&a
    S1 = 0x10==0x10&a
    S4 = 0x08==0x08&a
    S2 = 0x04==0x04&a
    a = data[1]
    H1[0] = 0x80==0x80&a
    H1[1] = 0x40==0x40&a
    H1[2] = 0x20==0x20&a
    H1[3] = 0x10==0x10&a
    H4[0] = 0x08==0x08&a
    H4[1] = 0x04==0x04&a
    H4[2] = 0x02==0x02&a
    H4[3] = 0x01==0x01&a
    a = data[2]
    H3[0] = 0x80==0x80&a
    H3[1] = 0x40==0x40&a
    H3[2] = 0x20==0x20&a
    H3[3] = 0x10==0x10&a
    H2[0] = 0x08==0x08&a
    H2[1] = 0x04==0x04&a
    H2[2] = 0x02==0x02&a
    H2[3] = 0x01==0x01&a
    

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

while True:
    curtime = time.time() #HID data limit 64kB/s, assume writing 8 byte reports to device, no point writing too many: max 8k writes/s
    poll()
    while time.time()-curtime < 0.000125:
        time.sleep(0.00002)
    write_rep(organise(num_axes,axis_size,num_buttons,button_size,num_2pos,tupos_size,num_hats,hat_size))
        
