"""
RS232-MQTT-Bridge for Optoma HD25 Projector
(C) Jürgen Gluch, 2026
versions:
10.04.2026 - rebuild from begining based on mqtt_as example
"""
VERSION_DATE = "10.04.2026 a"

import sys
import gc
import machine
from mqtt_as import MQTTClient, config
import uasyncio as asyncio
import ubinascii
import json
import time
import network
from machine import UART, Pin, WDT
import ntptime
import socket

# ========== Load Configuration ==========
try:
    import cfg
except Exception as e:
    log_event("SYST", f"Exit. Config load failed: {e}")
    sys.exit() # machine.reset()

# Local configuration
config['ssid'] = cfg.WIFI_SSID
config['wifi_pw'] = cfg.WIFI_PASS
config['server'] = cfg.MQTT_BROKER
config['port'] = cfg.MQTT_PORT
config['user'] = cfg.MQTT_USER
config['password'] = cfg.MQTT_PASS
config['client_id'] = cfg.MQTT_CLIENT
config['keepalive'] = 60
config['queue_len'] = 1

cmd_log = [] # last command log
cmd_queue = []
mqtt_client = None
uart = None
projector_state = "unknown"   # "on" / "off" / "unknown"
lamp_hours = None

# ========== Time and Logger ==========
async def ntp_sync():
    while True:
        log_event("SYS", "Scheduled NTP sync")
        for _ in range(3):
            try:
                ntptime.host = cfg.NTP_SERVER
                ntptime.settime()
                log_event("SYST", f"NTP synced, local time: {format_time(time.time())}")
                return True
            except Exception as e:
                log_event("SYST", f"NTP error: {e}")
                await asyncio.sleep(5)
        await asyncio.sleep(86400)  # 24 hours

def is_dst_germany(ts):
    dt = time.localtime(ts) 
    year, month, day, hour = dt[0], dt[1], dt[2], dt[3]
    if month < 3 or month > 10: return False
    if month > 3 and month < 10: return True
    last_sunday = day + (6 - time.mktime((year, month, 1, 0, 0, 0, 0, 0)) // 86400 % 7) + 1
    if month == 3: return day >= last_sunday and hour >= 2
    if month == 10: return day < last_sunday or (day == last_sunday and hour < 3)
    return False

def format_time(ts):  # get_local_time_str
    offset = 0 if is_dst_germany(ts) else 3600
    ts += offset
    tm = time.localtime(ts)
    return "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(*tm[:6])

def log_event(direction, data):
    ts = int(time.time())
    cmd_log.append((ts, direction, data.strip()))
    print(f"{format_time(ts)} {direction}: {data.strip()}")
    if len(cmd_log) > cfg.MAX_LOG_ENTRIES:
        cmd_log.pop(0)

boot_time_monotonic = time.ticks_ms()
def uptime_hms():
    seconds = time.ticks_diff(time.ticks_ms(), boot_time_monotonic) // 1000
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}:{m:02d}:{s:02d}"

# ========== Watchdog ==========
async def watchdog():
    wdt = WDT(timeout=120000)  # 2 min
    while True:
        wdt.feed()
        await asyncio.sleep(60)

# ========== WIFI Connection and MQTT ==========
# Respond to incoming messages
async def messages(client):
    async for topic, msg, retained in client.queue:
        # print(topic.decode(), msg.decode(), retained)
        log_event("MQTT", f"{topic.decode()} : {msg.decode()}") 
        if topic == cfg.MQTT_DEVICE+cfg.TOPIC_CMD_POWER:
            if msg in (b"ON", b"1"):
                enqueue(cfg.CMD_PWR_ON)
            elif msg in (b"OFF", b"0"):
                enqueue(cfg.CMD_PWR_OFF)
        elif topic == cfg.MQTT_DEVICE+cfg.TOPIC_CMD_MSG:
            enqueue(cmd_msg(msg.decode()))

# Respond to connectivity being (re)established
async def up(client):  
    while True:
        await client.up.wait()  # Wait on an Event
        client.up.clear()
        # renew subscriptions
        await client.subscribe(cfg.MQTT_DEVICE+cfg.TOPIC_CMD_POWER, 1)
        await client.subscribe(cfg.MQTT_DEVICE+cfg.TOPIC_CMD_MSG, 1)
        log_event("MQTT", f"Connencted to {cfg.WIFI_SSID} and broker {cfg.MQTT_BROKER}")

# ========== Projector UART ==========
uart = UART(1, baudrate=cfg.UART_BAUD, tx=cfg.UART_TX, rx=cfg.UART_RX, timeout=100)

def enqueue(cmd):
    if len(cmd_queue) < 20:
        #log_event("U_TX", f"{cmd.strip()}")
        cmd_queue.append(cmd)
    else:
        log_event("CMD ", f"QUEUE FULL")

async def rs232_writer():
    while True:
        if cmd_queue:
            cmd = cmd_queue.pop(0)
            try:
                uart.write(cmd)
                log_event("U_TX", f"{cmd.strip()}")
                await asyncio.sleep_ms(200) # Give projector time to process
            except Exception as e:
                log_event("UART", f"write error: {e}")
        else:
            await asyncio.sleep_ms(20)

async def rs232_reader():
    global projector_state, lamp_hours
    buf = b""
    while True:
        n = uart.any()
        if n and n > 0:
            try:
                data = uart.read(n)
            except Exception as e:
                log_event("UART", f"read error: {e}")
                data = None

        #if n and n > 0:
        #    try:
        #        data = await asyncio.wait_for(uart.read(n), timeout=0.5)
        #    except asyncio.TimeoutError:
        #        continue

            if data:
                buf += data  # accumulate
                # process all complete lines
                while b"\r" in buf:
                    line_bytes, buf = buf.split(b"\r", 1)
                    line = line_bytes.decode('utf-8', 'ignore').strip("\r\n")
                    log_event("U_RX", f"{line}")

                    if client:
                        await client.publish(cfg.MQTT_DEVICE+cfg.TOPIC_STATE_RAW, line)

                    # INFO1 = remote ON
                    if line.startswith("INFO"):
                        try:
                            n = line[4]
                            if n == "0":
                                projector_state = "off"
                            elif n == "1":
                                projector_state = "on"
                                enqueue(cfg.CMD_LAMP)
                            elif n == "2":
                                projector_state = "Cooling"
                            elif n == "3":
                                projector_state = "Out of range"
                            elif n == "4":
                                projector_state = "Lamp fail"
                            elif n == "6":
                                projector_state = "Fan lock"
                            elif n == "7":
                                projector_state = "Over temperature"
                            elif n == "8":
                                projector_state = "Lamp near EOL"
                            else:
                                projector_state = "unknown "+n
                            if client:
                                await client.publish(cfg.MQTT_DEVICE+cfg.TOPIC_STATE_POWER, projector_state.upper())
                            log_event("HD25", f"INFO:{projector_state}")
                        except Exception as e:
                            log_event("UART", f"RS232 parse error: {e}")
                                
                    # OK lamp response
                    if line.startswith("OK") and len(line) >= 10:
                        try:
                            a = line[2]
                            bbbb = line[3:7]
                            if a == "0":
                                projector_state = "off"
                                #lamp_hours = None
                                if client:
                                    await client.publish(cfg.MQTT_DEVICE+cfg.TOPIC_STATE_POWER, "OFF")
                            elif a == "1":
                                projector_state = "on"
                                lamp_hours = int(bbbb)
                                if client:
                                    await client.publish(cfg.MQTT_DEVICE+cfg.TOPIC_STATE_POWER, "ON")
                                    await client.publish(cfg.MQTT_DEVICE+cfg.TOPIC_STATE_LAMP, str(lamp_hours))
                            else:
                                projector_state = "unknown"
                            log_event("HD25", f"{projector_state}, LAMP: {lamp_hours}h")
                        except Exception as e:
                            log_event("UART", f"RS232 parse error: {e}")
        await asyncio.sleep_ms(50)  # small delay to allow more bytes to arrive
        
async def poll_status():
    while True:
        log_event("UART", "Polling projector status...")
        enqueue(cfg.CMD_STATUS)
        await asyncio.sleep(cfg.POLLING_PAUSE)        

def cmd_msg(txt):
    txt = txt[:30]  # crop to 30 characters
    return cfg.CMD_MESSAGE + "{}\r".format(txt)

# ========== Web Server ==========
def urldecode(s):
    """Decode URL-encoded characters (e.g., %20 -> space)"""
    s = s.replace("+", " ")
    parts = s.split("%")
    out = parts[0]
    for p in parts[1:]:
        if len(p) >= 2:
            try:
                c = chr(int(p[:2], 16))
                out += c + p[2:]
            except:
                out += "%" + p
        else:
            out += "%" + p
    return out

def build_html():
    try:
        with open("index.html", "r") as f:
            html = f.read()
    except:
        return "HTML build: File error"
    ip = network.WLAN(network.STA_IF).ifconfig()[0]
    state_class = projector_state  # "on/off/unknown"
    html = html.replace("%IP%", ip)
    html = html.replace("%UPTIME%", uptime_hms())
    html = html.replace("%STATE%", projector_state.upper())
    html = html.replace("%STATE_CLASS%", state_class)
    html = html.replace("%LAMP%", str(lamp_hours or "-"))
    html = html.replace("%VERSION%", VERSION_DATE)
    return html

async def http_server():
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(addr)
        s.listen(2)
    except OSError as e:
        log_event("HTTP", f"Socket bind error: {e}")
        s.close()
        await asyncio.sleep(1)
    s.setblocking(True)
    log_event("HTTP", f"Server running on http://{network.WLAN(network.STA_IF).ifconfig()[0]}:80")
    while True:
        try:
            client_sock, client_addr = s.accept()
            client_sock.settimeout(5.0)  # Timeout after 5 seconds
            #print("HTTP connection from", client_addr)
            req = client_sock.recv(1024)
            if b"GET /data" in req:
                import ujson
                data = ujson.dumps(build_json())
                response = b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n" + data.encode()
            elif b"GET /cmd?power=ON" in req:
                enqueue(cfg.CMD_PWR_ON)
            elif b"GET /cmd?power=OFF" in req:
                enqueue(cfg.CMD_PWR_OFF)
            elif b"GET /cmd?msg=" in req:
                msg = req.decode().split("msg=")[1].split(" ")[0]
                msg = urldecode(msg)  # Decode URL-encoded characters
                enqueue(cmd_msg(msg))
                response = b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\nOK"
            else:
                html = build_html()
                response = b"HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n" + html.encode()
            client_sock.sendall(response)
        except Exception as e:
            log_event("HTTP", f" server error: {e}")
        finally:
            client_sock.close()
        await asyncio.sleep_ms(50)

def build_json():
    rows = []
    for ts, direction, cmd in reversed(cmd_log):
        rows.append({
            "time": format_time(ts),
            "dir": direction,
            "data": cmd
        })
    return {
        "ip": network.WLAN(network.STA_IF).ifconfig()[0],
        "uptime": uptime_hms(),
        "state": projector_state,
        "lamp": lamp_hours,
        "log": rows
    }

# ========== Main ==========
async def main(client):
    #asyncio.create_task(watchdog())
    
    # connect to WLAN and MQTT
    await client.connect()
    for coroutine in (up, messages):
        asyncio.create_task(coroutine(client))
    
    await asyncio.sleep(5)
    # start communicatio with projector
    asyncio.create_task(rs232_writer())
    asyncio.create_task(rs232_reader())
    asyncio.create_task(poll_status())
    
    # start web server
    asyncio.create_task(http_server())
    
    # run main loop
    while True:
        await asyncio.sleep(120)
        # If WiFi is down the following will pause for the duration.
        gc.collect()
        log_event("SYST", f"Uptime: {uptime_hms()}, free memory {gc.mem_free()} byte")
        await client.publish(cfg.MQTT_DEVICE+cfg.TOPIC_STATE_ESP, f"Uptime: {uptime_hms()}, free memory {gc.mem_free()}", qos = 1)


config["queue_len"] = 1  # Use event interface with default queue size
MQTTClient.DEBUG = False  # Optional: print diagnostic messages
client = MQTTClient(config)
try:
    asyncio.run(main(client))
except Exception as e:
    log_event("SYST", f"Fatal error: {e}, resetting in 10s")
    time.sleep(10)
    #sys.exit()
    machine.reset()
finally:
    client.close()  # Prevent LmacRxBlk:1 errors


