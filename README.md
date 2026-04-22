# ESP32-MQTT-OptomaProjector
Connect any Optoma projector with RS232 port to smarthome via MQTT on a ESP32 with micropython

![logo](https://github.com/GoHoHa/ESP32-MQTT-OptomaProjector/blob/main/images/optoma-esp32.png)

## Features

The MicroPython script enables to connect an Optoma Projector with RS232 interface to a smarthome by MQTT messages.
So far it transmits **power ON** and **OFF** command and can make use of the **text notification** option.
It polls the status and current **lamp age**.

After startup, the ESP32 publishes its IP address via MQTT.
Opening this IP in your browser will bring up a dashboard featuring status information, device controls, and a log of recent communications.

![Screen shot homepage](https://github.com/GoHoHa/ESP32-MQTT-OptomaProjector/blob/main/images/homepage.jpg "Screen shot homepage")

It uses asyncio and [Peter Hinchs Asynchronous MQTT](https://github.com/peterhinch/micropython-mqtt) implementation, it also tries to get correct time from [NTP](https://en.wikipedia.org/wiki/Network_Time_Protocol) server. I think the code is clean an easy to understand. Feel free to add more commands as needed or reuse the code for any other serial communication hardware (e.g. gas boiler). 

## Hardware

You need:
- a Optoma projector with a RS232 connector (I have a [OPTOMA HD25e](https://www.optoma.de/uploads/manuals/HD25e-M-de.pdf))
- a USB power supply
- any ESP32 board (I used a ESP32-C3-SuperMini)
- an MAX3232 breakout board with a female D-sub9 connector, like [this](https://de.aliexpress.com/item/4000055222836.html)

Connect MAX3232's TX and RX with two free GPIO for UART connection, connect 3V3 from ESP32 to MAX3232 VCC:

![schematics](https://github.com/GoHoHa/ESP32-MQTT-OptomaProjector/blob/main/images/schematics.png "schematic")

All fits in a machtbox sized housing, like this:

![esp32 rs232 bridge in safran case](https://github.com/GoHoHa/ESP32-MQTT-OptomaProjector/blob/main/images/hardware.jpg "esp32 rs232 bridge in safran case :-)")


## Installation

1. Install actual [MicroPython firmware](https://micropython.org/download/) to your ESP32 board
2. Edit the variables in `cfg.py` to match your network (SSID, Password, MQTT-Broker ...)
3. You can also edit the mqtt topics in the configuiration file to fit your smarthome setup (e.g. [OpenHAB](https://openhab.org/))
4. Copy `cfg.py`, `main.py`, `mqtt_as.py` and `index.html` to your ESP (e.g. using [Thonny](https://thonny.org/))
5. Attach hardware to projector and power it up
