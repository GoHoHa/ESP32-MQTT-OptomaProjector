# This file contains all configurable variables

WIFI_SSID = "mySSID"
WIFI_PASS = "myPassword"
WIFI_DHCP = "ESP32-projector"

MQTT_BROKER = "192.168.1.XX"
MQTT_PORT   = 1883
MQTT_USER   = "mqttuser"
MQTT_PASS   = "mqttpassword"
MQTT_CLIENT = "esp32_projector"

MQTT_DEVICE = b"projector"
TOPIC_CMD_POWER   = b"/cmd/power"
TOPIC_CMD_MSG     = b"/cmd/message"
TOPIC_STATE_ESP   = b"/state/esp"
TOPIC_STATE_POWER = b"/state/power"
TOPIC_STATE_LAMP  = b"/state/lamp_hours"
TOPIC_STATE_RAW   = b"/state/raw"

# UART
# ESP32 with SPIRAM, the default pins for UART1 are tx=5 and rx=4
UART_TX = 21 
UART_RX = 20 
UART_BAUD = 9600

# Optoma commands
CMD_PWR_ON    = "~0000 1\r"    # returns INFO1
CMD_PWR_OFF   = "~0000 0\r"    # returns INFO2, later INFO0
CMD_LAMP      = "~00108 1\r"   # only works when PWR=ON, returns hours as OKbbbb
CMD_PWR_QUERY = "~00124 1\r"   # returns OKa a=0 OFF or a=1 ON
CMD_STATUS    = "~00150 1\r"   # unified poll command, returns OKabbbbccdddde 
CMD_MESSAGE   = "~00210 "      # display message on the OSD n: 1-30 characters

NTP_SERVER = "ptbtime1.ptb.de"

POLLING_PAUSE = 300 # seconds, normal 5 min  
WDT_TIMEOUT = 60000
MAX_LOG_ENTRIES = 20
