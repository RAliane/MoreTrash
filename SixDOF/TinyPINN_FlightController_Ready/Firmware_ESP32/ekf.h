// ekf.h
#pragma once
#include <stdint.h>

struct State {
    float x, y, z;
    float vx, vy, vz;
    float qw, qx, qy, qz;
    float wx, wy, wz;
};

void EKFInit(State &state);
void EKFPredict(const float accel[3], const float gyro[3], float dt, State &state);
void EKFUpdateGPS(const float gpsPos[3], State &state);
void EKFUpdateBaro(float altitude, State &state);
