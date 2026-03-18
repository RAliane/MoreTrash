// sensors.cpp
// Minimal drivers and wrappers for MPU6050 (or LSM6DS3), NEO6M GPS, BME280.
// You should replace low-level implementation with appropriate library calls.

#include "sensors.h"
#include <Wire.h>

// Receiver pins (from user's mapping)
const int Channel1Pin = 34;
const int Channel2Pin = 35;
const int Channel3Pin = 32;
const int Channel4Pin = 33;
const int Channel5Pin = 25;
const int Channel6Pin = 26;

void SensorsInit() {
    Wire.begin();
    // MPU6050 init minimal (wake up)
    Wire.beginTransmission(0x68);
    Wire.write(0x6B); // PWR_MGMT_1
    Wire.write(0x00);
    Wire.endTransmission();
    // Additional initializations (filters) as needed
    pinMode(Channel1Pin, INPUT_PULLUP);
    pinMode(Channel2Pin, INPUT_PULLUP);
    pinMode(Channel3Pin, INPUT_PULLUP);
    pinMode(Channel4Pin, INPUT_PULLUP);
    pinMode(Channel5Pin, INPUT_PULLUP);
    pinMode(Channel6Pin, INPUT_PULLUP);
}

void ReadIMU(IMUData &out) {
    // Read MPU6050 raw registers (6 accel, 6 gyro)
    Wire.beginTransmission(0x68);
    Wire.write(0x3B); // ACCEL_XOUT_H
    Wire.endTransmission(false);
    Wire.requestFrom(0x68, 6);
    int16_t ax = (Wire.read() << 8) | Wire.read();
    int16_t ay = (Wire.read() << 8) | Wire.read();
    int16_t az = (Wire.read() << 8) | Wire.read();

    Wire.beginTransmission(0x68);
    Wire.write(0x43); // GYRO_XOUT_H
    Wire.endTransmission(false);
    Wire.requestFrom(0x68, 6);
    int16_t gx = (Wire.read() << 8) | Wire.read();
    int16_t gy = (Wire.read() << 8) | Wire.read();
    int16_t gz = (Wire.read() << 8) | Wire.read();

    // Scale factors: MPU6050 default: accel/4096 for +/-8g? Adjust as per your setup.
    out.ax = (float)ax / 4096.0f * 9.80665f;
    out.ay = (float)ay / 4096.0f * 9.80665f;
    out.az = (float)az / 4096.0f * 9.80665f;

    // Gyro scaling: raw/65.5 -> deg/s if FS=500 dps; convert to rad/s
    out.gx = ((float)gx / 65.5f) * (3.14159265f / 180.0f);
    out.gy = ((float)gy / 65.5f) * (3.14159265f / 180.0f);
    out.gz = ((float)gz / 65.5f) * (3.14159265f / 180.0f);
}

void ReadGPS(GPSData &out) {
    // Minimal stub. Replace with serial parsing of NEO6M (TinyGPS++ recommended).
    out.hasFix = false;
    out.x = 0.0f;
    out.y = 0.0f;
    out.alt = 0.0f;
}

void ReadBarometer(BaroData &out) {
    // Minimal stub. Replace with BME280 library calls.
    out.valid = false;
    out.pressure = 0.0f;
    out.altitude = 0.0f;
    out.temperature = 0.0f;
    out.humidity = 0.0f;
}

void ReadReceiver(ReceiverData &out) {
    // Simple pulseIn-based receiver read; for reliability, replace with interrupt/capture implementation.
    out.roll = pulseIn(Channel1Pin, HIGH, 25000);
    out.pitch = pulseIn(Channel2Pin, HIGH, 25000);
    out.throttle = pulseIn(Channel3Pin, HIGH, 25000);
    out.yaw = pulseIn(Channel4Pin, HIGH, 25000);
    out.ch5 = pulseIn(Channel5Pin, HIGH, 25000);
    out.ch6 = pulseIn(Channel6Pin, HIGH, 25000);
}
