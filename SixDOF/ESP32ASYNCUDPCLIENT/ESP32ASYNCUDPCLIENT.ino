#include <SPI.h>

#include <Adafruit_GFX.h>
#include <Adafruit_GrayOLED.h>
#include <Adafruit_SPITFT.h>
#include <Adafruit_SPITFT_Macros.h>
#include <gfxfont.h>

#include <Wire.h>

#include "WiFi.h"

#include <MUIU8g2.h>
#include <U8g2lib.h>
#include <U8x8lib.h>

#include <Arduino_JSON.h>

#include <Adafruit_SSD1306.h>
#include <splash.h>

#include <AsyncUDP.h>

#include "WiFi.h"
#include "AsyncUDP.h"

const char *ssid = "TheOracle";
const char *password = "D0y0usp3AK0R4CL353";


// THIS IS THE CLIENT SIDE

AsyncUDP udp;

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  if (WiFi.waitForConnectResult() != WL_CONNECTED) {
    Serial.println("WiFi Failed");
    while (1) {
      delay(1000);
    }
  }
  if (udp.connect(IPAddress(192, 168, 1, 100), 1234)) {
    Serial.println("UDP connected");
    udp.onPacket([](AsyncUDPPacket packet) {
      Serial.print("UDP Packet Type: ");
      Serial.print(packet.isBroadcast() ? "Broadcast" : packet.isMulticast() ? "Multicast"
                                                                             : "Unicast");
      Serial.print(", From: ");
      Serial.print(packet.remoteIP());
      Serial.print(":");
      Serial.print(packet.remotePort());
      Serial.print(", To: ");
      Serial.print(packet.localIP());
      Serial.print(":");
      Serial.print(packet.localPort());
      Serial.print(", Length: ");
      Serial.print(packet.length());
      Serial.print(", Data: ");
      Serial.write(packet.data(), packet.length());
      Serial.println();
      //reply to the client
      packet.printf("Got %u bytes of data", packet.length());
    });
    //Send unicast
    udp.print("Hello Server!");
  }
}

void loop() {
  delay(1000);
  //Send broadcast on port 1234
  udp.broadcastTo("Anyone here?", 1234);
}
