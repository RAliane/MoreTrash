#include <Arduino.h>
#include "TinyPINN_Model_Int8.h"
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "tensorflow/lite/version.h"

constexpr int kTensorArenaSize = 128*1024;
uint8_t tensorArena[kTensorArenaSize];

tflite::AllOpsResolver resolver;
const tflite::Model* model = tflite::GetModel(TinyPINN_Model_Int8_tflite);
tflite::MicroInterpreter interpreter(model, resolver, tensorArena, kTensorArenaSize);
TfLiteTensor* inputTensor;
TfLiteTensor* outputTensor;

struct State {
  float x,y,z;
  float vx,vy,vz;
  float qw,qx,qy,qz;
  float wx,wy,wz;
};
State ekfState;

uint16_t motorPWM[4];

void setup() {
  Serial.begin(115200);
  interpreter.AllocateTensors();
  inputTensor = interpreter.input(0);
  outputTensor = interpreter.output(0);
}

void loop() {
  float dt = 0.01;
  // Placeholder: read sensors, EKF predict/update

  // TinyPINN inference
  for(int i=0;i<13;i++) inputTensor->data.f[i] = *((float*)&ekfState + i);
  interpreter.Invoke();
  float control[4];
  for(int i=0;i<4;i++) control[i] = outputTensor->data.f[i];

  // Motor mixing (simplified)
  motorPWM[0] = constrain(control[0]-control[1]-control[2]-control[3],1000,2000);
  motorPWM[1] = constrain(control[0]-control[1]+control[2]+control[3],1000,2000);
  motorPWM[2] = constrain(control[0]+control[1]+control[2]-control[3],1000,2000);
  motorPWM[3] = constrain(control[0]+control[1]-control[2]+control[3],1000,2000);

  delay(dt*1000);
}
