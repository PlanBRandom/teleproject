/*
 * OI-7530/7010 Modbus to MQTT Bridge for Arduino
 * 
 * Hardware:
 *  - Arduino board (Uno, Mega, Nano, ESP32, etc.)
 *  - MAX485 or similar RS485 transceiver module
 *  - Ethernet shield or WiFi module for MQTT
 * 
 * Wiring (MAX485):
 *  Arduino Pin 2  -> MAX485 RO (Receiver Output)
 *  Arduino Pin 3  -> MAX485 DI (Driver Input)
 *  Arduino Pin 4  -> MAX485 DE and RE (Direction control)
 *  Arduino 5V     -> MAX485 VCC
 *  Arduino GND    -> MAX485 GND
 *  MAX485 A       -> OI-7530 A/+
 *  MAX485 B       -> OI-7530 B/-
 * 
 * Libraries Required:
 *  - ModbusMaster (by Doc Walker)
 *  - PubSubClient (by Nick O'Leary) for MQTT
 *  - Ethernet or WiFi library depending on your board
 */

#include <ModbusMaster.h>
#include <SoftwareSerial.h>

// Modbus Configuration
#define MODBUS_SLAVE_ID 1
#define MAX485_DE 4  // Driver Enable / Receiver Enable pin
#define MODBUS_RX 2
#define MODBUS_TX 3

// Register Addresses (from OI-7530 register map)
#define REG_CHANNEL_1_READING 0x21  // Channel 1 gas reading (float32)
#define REG_CHANNEL_2_READING 0x23
#define REG_CHANNEL_3_READING 0x25
#define REG_CHANNEL_4_READING 0x27

// SoftwareSerial for Modbus communication
SoftwareSerial modbusSerial(MODBUS_RX, MODBUS_TX);

// Modbus object
ModbusMaster node;

// Timing
unsigned long lastPoll = 0;
const unsigned long POLL_INTERVAL = 5000; // 5 seconds

void setup() {
  // Initialize serial for debugging
  Serial.begin(115200);
  while (!Serial) delay(10);
  
  Serial.println(F("OI-7530/7010 Modbus Bridge Starting..."));
  
  // Initialize MAX485 control pin
  pinMode(MAX485_DE, OUTPUT);
  digitalWrite(MAX485_DE, LOW); // Start in receive mode
  
  // Initialize Modbus communication
  modbusSerial.begin(9600);
  node.begin(MODBUS_SLAVE_ID, modbusSerial);
  
  // Callbacks for RS485 direction control
  node.preTransmission(preTransmission);
  node.postTransmission(postTransmission);
  
  Serial.println(F("✓ Modbus initialized"));
  
  // TODO: Initialize Ethernet/WiFi
  // TODO: Connect to MQTT broker
  
  Serial.println(F("Ready to poll sensors"));
}

void loop() {
  unsigned long currentMillis = millis();
  
  // Poll sensors at regular interval
  if (currentMillis - lastPoll >= POLL_INTERVAL) {
    lastPoll = currentMillis;
    
    Serial.println(F("\n--- Polling Sensors ---"));
    
    // Read Channel 1
    float channel1 = readFloat32Register(REG_CHANNEL_1_READING);
    if (!isnan(channel1)) {
      Serial.print(F("Channel 1: "));
      Serial.print(channel1, 2);
      Serial.println(F(" PPM"));
      
      // TODO: Publish to MQTT
      // publishToMQTT("oi7530/channel1", channel1);
    }
    
    // Read Channel 2
    float channel2 = readFloat32Register(REG_CHANNEL_2_READING);
    if (!isnan(channel2)) {
      Serial.print(F("Channel 2: "));
      Serial.print(channel2, 2);
      Serial.println(F(" PPM"));
    }
    
    // Read Channel 3
    float channel3 = readFloat32Register(REG_CHANNEL_3_READING);
    if (!isnan(channel3)) {
      Serial.print(F("Channel 3: "));
      Serial.print(channel3, 2);
      Serial.println(F(" PPM"));
    }
    
    // Read Channel 4
    float channel4 = readFloat32Register(REG_CHANNEL_4_READING);
    if (!isnan(channel4)) {
      Serial.print(F("Channel 4: "));
      Serial.print(channel4, 2);
      Serial.println(F(" PPM"));
    }
    
    Serial.println(F("----------------------"));
  }
  
  // TODO: Handle MQTT loop
  // mqttClient.loop();
  
  delay(100);
}

/**
 * Read 32-bit float from two consecutive Modbus registers
 */
float readFloat32Register(uint16_t address) {
  uint8_t result = node.readHoldingRegisters(address, 2);
  
  if (result == node.ku8MBSuccess) {
    // Combine two 16-bit registers into 32-bit float
    uint16_t high = node.getResponseBuffer(0);
    uint16_t low = node.getResponseBuffer(1);
    
    // Pack into union for float conversion
    union {
      uint32_t i;
      float f;
    } converter;
    
    converter.i = ((uint32_t)high << 16) | low;
    
    return converter.f;
  } else {
    Serial.print(F("Modbus error reading address 0x"));
    Serial.print(address, HEX);
    Serial.print(F(": "));
    Serial.println(result);
    return NAN;
  }
}

/**
 * Read 16-bit unsigned integer from single register
 */
uint16_t readUint16Register(uint16_t address) {
  uint8_t result = node.readHoldingRegisters(address, 1);
  
  if (result == node.ku8MBSuccess) {
    return node.getResponseBuffer(0);
  } else {
    Serial.print(F("Modbus error reading address 0x"));
    Serial.print(address, HEX);
    Serial.print(F(": "));
    Serial.println(result);
    return 0xFFFF;
  }
}

/**
 * Callback to enable RS485 transmit mode
 */
void preTransmission() {
  digitalWrite(MAX485_DE, HIGH);
}

/**
 * Callback to enable RS485 receive mode
 */
void postTransmission() {
  digitalWrite(MAX485_DE, LOW);
}

/*
 * TODO: Add MQTT Publishing Functions
 * 
 * Example with PubSubClient:
 * 
 * #include <PubSubClient.h>
 * 
 * WiFiClient wifiClient;
 * PubSubClient mqttClient(wifiClient);
 * 
 * void setupMQTT() {
 *   mqttClient.setServer("192.168.1.100", 1883);
 *   connectToMQTT();
 * }
 * 
 * void connectToMQTT() {
 *   while (!mqttClient.connected()) {
 *     Serial.print("Connecting to MQTT...");
 *     if (mqttClient.connect("oi7530_arduino")) {
 *       Serial.println("connected");
 *     } else {
 *       Serial.print("failed, rc=");
 *       Serial.println(mqttClient.state());
 *       delay(5000);
 *     }
 *   }
 * }
 * 
 * void publishToMQTT(const char* topic, float value) {
 *   char msg[50];
 *   snprintf(msg, sizeof(msg), "{\"value\":%.2f}", value);
 *   mqttClient.publish(topic, msg);
 * }
 */
