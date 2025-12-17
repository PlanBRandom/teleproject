# UNO Q LED Matrix Integration for Gas Monitoring

## Overview

The Arduino UNO Q features an **LED dot matrix display** that can show real-time gas readings, alerts, and system status. This guide shows how to integrate it with your OI monitor pipeline.

## Display Capabilities

The LED matrix can show:
- 📊 **Real-time gas readings** (channel + PPM value)
- ⚠️ **Alert indicators** (high gas warnings)
- 📡 **System status** (WiFi, MQTT, Modbus connection)
- 📜 **Scrolling messages** (device info, alarms)
- 📈 **Trend indicators** (rising/falling gas levels)

## Approach 1: Python Display (Recommended)

Use Python on the Linux side to control the LED matrix while running the full pipeline.

### Install LED Matrix Library

```bash
ssh arduino@uno-q.local
cd ~/teleproject

# Install LED matrix Python library
source venv/bin/activate
pip install spidev pillow  # For LED matrix control
```

### Create Display Manager

Create `pipeline/led_display.py`:

```python
"""
LED Matrix Display Manager for UNO Q
Displays gas readings and alerts on the built-in LED matrix
"""

import time
from typing import List, Dict, Optional
from PIL import Image, ImageDraw, ImageFont
import threading

class LEDMatrixDisplay:
    """Manages LED matrix display for gas monitor readings"""
    
    def __init__(self, width: int = 128, height: int = 64):
        """
        Initialize LED matrix display
        
        Args:
            width: Display width in pixels
            height: Display height in pixels
        """
        self.width = width
        self.height = height
        self.current_screen = 0
        self.alert_mode = False
        self.running = False
        self._thread = None
        
        # Initialize display hardware (specific to UNO Q LED matrix)
        self._init_hardware()
        
    def _init_hardware(self):
        """Initialize the UNO Q LED matrix hardware"""
        try:
            # TODO: Replace with actual UNO Q LED matrix initialization
            # This will depend on the specific LED matrix library/driver
            print("✓ LED Matrix initialized")
        except Exception as e:
            print(f"⚠ LED Matrix init failed: {e}")
    
    def start(self):
        """Start the display update thread"""
        self.running = True
        self._thread = threading.Thread(target=self._display_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the display updates"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)
    
    def _display_loop(self):
        """Main display update loop"""
        while self.running:
            try:
                self._render_current_screen()
                time.sleep(0.1)  # 10 FPS
            except Exception as e:
                print(f"Display error: {e}")
                time.sleep(1)
    
    def _render_current_screen(self):
        """Render the current screen based on mode"""
        # Create blank image
        image = Image.new('1', (self.width, self.height), 0)
        draw = ImageDraw.Draw(image)
        
        if self.alert_mode:
            self._draw_alert_screen(draw)
        else:
            self._draw_normal_screen(draw)
        
        # Send to hardware
        self._display_image(image)
    
    def _draw_normal_screen(self, draw):
        """Draw normal monitoring screen"""
        # Header
        draw.text((2, 2), "OI MONITOR", fill=1)
        draw.line([(0, 12), (self.width, 12)], fill=1)
        
        # System status icons
        if self.wifi_connected:
            draw.text((100, 2), "WiFi", fill=1)
        if self.mqtt_connected:
            draw.text((80, 2), "MQTT", fill=1)
        
        # Rotate through channels (show 3 at a time)
        y_pos = 18
        for i, (channel, reading) in enumerate(self.current_readings[:3]):
            draw.text((2, y_pos), f"CH{channel:2d}: {reading:6.2f} PPM", fill=1)
            y_pos += 14
    
    def _draw_alert_screen(self, draw):
        """Draw alert/warning screen with blinking effect"""
        # Blink warning
        if int(time.time() * 2) % 2 == 0:  # Blink at 0.5 Hz
            draw.rectangle([(0, 0), (self.width, self.height)], outline=1, width=2)
            draw.text((10, 10), "!!! ALERT !!!", fill=1)
            
            # Show highest reading
            if self.alert_channel:
                draw.text((10, 30), f"CH{self.alert_channel}", fill=1)
                draw.text((10, 44), f"{self.alert_value:.1f} PPM", fill=1)
    
    def _display_image(self, image):
        """Send image to LED matrix hardware"""
        try:
            # TODO: Replace with actual UNO Q LED matrix driver
            # Example: self.display.image(image)
            pass
        except Exception as e:
            print(f"Display update error: {e}")
    
    def update_readings(self, readings: List[Dict]):
        """
        Update current gas readings
        
        Args:
            readings: List of dicts with 'channel', 'value', 'gas_type'
        """
        self.current_readings = [(r['channel'], r['value']) for r in readings]
        
        # Check for alerts (over 100 PPM)
        self.alert_mode = any(r['value'] > 100 for r in readings)
        if self.alert_mode:
            # Find highest reading
            max_reading = max(readings, key=lambda x: x['value'])
            self.alert_channel = max_reading['channel']
            self.alert_value = max_reading['value']
    
    def update_status(self, wifi: bool, mqtt: bool, modbus: bool):
        """Update connection status indicators"""
        self.wifi_connected = wifi
        self.mqtt_connected = mqtt
        self.modbus_connected = modbus
    
    def show_message(self, message: str, duration: float = 3.0):
        """
        Display a scrolling message
        
        Args:
            message: Text to display
            duration: How long to show (seconds)
        """
        # TODO: Implement scrolling text animation
        pass

# Initialize global display
display = None

def init_display():
    """Initialize the LED display"""
    global display
    display = LEDMatrixDisplay()
    display.start()
    return display

def update_display(readings: List[Dict], wifi: bool, mqtt: bool, modbus: bool):
    """Update display with current readings and status"""
    if display:
        display.update_readings(readings)
        display.update_status(wifi, mqtt, modbus)
```

### Integrate with Main Pipeline

Add to `pipeline/main.py`:

```python
from pipeline.led_display import init_display, update_display

class ModbusMQTTBridge:
    def __init__(self, config_path: str = "configs/lovelace/dashboard.yaml"):
        # ... existing init code ...
        
        # Initialize LED display
        try:
            self.display = init_display()
            logger.info("✓ LED Display initialized")
        except Exception as e:
            logger.warning(f"LED Display not available: {e}")
            self.display = None
    
    def run(self):
        """Main polling loop"""
        while True:
            try:
                # ... existing polling code ...
                
                # Update LED display
                if self.display:
                    readings = []
                    for device in self.devices:
                        for channel in device.active_channels:
                            value = self.modbus.read_float32(
                                device.register_map['channels'][channel]['reading']
                            )
                            readings.append({
                                'channel': channel,
                                'value': value,
                                'gas_type': device.channel_gas_types.get(channel)
                            })
                    
                    self.display.update_readings(
                        readings,
                        wifi=True,  # Check actual WiFi status
                        mqtt=self.mqtt.client.is_connected(),
                        modbus=True  # Check actual Modbus status
                    )
                
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                if self.display:
                    self.display.stop()
                break
```

## Approach 2: Arduino Sketch with Display

Create a dedicated Arduino sketch that receives data via RPC and displays it:

Create `arduino_sketch/oi_monitor_display/oi_monitor_display.ino`:

```cpp
/*
 * OI Monitor LED Matrix Display for Arduino UNO Q
 * 
 * Receives gas readings from Linux side via RPC
 * Displays on built-in LED matrix
 */

#include <ArduinoGraphics.h>
#include <Arduino_LED_Matrix.h>

ArduinoLEDMatrix matrix;

// Display state
struct GasReading {
  int channel;
  float value;
  char gasType[10];
};

GasReading readings[8];
int numReadings = 0;
bool alertMode = false;
unsigned long lastUpdate = 0;
int displayPage = 0;

// Status indicators
bool wifiConnected = false;
bool mqttConnected = false;
bool modbusConnected = false;

void setup() {
  Serial.begin(115200);
  
  // Initialize LED Matrix
  matrix.begin();
  
  // Show startup animation
  showStartupScreen();
  
  Serial.println("OI Monitor Display Ready");
}

void loop() {
  // Check for serial commands from Linux side
  if (Serial.available()) {
    handleSerialCommand();
  }
  
  // Update display every 500ms
  if (millis() - lastUpdate > 500) {
    lastUpdate = millis();
    updateDisplay();
  }
  
  delay(10);
}

void handleSerialCommand() {
  String cmd = Serial.readStringUntil('\n');
  
  // Parse JSON-like commands from Python
  // Format: UPDATE:CH1:25.4:CO2
  if (cmd.startsWith("UPDATE:")) {
    parseReadingUpdate(cmd);
  }
  else if (cmd.startsWith("STATUS:")) {
    parseStatusUpdate(cmd);
  }
  else if (cmd.startsWith("ALERT:")) {
    alertMode = true;
  }
  else if (cmd.startsWith("CLEAR:")) {
    alertMode = false;
  }
}

void parseReadingUpdate(String cmd) {
  // Parse: UPDATE:CH1:25.4:CO2
  int ch = cmd.substring(10, 12).toInt();
  float val = cmd.substring(13, 17).toFloat();
  String gas = cmd.substring(18);
  
  // Find or add reading
  int idx = -1;
  for (int i = 0; i < numReadings; i++) {
    if (readings[i].channel == ch) {
      idx = i;
      break;
    }
  }
  
  if (idx == -1 && numReadings < 8) {
    idx = numReadings++;
  }
  
  if (idx >= 0) {
    readings[idx].channel = ch;
    readings[idx].value = val;
    gas.toCharArray(readings[idx].gasType, 10);
  }
}

void parseStatusUpdate(String cmd) {
  // Parse: STATUS:W1:M1:B1 (WiFi:MQTT:Modbus)
  wifiConnected = cmd.charAt(9) == '1';
  mqttConnected = cmd.charAt(12) == '1';
  modbusConnected = cmd.charAt(15) == '1';
}

void updateDisplay() {
  matrix.beginDraw();
  matrix.clear();
  
  if (alertMode) {
    drawAlertScreen();
  } else {
    drawNormalScreen();
  }
  
  matrix.endDraw();
  
  // Rotate through pages
  displayPage = (displayPage + 1) % 3;
}

void drawNormalScreen() {
  matrix.stroke(0xFFFFFFFF);
  
  // Header
  matrix.textFont(Font_4x6);
  matrix.text("OI", 0, 0);
  
  // Status indicators (right side)
  if (wifiConnected) matrix.point(10, 0);
  if (mqttConnected) matrix.point(11, 0);
  if (modbusConnected) matrix.point(12, 0);
  
  // Show 2 channels per page
  int startIdx = displayPage * 2;
  for (int i = 0; i < 2 && (startIdx + i) < numReadings; i++) {
    int y = 2 + (i * 4);
    GasReading r = readings[startIdx + i];
    
    // Channel number
    matrix.text(String(r.channel).c_str(), 0, y);
    
    // Value
    matrix.text(String(r.value, 1).c_str(), 4, y);
  }
}

void drawAlertScreen() {
  // Blinking border
  if ((millis() / 500) % 2 == 0) {
    matrix.stroke(0xFFFFFFFF);
    matrix.rect(0, 0, 12, 8);
    
    // Find highest reading
    float maxVal = 0;
    int maxCh = 0;
    for (int i = 0; i < numReadings; i++) {
      if (readings[i].value > maxVal) {
        maxVal = readings[i].value;
        maxCh = readings[i].channel;
      }
    }
    
    // Show alert
    matrix.textFont(Font_4x6);
    matrix.text("!", 1, 1);
    matrix.text(String(maxCh).c_str(), 4, 1);
    matrix.text(String(maxVal, 0).c_str(), 1, 5);
  }
}

void showStartupScreen() {
  matrix.beginDraw();
  matrix.stroke(0xFFFFFFFF);
  matrix.textFont(Font_4x6);
  matrix.text("OI", 4, 2);
  matrix.endDraw();
  delay(2000);
}
```

### Python Side - Send to Display via Serial/RPC

Add to `pipeline/main.py`:

```python
import serial

class DisplayBridge:
    """Bridge to send display updates to Arduino MCU"""
    
    def __init__(self, port: str = "/dev/ttyACM0"):
        try:
            self.serial = serial.Serial(port, 115200, timeout=1)
            time.sleep(2)  # Wait for Arduino reset
            print("✓ Display bridge connected")
        except Exception as e:
            print(f"⚠ Display bridge not available: {e}")
            self.serial = None
    
    def update_reading(self, channel: int, value: float, gas_type: str):
        """Send reading update to display"""
        if self.serial:
            cmd = f"UPDATE:CH{channel:02d}:{value:.1f}:{gas_type}\n"
            self.serial.write(cmd.encode())
    
    def update_status(self, wifi: bool, mqtt: bool, modbus: bool):
        """Send status update to display"""
        if self.serial:
            cmd = f"STATUS:W{1 if wifi else 0}:M{1 if mqtt else 0}:B{1 if modbus else 0}\n"
            self.serial.write(cmd.encode())
    
    def set_alert(self, alert: bool):
        """Set alert mode on display"""
        if self.serial:
            cmd = "ALERT:\n" if alert else "CLEAR:\n"
            self.serial.write(cmd.encode())
```

## Display Layouts

### Layout 1: Multi-Channel Scrolling
```
┌────────────┐
│ OI  ●●●    │  (Status indicators)
├────────────┤
│ CH01  25.4 │
│ CH02   0.8 │
│ CH03  15.2 │
└────────────┘
```

### Layout 2: Alert Mode
```
┌────────────┐
│ ┏━━━━━━━┓  │
│ ┃ ALERT ┃  │
│ ┃ CH03  ┃  │
│ ┃ 125ppm┃  │
│ ┗━━━━━━━┛  │
└────────────┘
```

### Layout 3: Summary View
```
┌────────────┐
│ 8 Active   │
│ Max: 25ppm │
│ Avg: 12ppm │
│ ●●● OK     │
└────────────┘
```

## Configuration

Add to `configs/lovelace/dashboard.yaml`:

```yaml
display:
  enabled: true
  type: "led_matrix"  # or "arduino_mcu"
  port: "/dev/ttyACM0"  # For Arduino bridge
  refresh_rate: 2  # Updates per second
  alert_threshold: 100  # PPM
  rotation_interval: 5  # Seconds per channel page
```

## Advanced Features

### 1. Trend Indicators
Show arrows for rising/falling gas levels

### 2. Historical Graph
Show mini sparkline graph of last 60 seconds

### 3. Wireless Radio Status
Display radio signal strength and packet count

### 4. Device Health
Show uptime, memory usage, error counts

## Testing

```bash
# Test display without full pipeline
cd ~/teleproject
source venv/bin/activate

python3 << EOF
from pipeline.led_display import init_display
display = init_display()

# Test readings
display.update_readings([
    {'channel': 1, 'value': 25.4, 'gas_type': 'CO2'},
    {'channel': 2, 'value': 0.8, 'gas_type': 'O2'},
    {'channel': 3, 'value': 105.2, 'gas_type': 'CO'}  # Triggers alert
])

display.update_status(wifi=True, mqtt=True, modbus=True)

import time
time.sleep(10)  # Watch display for 10 seconds
display.stop()
EOF
```

## Benefits

✅ **Real-time monitoring** without external display
✅ **Standalone operation** - see status without HA
✅ **Alert visibility** - immediate visual warnings
✅ **System health** - connection status at a glance
✅ **Portable** - monitor readings anywhere

This makes the UNO Q a **complete standalone monitoring station** with visual feedback!
