// TinyPINN.cpp
// Tiny TFLite Micro wrapper. Handles quantized int8 model inputs/outputs if needed.

#include "TinyPINN.h"
#include "TinyPINN_Model_Int8.h" // Generated header from tflite -> C array
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "tensorflow/lite/version.h"

// Tensor arena size tuned earlier
constexpr int kTensorArenaSize = 96 * 1024;
static uint8_t tensorArena[kTensorArenaSize];

static tflite::MicroInterpreter* interpreterPtr = nullptr;
static TfLiteTensor* inputTensor = nullptr;
static TfLiteTensor* outputTensor = nullptr;

void TinyPINNInit() {
  static tflite::AllOpsResolver resolver;
  const tflite::Model* model = tflite::GetModel(TinyPINN_Model_Int8_tflite);
  static tflite::MicroInterpreter staticInterpreter(model, resolver, tensorArena, kTensorArenaSize);
  interpreterPtr = &staticInterpreter;
  TfLiteStatus status = interpreterPtr->AllocateTensors();
  if (status != kTfLiteOk) {
    // allocation failed
  }
  inputTensor = interpreterPtr->input(0);
  outputTensor = interpreterPtr->output(0);
}
void TinyPINNInference(const float state[13], float controlOut[4]) {
  // Handle int8 quantization if model is int8. We detect by checking input tensor type.
  if (inputTensor->type == kTfLiteInt8) {
    // get quantization params
    float scale = inputTensor->params.scale;
    int zeroPoint = inputTensor->params.zero_point;
    for (int i=0;i<13;i++) {
      int32_t q = (int32_t)roundf(state[i] / scale) + zeroPoint;
      if (q < -128) q = -128;
      if (q > 127) q = 127;
      inputTensor->data.int8[i] = (int8_t)q;
    }
  } else {
    // float input
    for (int i=0;i<13;i++) inputTensor->data.f[i] = state[i];
  }

  interpreterPtr->Invoke();

  if (outputTensor->type == kTfLiteInt8) {
    float outScale = outputTensor->params.scale;
    int outZero = outputTensor->params.zero_point;
    for (int i=0;i<4;i++) {
      int8_t q = outputTensor->data.int8[i];
      controlOut[i] = (float)( (int)q - outZero ) * outScale;
    }
  } else {
    for (int i=0;i<4;i++) controlOut[i] = outputTensor->data.f[i];
  }
}
