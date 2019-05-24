# Mark's Joystick Number 1 - Research Edition development interface
# Bits of this are probably copyright Mark Bakovic and/or Bakovic Aerospace, 2019


# take a string of byte data (usually chars) and plop them in a HID report
# default Flightstick Pro joystick sends 4 bytes (1 byte per axis,
# 4 bits hat direction (only one true), 4 bits for 4 buttons (can all be true))
def write_rep(report):
    with open('/dev/hidg0', 'rb+') as fd:
        fd.write(report.encode())

nc = char(0)
