# 6DoF Flight Dynamics System - Complete Setup Manual

## Table of Contents
1. [System Overview](#system-overview)
2. [Hardware Requirements](#hardware-requirements)
3. [ESP32 Client Setup](#esp32-client-setup)
4. [ESP8266 Server Setup](#esp8266-server-setup)
5. [Network Configuration](#network-configuration)
6. [Node-RED Integration](#node-red-integration)
7. [Protocols & Communication](#protocols--communication)
8. [Troubleshooting](#troubleshooting)
9. [Testing & Validation](#testing--validation)

---

## System Overview

This system consists of three main components:

- **ESP32 (Flight Computer)**: Runs 6DoF physics simulation, calculates flight dynamics, sends telemetry via UDP
- **ESP8266 (Telemetry Display)**: Receives UDP telemetry packets, parses JSON data, displays on OLED screen
- **Node-RED (Control Hub)**: Acts as a middleware for data logging, visualization, protocol conversion, and advanced control

### Architecture Diagram
```
ESP32 (6DoF Physics)
    ↓ UDP JSON Telemetry (Port 1234)
    ↓
ESP8266 (Telemetry Server)
    ↓ Display on OLED
    
Node-RED (Parallel Connection)
    ↓ Listens on UDP Port 1234
    ↓ Processes, logs, visualizes data
```

---

## Hardware Requirements

### ESP32 Setup
- ESP32 Development Board
- USB-C Cable (programming)
- WiFi connection (2.4GHz band)
- Optional: IMU sensor (MPU6050/BNO055) for real sensor data

### ESP8266 Setup
- ESP8266 Development Board (NodeMCU or Wemos D1 Mini recommended)
- USB Micro Cable (programming)
- SSD1306 OLED Display (128x64, I2C)
  - SDA → GPIO 4 (D2)
  - SCL → GPIO 5 (D1)
  - GND → GND
  - VCC → 3.3V
- WiFi connection (2.4GHz band)

### Node-RED Setup
- Computer running Linux, macOS, or Windows
- Node-RED installed (`npm install -g node-red`)
- Node-RED running on localhost:1880

---

## ESP32 Client Setup

### Step 1: Install Arduino IDE & Boards
1. Download Arduino IDE 2.x from arduino.cc
2. Open Arduino IDE → Preferences
3. Add to "Additional Boards Manager URLs":
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Tools → Board Manager → Search "esp32" → Install latest version

### Step 2: Install Required Libraries
In Arduino IDE, go to Sketch → Include Library → Manage Libraries:
- Search and install:
  - `AsyncUDP` by Hristo Gochkov
  - `ArduinoJSON` by Benoit Blanchon
  - `WiFi` (built-in)

### Step 3: Configure WiFi Credentials
In the ESP32 sketch, update these lines:
```cpp
const char *ssid = "TheOracle";
const char *password = "D0y0usp3AK0R4CL353";
```
Replace with your actual WiFi SSID and password.

### Step 4: Configure UDP Server Address
Update the server IP address (currently set to ESP8266):
```cpp
if (udp.connect(IPAddress(192, 168, 1, 100), 1234)) {
```
Replace `192.168.1.100` with your ESP8266's actual local IP address.

### Step 5: Program the ESP32
1. Connect ESP32 via USB-C cable
2. Tools → Board → Select "ESP32 Dev Module"
3. Tools → Port → Select your COM port
4. Click Upload (→ button)
5. Open Serial Monitor (Ctrl+Shift+M, 115200 baud)
6. Verify output shows "UDP connected"

### Step 6: Verify Operation
In Serial Monitor, you should see:
```
Starting ESP32 6DoF UDP Client...
Connecting to WiFi.....
WiFi connected
ESP32 IP: 192.168.1.xxx
UDP connected to server
Telemetry sent: {"pos_x":0.0,"pos_y":0.0,...}
```

---

## ESP8266 Server Setup

### Step 1: Install Arduino IDE for ESP8266
1. Arduino IDE → Preferences → Additional Boards Manager URLs
2. Add:
   ```
   http://arduino.esp8266.com/stable/package_esp8266com_index.json
   ```
3. Tools → Board Manager → Search "esp8266" → Install latest

### Step 2: Install Required Libraries
Same libraries as ESP32:
- `AsyncUDP`
- `ArduinoJSON`
- `Adafruit_SSD1306`
- `Adafruit_GFX`

### Step 3: Configure I2C for OLED
The OLED display communicates via I2C:
- Default ESP8266 I2C pins: SDA=GPIO4 (D2), SCL=GPIO5 (D1)
- Display address: `0x3D` (verify with I2C scanner if needed)

### Step 4: Configure WiFi Credentials
Update the same WiFi credentials as ESP32:
```cpp
const char *ssid = "TheOracle";
const char *password = "D0y0usp3AK0R4CL353";
```

### Step 5: Program the ESP8266
1. Connect ESP8266 via USB Micro cable
2. Tools → Board → Select "NodeMCU 1.0 (ESP-12E Module)" (or your variant)
3. Tools → Port → Select your COM port
4. Click Upload
5. Open Serial Monitor (115200 baud)

### Step 6: Verify OLED Display
The OLED should show:
1. "Initializing..."
2. "WiFi Connected" + IP address
3. "Waiting for data..."
4. Once ESP32 starts sending: cycling telemetry pages

---

## Network Configuration

### Step 1: Find Your Network
1. Determine your WiFi router's IP (typically 192.168.1.1)
2. Access router admin panel → Connected Devices
3. Note the IPs assigned to ESP32 and ESP8266

### Step 2: Static IP Assignment (Recommended)
To avoid IP changes on reboot:

#### Option A: Router DHCP Reservation
1. Log into router (192.168.1.1)
2. DHCP Settings → Reserved IPs
3. Reserve:
   - `192.168.1.99` for ESP32
   - `192.168.1.100` for ESP8266

#### Option B: Hardcode IPs in Sketch
Update ESP32 code:
```cpp
// Instead of WiFi.begin()
WiFi.config(
  IPAddress(192, 168, 1, 99),      // Static IP
  IPAddress(192, 168, 1, 1),       // Gateway
  IPAddress(255, 255, 255, 0),     // Subnet
  IPAddress(8, 8, 8, 8),           // DNS
  IPAddress(8, 8, 4, 4)            // DNS2
);
WiFi.begin(ssid, password);
```

### Step 3: Verify Network Connectivity
1. **From ESP32 Serial Monitor**: Should show successful WiFi connection
2. **From ESP8266 Serial Monitor**: Should show "UDP Listening on IP: 192.168.1.100"
3. **Ping test** (from computer):
   ```bash
   ping 192.168.1.99    # ESP32
   ping 192.168.1.100   # ESP8266
   ```

---

## Node-RED Integration

### Step 1: Install Node-RED
```bash
# On Windows/Mac/Linux
npm install -g node-red

# Start Node-RED
node-red

# Access at: http://localhost:1880
```

### Step 2: Find Your Computer's IP
```bash
# Windows (Command Prompt)
ipconfig

# Mac/Linux (Terminal)
ifconfig
```
Look for your local IP (typically 192.168.1.xxx). Let's assume it's `192.168.1.50`.

### Step 3: Create Node-RED UDP Listener

1. Open http://localhost:1880 in browser
2. From the left panel, drag these nodes:
   - **Input** → `UDP in` (UDP network input)
   - **Output** → `debug` (for viewing messages)
   - **Output** → `file` (for logging)

3. **Configure UDP in node:**
   - Double-click "UDP in"
   - Protocol: UDP4
   - Port: 1234 (same as ESP devices)
   - Click Done

4. **Connect nodes:**
   - UDP in → debug (connect dot on right to debug input dot)
   - UDP in → file (connect for data logging)

5. **Configure file node:**
   - File: `/tmp/telemetry_log.txt` (or choose location)
   - Append to file: Checked
   - Format: JSON (each line is JSON)

6. Click **Deploy** (top-right red button)

7. **Open Debug panel** (right sidebar, bug icon) to see incoming messages

### Step 4: Parse JSON Telemetry

1. Drag **Function** node from left panel
2. Place between UDP in and debug
3. Double-click and enter:
```javascript
// Parse the UDP payload as JSON
var data = JSON.parse(msg.payload.toString());

msg.payload = {
    altitude: data.pos_z,
    airspeed: data.airspeed,
    throttle: (data.throttle * 100).toFixed(1),
    fuel: data.fuel_mass.toFixed(2),
    pitch: data.q_x,
    roll: data.q_y,
    yaw: data.q_z,
    timestamp: new Date().toLocaleTimeString()
};

return msg;
```

4. Click Done and Deploy

### Step 5: Create Dashboard Display

1. Install dashboard: 
   - Menu (top-left) → Manage palette → Install
   - Search: `node-red-dashboard`
   - Install and restart Node-RED

2. Drag these nodes:
   - **Dashboard** → `gauge` (for altitude)
   - **Dashboard** → `gauge` (for airspeed)
   - **Dashboard** → `chart` (for altitude over time)
   - **Dashboard** → `text` (for throttle percentage)

3. **Configure gauge for altitude:**
   - Double-click gauge
   - Label: "Altitude"
   - Group: Create new group "Flight Data"
   - Min: 0, Max: 1000
   - Units: "m"
   - Color gradient: 0=green, 100=red

4. **Configure second gauge for airspeed:**
   - Label: "Airspeed"
   - Same group
   - Min: 0, Max: 100
   - Units: "m/s"

5. **Connect your function node to all dashboard nodes:**
   - Function → Gauge (altitude) input
   - Function → Gauge (airspeed) input
   - Function → Chart input
   - Function → Text input

6. Deploy and access dashboard at: http://localhost:1880/ui

---

## Protocols & Communication

### UDP Protocol Specification

**Port:** 1234 (UDP)
**Direction:** ESP32 → ESP8266 (and Node-RED if listening)
**Frequency:** 100 ms (10 Hz)
**Format:** JSON

### Telemetry Packet Format

```json
{
  "pos_x": 0.125,          // Position X (meters)
  "pos_y": -0.042,         // Position Y (meters)
  "pos_z": 45.3,           // Position Z / Altitude (meters)
  
  "vel_x": 2.14,           // Velocity X (m/s)
  "vel_y": -0.08,          // Velocity Y (m/s)
  "vel_z": -1.23,          // Velocity Z (m/s)
  "airspeed": 45.8,        // Total airspeed magnitude (m/s)
  
  "q_w": 0.9999,           // Quaternion W component
  "q_x": 0.0042,           // Quaternion X component (pitch)
  "q_y": -0.0031,          // Quaternion Y component (roll)
  "q_z": 0.0015,           // Quaternion Z component (yaw)
  
  "thrust": 15000.0,       // Current thrust (Newtons)
  "fuel_flow": 1.25,       // Fuel consumption rate (kg/s)
  "throttle": 0.3,         // Throttle setting [0.0-1.0]
  
  "fuel_mass": 48.75,      // Remaining fuel (kg)
  "total_mass": 670.0,     // Total aircraft mass (kg)
  
  "altitude": 45.3,        // Altitude (meters)
  "air_density": 1.225     // Air density (kg/m³)
}
```

### ESP8266 Acknowledgment (Optional)

ESP8266 sends back:
```
Got [n] bytes of data
```
This confirms receipt but isn't critical for operation.

### Network Firewall Rules

For Node-RED on separate computer:

1. **Windows Firewall:**
   - Settings → Firewall & Network Protection
   - Allow app through firewall → Node.js/npm
   - Enable on Private networks

2. **macOS:**
   ```bash
   # Allow port 1234 UDP
   sudo pfctl -f /etc/pf.conf
   ```

3. **Linux (UFW):**
   ```bash
   sudo ufw allow 1234/udp
   ```

---

## Troubleshooting

### ESP32 Won't Connect to WiFi
**Symptom:** Serial output shows "WiFi Failed"
**Solutions:**
1. Verify SSID and password (case-sensitive)
2. Ensure you're using 2.4GHz band (5GHz not supported)
3. Check router isn't MAC-filtering
4. Restart both ESP32 and router

### ESP8266 Doesn't Receive Data
**Symptom:** OLED shows "Waiting for data..." indefinitely
**Solutions:**
1. Verify IP addresses match ESP32 code:
   ```cpp
   if (udp.connect(IPAddress(192, 168, 1, 100), 1234)) {
   ```
2. Check both devices on same WiFi network:
   ```
   ESP32 Serial: "WiFi connected"
   ESP8266 Serial: "UDP Listening on IP: 192.168.1.100"
   ```
3. Disable firewall temporarily to test
4. Restart both devices

### OLED Display Shows Nothing
**Symptom:** OLED blank
**Solutions:**
1. Check I2C wiring (SDA=D2/GPIO4, SCL=D1/GPIO5)
2. Verify display address with I2C scanner sketch
3. Check power (3.3V on VCC, not 5V)
4. Try display example from Adafruit library

### Node-RED Not Receiving UDP
**Symptom:** Debug pane shows no messages
**Solutions:**
1. Verify port 1234 listening:
   ```bash
   # Windows
   netstat -ano | findstr :1234
   
   # Mac/Linux
   lsof -i :1234
   ```
2. Check firewall allows port 1234
3. Verify computer's local IP address (not 127.0.0.1)
4. ESP devices must be able to reach computer's IP

### Telemetry Data Missing Fields
**Symptom:** Node-RED shows undefined fields
**Solutions:**
1. Update ESP32 to latest version
2. Check JSON function in Node-RED parses correctly
3. Verify telemetry packet contains all expected fields in debug panel

---

## Testing & Validation

### Phase 1: Hardware Validation (No Network)

1. **Program each device independently**
   - ESP32: Upload, check Serial Monitor
   - ESP8266: Upload, check Serial Monitor & OLED

2. **Verify on-device systems work**
   - ESP32: Physics engine running, generating data
   - ESP8266: OLED displaying test patterns

### Phase 2: Network Connection

1. **Bring devices online:**
   ```
   ESP32 Serial: "WiFi connected" + IP shown
   ESP8266 Serial: "UDP Listening" + IP shown
   ```

2. **Test connectivity:**
   - Ping each device from computer
   - Check router's connected devices list

3. **Monitor ESP8266 OLED:**
   - Should transition from "Waiting for data..." to showing telemetry pages
   - Pages should cycle every ~200ms

### Phase 3: Node-RED Integration

1. **Start Node-RED:**
   ```bash
   node-red
   # Should show: "Node-RED running at http://localhost:1880"
   ```

2. **Create basic UDP listener:**
   - Deploy UDP in → debug flow
   - Check debug panel for incoming packets

3. **Validate JSON parsing:**
   - Add function node
   - Check parsed values in debug panel

4. **Access dashboard:**
   - Open http://localhost:1880/ui
   - Verify gauges update in real-time

### Phase 4: Full System Test

**Checklist:**
- [ ] ESP32 Serial shows "Telemetry sent" messages
- [ ] ESP8266 OLED cycling through flight data pages
- [ ] Node-RED debug panel showing JSON messages
- [ ] Dashboard gauges updating smoothly
- [ ] Telemetry log file growing (`/tmp/telemetry_log.txt`)
- [ ] All IP addresses stable (no disconnects)

### Example Test Commands

**Check ESP32 is sending:**
```bash
# Run from computer on same network
tcpdump -i any udp port 1234 -v
# Should show packets from ESP32 IP to UDP port 1234
```

**Verify JSON validity:**
```bash
# Check Node-RED telemetry log
cat /tmp/telemetry_log.txt | head -1
# Should show valid JSON
```

---

## Performance Tuning

### Reduce Telemetry Rate
If network is saturated:
```cpp
// In ESP32, change from 100ms to 200ms
const unsigned long TELEMETRY_INTERVAL = 200;
```

### Increase Physics Accuracy
For more realistic dynamics:
```cpp
// Change Euler to Runge-Kutta integration (advanced)
// Replace quaternionUpdateEuler with RK4 method
```

### Adjust OLED Update Frequency
If display flickers:
```cpp
// In ESP8266, increase from 200ms to 500ms
const unsigned long DISPLAY_UPDATE_INTERVAL = 500;
```

---

## Advanced: Custom Control via Node-RED

To send control commands from Node-RED back to ESP32:

1. In Node-RED, add `UDP out` node
2. Configure with ESP32 IP (192.168.1.99) and port 1234
3. Create control message format:
```javascript
msg.payload = JSON.stringify({
  "command": "throttle",
  "value": 0.5
});
```
4. Update ESP32 to parse incoming commands in UDP receive callback

---

## System Maintenance

### Weekly
- Check for loose connections on OLED display
- Verify both devices still have stable IPs
- Monitor temperature of microcontrollers

### Monthly
- Update Node-RED packages: `npm update -g node-red`
- Check telemetry log file size (archive if >100MB)
- Review and optimize Node-RED flows for efficiency

### Quarterly
- Update Arduino IDE boards/libraries
- Review WiFi security (change password if needed)
- Test recovery from power loss

---

## Quick Reference

| Component | IP | Port | Protocol |
|-----------|----|----|----------|
| ESP32 | 192.168.1.99 | 1234 | UDP |
| ESP8266 | 192.168.1.100 | 1234 | UDP |
| Node-RED | 192.168.1.50 | 1880 | TCP (HTTP) |

| File | Purpose |
|------|---------|
| ESP32ASYNCUDPCLIENT.ino | Flight dynamics client |
| ESP8266ASYNCUDPSERVER.ino | Telemetry display server |
| sixDoF.c | Physics engine (included in ESP32) |
| /tmp/telemetry_log.txt | Node-RED data log |

---

## Support & Next Steps

### To Debug Issues:
1. Always check **Serial Monitor** output first
2. Verify **IP addresses** and **port 1234**
3. Check **firewall** and **WiFi password**
4. Restart both devices and try again

### To Extend System:
- Add real sensor inputs (IMU for actual flight data)
- Create advanced Node-RED dashboards
- Implement closed-loop autopilot control
- Add data recording/playback capability
- Integrate with flight simulator (FlightGear/X-Plane)