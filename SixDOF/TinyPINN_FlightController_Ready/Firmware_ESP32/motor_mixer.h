// motor_mixer.h
#pragma once
#include <stdint.h>

void MotorMixerInit();
void MotorMixer(const float control[4], uint16_t pwmOut[4]);
void MotorMixerWrite(const uint16_t pwmOut[4]);
