# MJ1
Mark's Joystick number 1

A first attempt at creating a minimally-invasive update for Thrustmaster FCLS+TQS HOTAS systems, probably easily adaptable to other 15-pin Gameport joystick and throttle systems. Based on some hard-password filler automation found at iSticktoit.net (1383, look it up!) utilising a Raspberry Pi Zero as a HID gadget (in that case a keyboard). The idea is to use GPIO to select data sources (shift registers already present in the hardware for buttons + modded-in ADCs for the 5 analogue axes) and read their data over SPI. This script(s) will do that and then prepare USB Foundation HID compliant (1.11) reports to serve to the host over the Pi's USB OTG port - hopefully thereby appearing as a well-defined USB joystick with all the right axes and button behaviours.

I may try and make the code legible and easily-adaptable enough to support simple tweaking to suit other legacy HOTAS/joystick systems, but each one will also need its own config file (MJ1_usb here) so unless you want to download the HID Descriptor Tool and basically do everything except write your own script from scratch as well as type out all the relevant hex... this probably won't be hugely useful to you. (and if you do, then you don't need any of this!).

Cheers,
-M
