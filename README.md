# ESP32-MQTT-OptomaProjector
Connect any Optoma projector with RS232 port to smarthome via MQTT on a ESP32 with micropython

![logo](https://github.com/GoHoHa/ESP32-MQTT-OptomaProjector/raw/master/src/common/images/optoma-esp32.png)

## Features

The MicroPython script enables to connect an Optoma Projector with RS232 interface to a smarthome by MQTT messages.
So far it transmits power ON and OFF command and can make use of the text notification option.
It polls the status and current lamp age.

After starting the ESP32 published it's IP adress via MQTT.
If you open the IP in your browser you will see a homepage with status information, some controls and a log with the recent communication.

![Screen shot homepage](https://github.com/GoHoHa/ESP32-MQTT-OptomaProjector/raw/master/src/common/images/homepage.png "Screen shot homepage")

## Hardware

You need:
- a Optoma projector with a RS232 connector (I have a [OPTOMA HD25e](https://www.optoma.de/uploads/manuals/HD25e-M-de.pdf))
- a USB power supply
- any ESP32 board (I used a ESP32-C3-SuperMini)
- an MAX3232 breakout board with a female D-sub9 connector, like [this](https://de.aliexpress.com/item/4000055222836.html)

all fits in a machtbox sized housing, like this:
![esp32 rs232 bridge in safran case](https://github.com/GoHoHa/ESP32-MQTT-OptomaProjector/raw/master/src/common/images/hardware.jpg "esp32 rs232 bridge in safran case :-)")


## Installation

1. Install actual [MicroPython firmware](https://micropython.org/download/) to your ESP32 board
2. Edit the variables in `cfg.py` to match your network (SSID, Password, MQTT-Broker...)
3. You can also edit the mqtt topics in the configuiration file to fit your smarthome setup (e.g. [OpenHAB](https://openhab.org/))
4. Copy `cfg.py`, `main.py`, `mqtt_as.py` and `index.html` to your ESP (e.g. using [Thonny](https://thonny.org/))
5. Attach hardware to projector and power it up
