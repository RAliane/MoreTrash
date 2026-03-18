// TinyPINN.h
#pragma once
#include <stdint.h>

void TinyPINNInit();
void TinyPINNInference(const float state[13], float controlOut[4]);
