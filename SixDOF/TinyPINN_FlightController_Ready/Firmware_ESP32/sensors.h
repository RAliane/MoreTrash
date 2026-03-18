// sensors.h
#pragma once
#include <stdint.h>

struct IMUData {
    float ax, ay, az; // m/s^2
    float gx, gy, gz; // rad/s (or deg/s depending on driver scaling)
};

struct GPSData {
    bool hasFix;
    float x, y, alt; // local coordinates or lat/lon (converted)
};

struct BaroData {
    bool valid;
    float pressure;
    float altitude;
    float temperature;
    float humidity;
};

struct ReceiverData {
    int throttle;
    int roll;
    int pitch;
    int yaw;
    int ch5;
    int ch6;
};

void SensorsInit();
void ReadIMU(IMUData &out);
void ReadGPS(GPSData &out);
void ReadBarometer(BaroData &out);
void ReadReceiver(ReceiverData &out);
