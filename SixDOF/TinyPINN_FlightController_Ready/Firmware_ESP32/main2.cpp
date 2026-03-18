// main.cpp
// Top-level firmware: sensors -> EKF -> TinyPINN -> MotorMixer
// All names use PascalCase / camelCase per project rules.

#include <Arduino.h>
#include "sensors.h"
#include "ekf.h"
#include "TinyPINN.h"
#include "motor_mixer.h"

// Timing
constexpr float ControlDt = 0.01f; // 100 Hz loop

// Global state
State EkfState;

// Safety and receiver
int ThrottleIdle = 1170;
int ThrottleCutOff = 1000;

// Setup and loop
void setup() {
    Serial.begin(115200);
    delay(100);

    // Initialize sensors
    SensorsInit();

    // Initialize EKF
    EKFInit(EkfState);

    // Initialize TinyPINN (TFLM)
    TinyPINNInit();

    // Initialize motors
    MotorMixerInit();

    Serial.println("Startup complete");
}
void loop() {
    static unsigned long lastTime = micros();
    unsigned long now = micros();
    float dt = (now - lastTime) * 1e-6f;
    if (dt <= 0.0f) dt = ControlDt;
    // keep control rate steady
    if (dt < ControlDt) {
        delay((int)((ControlDt - dt)*1000.0f));
        now = micros();
        dt = (now - lastTime) * 1e-6f;
    }
    lastTime = now;

    // 1) Read sensors
    IMUData imu;
    GPSData gps;
    BaroData baro;
    ReceiverData receiver;
    ReadIMU(imu);
    ReadGPS(gps);
    ReadBarometer(baro);
    ReadReceiver(receiver);

    // 2) EKF predict & update
    float accel[3] = { imu.ax, imu.ay, imu.az };
    float gyro[3]  = { imu.gx, imu.gy, imu.gz };
    EKFPredict(accel, gyro, dt, EkfState);

    if (gps.hasFix) {
        float gpsPos[3] = {gps.x, gps.y, gps.alt};
        EKFUpdateGPS(gpsPos, EkfState);
    }
    if (baro.valid) {
        EKFUpdateBaro(baro.altitude, EkfState);
    }

    // 3) Build state vector for TinyPINN (13 elements)
    float stateVec[13];
    stateVec[0]  = EkfState.x;
    stateVec[1]  = EkfState.y;
    stateVec[2]  = EkfState.z;
    stateVec[3]  = EkfState.vx;
    stateVec[4]  = EkfState.vy;
    stateVec[5]  = EkfState.vz;
    stateVec[6]  = EkfState.qw;
    stateVec[7]  = EkfState.qx;
    stateVec[8]  = EkfState.qy;
    stateVec[9]  = EkfState.qz;
    stateVec[10] = EkfState.wx;
    stateVec[11] = EkfState.wy;
    stateVec[12] = EkfState.wz;

    // 4) Get TinyPINN control output
    float controlOut[4]; // [Thrust, TauX, TauY, TauZ]
    TinyPINNInference(stateVec, controlOut);

    // 5) Safety: map thrust to receiver scale and enforce throttle cutoffs
    // Convert controlOut[0] (N) to PWM range or use directly; here we assume controlOut[0] scaled to 1000..2000
    uint16_t motorPWM[4];
    MotorMixer(controlOut, motorPWM);

    // Enforce throttle cutoffs and receiver override (keep existing safety)
    if (receiver.throttle < 1030) {
        motorPWM[0] = ThrottleCutOff;
        motorPWM[1] = ThrottleCutOff;
        motorPWM[2] = ThrottleCutOff;
        motorPWM[3] = ThrottleCutOff;
    }

    // 6) Write PWM to ESCs
    MotorMixerWrite(motorPWM);

    // Optional telemetry
    if (millis() % 250 == 0) {
        Serial.print("State: ");
        Serial.print(EkfState.x); Serial.print(", ");
        Serial.print(EkfState.y); Serial.print(", ");
        Serial.println(EkfState.z);
    }
}

// 4) Get TinyPINN control output
float controlOut[4]; // [Thrust, TauX, TauY, TauZ]
TinyPINNInference(stateVec, controlOut);

// 5) Safety: map thrust to receiver scale and enforce throttle cutoffs
// Convert controlOut[0] (N) to PWM range or use directly; here we assume controlOut[0] scaled to 1000..2000
uint16_t motorPWM[4];
MotorMixer(controlOut, motorPWM);

// Enforce throttle cutoffs and receiver override (keep existing safety)
if (receiver.throttle < 1030) {
    motorPWM[0] = ThrottleCutOff;
    motorPWM[1] = ThrottleCutOff;
    motorPWM[2] = ThrottleCutOff;
    motorPWM[3] = ThrottleCutOff;
}

// 6) Write PWM to ESCs
MotorMixerWrite(motorPWM);

// Optional telemetry
if (millis() % 250 == 0) {
    Serial.print("State: ");
    Serial.print(EkfState.x); Serial.print(", ");
    Serial.print(EkfState.y); Serial.print(", ");
    Serial.println(EkfState.z);
}
}
