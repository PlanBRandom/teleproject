/*
 * OI-7530/7010 Modbus to MQTT Bridge for Arduino UNO R4 WiFi
 * 
 * Hardware:
 *  - Arduino UNO R4 WiFi (Qualcomm QRB2210 + STM32U585)
 *  - MAX485 or similar RS485 transceiver module
 *  - Built-in WiFi for MQTT connection
 * 
 * Wiring (MAX485 to UNO R4):
 *  D2 (RX)        -> MAX485 RO (Receiver Output)
 *  D3 (TX)        -> MAX485 DI (Driver Input)
 *  D4             -> MAX485 DE and RE (Direction control, tie together)
 *  5V             -> MAX485 VCC
 *  GND            -> MAX485 GND
 *  MAX485 A       -> OI Monitor A/+ (RS485+)
 *  MAX485 B       -> OI Monitor B/- (RS485-)
 * 
 * Libraries Required (Install via Arduino Library Manager):
 *  - ModbusMaster (by Doc Walker)
 *  - ArduinoMqttClient (by Arduino)
 *  - WiFiS3 (built-in for UNO R4 WiFi)
 */

#include <WiFiS3.h>
#include <ArduinoMqttClient.h>
#include <ModbusMaster.h>

// WiFi Configuration
const char* WIFI_SSID = "YourWiFiSSID";          // Change this
const char* WIFI_PASSWORD = "YourWiFiPassword";  // Change this

// MQTT Configuration
const char* MQTT_BROKER = "192.168.1.100";       // Your Home Assistant IP
const int MQTT_PORT = 1883;
const char* MQTT_USERNAME = "homeassistant";     // Change if needed
const char* MQTT_PASSWORD = "your_mqtt_pass";    // Change this
const char* MQTT_CLIENT_ID = "arduino_oi_monitor";

// Modbus Configuration
#define MODBUS_SLAVE_ID 1        // OI-7530 slave address
#define MAX485_DE_RE 4           // Direction control pin
#define MODBUS_BAUD 9600

// Hardware Serial1 for Modbus (pins 0/1 or D0/D1)
// On UNO R4: Serial1 uses pins D0(RX) and D1(TX)
// Alternative: Use SoftwareSerial on D2/D3 if you need USB debugging
#define USE_HARDWARE_SERIAL true  // Set false to use SoftwareSerial on D2/D3

#if USE_HARDWARE_SERIAL
  #define modbusSerial Serial1
#else
  #include <SoftwareSerial.h>
  SoftwareSerial modbusSerial(2, 3); // RX, TX
#endif

// WiFi and MQTT clients
WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

// Modbus object
ModbusMaster node;

// Timing
unsigned long lastPoll = 0;
unsigned long lastMqttReconnect = 0;
const unsigned long POLL_INTERVAL = 30000;      // 30 seconds between reads
const unsigned long MQTT_RECONNECT_INTERVAL = 5000;

// Device info
const char* DEVICE_NAME = "OI-7530-1";
String baseTopic = "homeassistant/sensor/oi7530_1/";

void setup() {
  // Initialize USB Serial for debugging
  Serial.begin(115200);
  delay(2000);
  
  Serial.println(F("==========================================="));
  Serial.println(F("  OI Gas Monitor - Arduino UNO R4 WiFi"));
  Serial.println(F("===========================================\n"));
  
  // Initialize MAX485 control pin
  pinMode(MAX485_DE_RE, OUTPUT);
  digitalWrite(MAX485_DE_RE, LOW); // Start in receive mode
  
  // Initialize Modbus communication
  modbusSerial.begin(MODBUS_BAUD);
  node.begin(MODBUS_SLAVE_ID, modbusSerial);
  
  // Callbacks for RS485 direction control
  node.preTransmission(preTransmission);
  node.postTransmission(postTransmission);
  
  Serial.println(F("✓ Modbus initialized"));
  Serial.print(F("  Slave ID: "));
  Serial.println(MODBUS_SLAVE_ID);
  Serial.print(F("  Baud Rate: "));
  Serial.println(MODBUS_BAUD);
  
  // Connect to WiFi
  connectWiFi();
  
  // Connect to MQTT
  connectMQTT();
  
  Serial.println(F("\n✓ System Ready"));
  Serial.println(F("===========================================\n"));
}

void loop() {
  unsigned long currentMillis = millis();
  
  // Maintain MQTT connection
  if (!mqttClient.connected()) {
    if (currentMillis - lastMqttReconnect >= MQTT_RECONNECT_INTERVAL) {
      lastMqttReconnect = currentMillis;
      connectMQTT();
    }
  } else {
    mqttClient.poll(); // Keep MQTT alive
  }
  
  // Poll sensors at regular interval
  if (currentMillis - lastPoll >= POLL_INTERVAL) {
    lastPoll = currentMillis;
    
    Serial.println(F("\n--- Polling OI Monitor ---"));
    Serial.print(F("Free Memory: "));
    Serial.print(freeMemory());
    Serial.println(F(" bytes\n"));
    
    // Read and publish first 8 channels
    for (int ch = 1; ch <= 8; ch++) {
      readAndPublishChannel(ch);
      delay(100); // Small delay between reads
    }
    
    // Read device diagnostics
    readDiagnostics();
    
    Serial.println(F("--- Poll Complete ---\n"));
  }
  
  delay(100);
}

/**
 * Read and publish a single channel
 */
void readAndPublishChannel(int channel) {
  // Calculate register address (0x21 + (channel-1)*2 for float32)
  uint16_t regAddr = 0x21 + (channel - 1) * 2;
  
  float reading = readFloat32(regAddr);
  
  if (!isnan(reading)) {
    Serial.print(F("Channel "));
    Serial.print(channel);
    Serial.print(F(": "));
    Serial.print(reading, 2);
    Serial.println(F(" PPM"));
    
    // Publish to MQTT
    String topic = baseTopic + "ch" + String(channel) + "/state";
    String payload = String(reading, 2);
    
    if (mqttClient.connected()) {
      mqttClient.beginMessage(topic);
      mqttClient.print(payload);
      mqttClient.endMessage();
    }
  } else {
    Serial.print(F("Channel "));
    Serial.print(channel);
    Serial.println(F(": Read error"));
  }
}

/**
 * Read device diagnostics
 */
void readDiagnostics() {
  // Uptime register (example - adjust based on your register map)
  uint16_t uptimeHigh = readUint16(0x321);
  uint16_t uptimeLow = readUint16(0x322);
  
  if (uptimeHigh != 0xFFFF && uptimeLow != 0xFFFF) {
    uint32_t uptimeSeconds = ((uint32_t)uptimeHigh << 16) | uptimeLow;
    Serial.print(F("Uptime: "));
    Serial.print(uptimeSeconds / 3600);
    Serial.println(F(" hours"));
    
    // Publish to MQTT
    if (mqttClient.connected()) {
      String topic = baseTopic + "uptime/state";
      mqttClient.beginMessage(topic);
      mqttClient.print(uptimeSeconds);
      mqttClient.endMessage();
    }
  }
}

/**
 * Read 32-bit float from two consecutive Modbus registers
 */
float readFloat32(uint16_t address) {
  uint8_t result = node.readHoldingRegisters(address, 2);
  
  if (result == node.ku8MBSuccess) {
    // Combine two 16-bit registers into 32-bit float (big-endian)
    uint16_t high = node.getResponseBuffer(0);
    uint16_t low = node.getResponseBuffer(1);
    
    union {
      uint32_t i;
      float f;
    } converter;
    
    converter.i = ((uint32_t)high << 16) | low;
    return converter.f;
  }
  
  return NAN;
}

/**
 * Read 16-bit unsigned integer from single register
 */
uint16_t readUint16(uint16_t address) {
  uint8_t result = node.readHoldingRegisters(address, 1);
  
  if (result == node.ku8MBSuccess) {
    return node.getResponseBuffer(0);
  }
  
  return 0xFFFF;
}

/**
 * Connect to WiFi
 */
void connectWiFi() {
  Serial.print(F("Connecting to WiFi: "));
  Serial.println(WIFI_SSID);
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(F("."));
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(F("\n✓ WiFi connected"));
    Serial.print(F("  IP Address: "));
    Serial.println(WiFi.localIP());
    Serial.print(F("  Signal Strength: "));
    Serial.print(WiFi.RSSI());
    Serial.println(F(" dBm"));
  } else {
    Serial.println(F("\n✗ WiFi connection failed!"));
  }
}

/**
 * Connect to MQTT broker
 */
void connectMQTT() {
  if (!mqttClient.connected()) {
    Serial.print(F("Connecting to MQTT broker: "));
    Serial.println(MQTT_BROKER);
    
    mqttClient.setUsernamePassword(MQTT_USERNAME, MQTT_PASSWORD);
    
    if (mqttClient.connect(MQTT_BROKER, MQTT_PORT)) {
      Serial.println(F("✓ MQTT connected"));
      
      // Publish discovery messages for Home Assistant
      publishDiscoveryMessages();
    } else {
      Serial.print(F("✗ MQTT connection failed, error: "));
      Serial.println(mqttClient.connectError());
    }
  }
}

/**
 * Publish Home Assistant MQTT discovery messages
 */
void publishDiscoveryMessages() {
  // Discovery for Channel 1 (example)
  String discoveryTopic = "homeassistant/sensor/oi7530_1_ch1/config";
  String discoveryPayload = "{";
  discoveryPayload += "\"name\":\"OI-7530-1 Channel 1\",";
  discoveryPayload += "\"state_topic\":\"" + baseTopic + "ch1/state\",";
  discoveryPayload += "\"unit_of_measurement\":\"PPM\",";
  discoveryPayload += "\"device_class\":\"gas\",";
  discoveryPayload += "\"unique_id\":\"oi7530_1_ch1\",";
  discoveryPayload += "\"device\":{";
  discoveryPayload += "\"identifiers\":[\"oi7530_1\"],";
  discoveryPayload += "\"name\":\"OI-7530 Monitor 1\",";
  discoveryPayload += "\"model\":\"OI-7530\",";
  discoveryPayload += "\"manufacturer\":\"OI Analytical\"";
  discoveryPayload += "}}";
  
  mqttClient.beginMessage(discoveryTopic, discoveryPayload.length(), true, 1);
  mqttClient.print(discoveryPayload);
  mqttClient.endMessage();
  
  Serial.println(F("✓ Published discovery messages"));
}

/**
 * Callback to enable RS485 transmit mode
 */
void preTransmission() {
  digitalWrite(MAX485_DE_RE, HIGH);
  delayMicroseconds(50); // Small delay for MAX485 to switch
}

/**
 * Callback to enable RS485 receive mode
 */
void postTransmission() {
  delayMicroseconds(50); // Wait for transmission to complete
  digitalWrite(MAX485_DE_RE, LOW);
}

/**
 * Estimate free memory (UNO R4 has 32KB RAM)
 */
int freeMemory() {
  extern int __heap_start, *__brkval;
  int v;
  return (int) &v - (__brkval == 0 ? (int) &__heap_start : (int) __brkval);
}
