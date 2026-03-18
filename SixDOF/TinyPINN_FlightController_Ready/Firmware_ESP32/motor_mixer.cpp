// motor_mixer.cpp
#include "motor_mixer.h"
#include <Arduino.h>
#include <ESP32Servo.h> // or appropriate library

// Using the same pins as user's original configuration
const int Mot1Pin = 13;
const int Mot2Pin = 12;
const int Mot3Pin = 14;
const int Mot4Pin = 27;

static Servo Mot1, Mot2, Mot3, Mot4;

void MotorMixerInit() {
    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    ESP32PWM::allocateTimer(2);
    ESP32PWM::allocateTimer(3);
    Mot1.attach(Mot1Pin, 1000, 2000);
    Mot1.setPeriodHertz(500);
    Mot2.attach(Mot2Pin, 1000, 2000);
    Mot2.setPeriodHertz(500);
    Mot3.attach(Mot3Pin, 1000, 2000);
    Mot3.setPeriodHertz(500);
    Mot4.attach(Mot4Pin, 1000, 2000);
    Mot4.setPeriodHertz(500);
}

void MotorMixer(const float control[4], uint16_t pwmOut[4]) {
    // control: [Thrust, TauX, TauY, TauZ]
    // Mixer assumes control values mapped to PWM units (1000..2000)
    float T = control[0];
    float Tx = control[1];
    float Ty = control[2];
    float Tz = control[3];

    float m1 = T - Tx - Ty - Tz;
    float m2 = T - Tx + Ty + Tz;
    float m3 = T + Tx + Ty - Tz;
    float m4 = T + Tx - Ty + Tz;

    auto clamp = [](float v, float lo, float hi)->uint16_t {
        if (v < lo) v = lo;
        if (v > hi) v = hi;
        return (uint16_t)roundf(v);
    };

    pwmOut[0] = clamp(m1, 1000.0f, 2000.0f);
    pwmOut[1] = clamp(m2, 1000.0f, 2000.0f);
    pwmOut[2] = clamp(m3, 1000.0f, 2000.0f);
    pwmOut[3] = clamp(m4, 1000.0f, 2000.0f);
}

void MotorMixerWrite(const uint16_t pwmOut[4]) {
    Mot1.writeMicroseconds(pwmOut[0]);
    Mot2.writeMicroseconds(pwmOut[1]);
    Mot3.writeMicroseconds(pwmOut[2]);
    Mot4.writeMicroseconds(pwmOut[3]);
}
