#include <WiFi.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <SPIFFS.h>
#include <PubSubClient.h>
#include <AsyncElegantOTA.h>

// 1. ESP32 Wi-Fi Access Point Credentials
const char* ssid = "DRDO_ANC_NODE";
const char* password = "hackathondemo";

// 2. MQTT Broker for Android App Integration
const char* mqtt_server = "broker.emqx.io"; 
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// 3. Web & Socket Servers
AsyncWebServer server(80);
AsyncWebSocket ws("/ws");

void setup() {
  Serial.begin(115200);

  // Mount Internal Flash Memory
  if (!SPIFFS.begin(true)) {
    Serial.println("An Error has occurred while mounting SPIFFS");
    return;
  }

  // Broadcast Independent Wi-Fi Network
  WiFi.softAP(ssid, password);
  Serial.print("Hardware Node IP: ");
  Serial.println(WiFi.softAPIP());

  // Connect to External Wi-Fi for MQTT (Optional/Switch as needed)
  // WiFi.begin("Your_Hostel_WiFi", "Your_Password");

  // Serve the HTML Dashboard
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
    request->send(SPIFFS, "/index.html", "text/html");
  });

  // Initialize WebSockets & OTA
  server.addHandler(&ws);
  AsyncElegantOTA.begin(&server);
  server.begin();

  // Setup MQTT
  mqttClient.setServer(mqtt_server, 1883);
}

void loop() {
  // 1. Reconnect MQTT if dropped
  if (!mqttClient.connected() && WiFi.status() == WL_CONNECTED) {
    if (mqttClient.connect("ESP32_DRDO_Node")) {
      mqttClient.subscribe("drdo/anc/control");
    }
  }
  mqttClient.loop();

  // 2. Simulated DSP Data Processing (Replace with actual ANC math)
  static unsigned long lastUpdate = 0;
  if (millis() - lastUpdate > 500) { 
    lastUpdate = millis();
    int simulatedNoiseReduction = random(12, 35); 
    String dataPayload = String(simulatedNoiseReduction);

    // Push data instantly to the HTML Dashboard
    ws.textAll(dataPayload);
    
    // Push data to the Android App via MQTT
    if (mqttClient.connected()) {
      mqttClient.publish("drdo/anc/metrics", dataPayload.c_str());
    }
  }
}