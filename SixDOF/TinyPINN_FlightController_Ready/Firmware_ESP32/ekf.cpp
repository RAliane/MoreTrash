// ekf.cpp
// A compact, efficient 13-state (full quaternion) EKF implementation.
// This implementation uses a simple covariance and linearized updates.
// It is intentionally compact and understandable; you can replace with a more
// optimized version for performance/accuracy as needed.

#include "ekf.h"
#include <math.h>
#include <string.h>

// Covariance and process noise (stored as 13x13 float arrays flattened)
static float P[13*13];
static float Qproc[13*13];
static float Rgps[3*3];
static float Rbaro;

// Helpers
static inline int idx(int i, int j) { return i*13 + j; }

// Quaternion multiply: qOut = q * r
static void QuaternionMultiply(const float q[4], const float r[4], float out[4]) {
    const float w1=q[0], x1=q[1], y1=q[2], z1=q[3];
    const float w2=r[0], x2=r[1], y2=r[2], z2=r[3];
    out[0] = w1*w2 - x1*x2 - y1*y2 - z1*z2;
    out[1] = w1*x2 + x1*w2 + y1*z2 - z1*y2;
    out[2] = w1*y2 - x1*z2 + y1*w2 + z1*x2;
    out[3] = w1*z2 + x1*y2 - y1*x2 + z1*w2;
}

static void QuaternionNormalize(float q[4]) {
    float n = sqrtf(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3]);
    if (n > 0.0f) {
        q[0] /= n; q[1] /= n; q[2] /= n; q[3] /= n;
    } else {
        q[0]=1; q[1]=0; q[2]=0; q[3]=0;
    }
}

// Initialize EKF
void EKFInit(State &state) {
    state.x = state.y = state.z = 0.0f;
    state.vx = state.vy = state.vz = 0.0f;
    state.qw = 1.0f; state.qx = state.qy = state.qz = 0.0f;
    state.wx = state.wy = state.wz = 0.0f;

    // Initialize covariance P small
    for (int i=0;i<13*13;i++) P[i]=0.0f;
    for (int i=0;i<13;i++) P[i*13 + i] = 0.01f;

    // Process noise Qproc (tuned conservatively)
    for (int i=0;i<13*13;i++) Qproc[i]=0.0f;
    // position, velocity process noise
    Qproc[idx(0,0)] = Qproc[idx(1,1)] = Qproc[idx(2,2)] = 1e-3f;
    Qproc[idx(3,3)] = Qproc[idx(4,4)] = Qproc[idx(5,5)] = 5e-3f;
    // attitude and angular rates
    Qproc[idx(6,6)] = Qproc[idx(7,7)] = Qproc[idx(8,8)] = Qproc[idx(9,9)] = 1e-4f;
    Qproc[idx(10,10)] = Qproc[idx(11,11)] = Qproc[idx(12,12)] = 1e-3f;

    // Measurement noise
    Rgps[0]=0.25f; Rgps[1]=0.0f; Rgps[2]=0.0f;
    Rgps[3]=0.0f; Rgps[4]=0.25f; Rgps[5]=0.0f;
    Rgps[6]=0.0f; Rgps[7]=0.0f; Rgps[8]=0.5f;

    Rbaro = 1.0f; // altitude variance in meters^2

}

// Predict step: propagate state using accel (in body) and gyro (body)
void EKFPredict(const float accel[3], const float gyro[3], float dt, State &state) {
    // 1) Quaternion integration (omega in rad/s, gyro array)
    // qdot = 0.5 * Omega(omega) * q
    float q[4] = { state.qw, state.qx, state.qy, state.qz };
    float omega[3] = { gyro[0], gyro[1], gyro[2] };
    float OmegaMat[4];
    // Use small quaternion derivative discrete integration (first order)
    float qDot[4];
    qDot[0] = -0.5f*(omega[0]*q[1] + omega[1]*q[2] + omega[2]*q[3]);
    qDot[1] =  0.5f*(omega[0]*q[0] + omega[1]*q[3] - omega[2]*q[2]);
    qDot[2] =  0.5f*(omega[1]*q[0] - omega[0]*q[3] + omega[2]*q[1]);
    qDot[3] =  0.5f*(omega[2]*q[0] + omega[0]*q[2] - omega[1]*q[1]);

    state.qw += qDot[0] * dt;
    state.qx += qDot[1] * dt;
    state.qy += qDot[2] * dt;
    state.qz += qDot[3] * dt;
    float qnorm[4] = { state.qw, state.qx, state.qy, state.qz };
    QuaternionNormalize(qnorm);
    state.qw = qnorm[0]; state.qx = qnorm[1]; state.qy = qnorm[2]; state.qz = qnorm[3];

    // 2) Rotate accel from body to inertial using quaternion
    // R(q) * a_body
    // compute rotation matrix elements
    float w = state.qw, x = state.qx, y = state.qy, z = state.qz;
    float R00 = 1 - 2*(y*y + z*z);
    float R01 = 2*(x*y - z*w);
    float R02 = 2*(x*z + y*w);
    float R10 = 2*(x*y + z*w);
    float R11 = 1 - 2*(x*x + z*z);
    float R12 = 2*(y*z - x*w);
    float R20 = 2*(x*z - y*w);
    float R21 = 2*(y*z + x*w);
    float R22 = 1 - 2*(x*x + y*y);

    // acceleration in inertial (m/s^2). Note: subtract gravity if accel measures gravity+acc
    float ax_i = R00*accel[0] + R01*accel[1] + R02*accel[2];
    float ay_i = R10*accel[0] + R11*accel[1] + R12*accel[2];
    float az_i = R20*accel[0] + R21*accel[1] + R22*accel[2];

    // Gravity (NED style: +z up). Adjust sign convention to match sensors.
    const float g = 9.80665f;
    az_i -= g;

    // 3) Integrate velocity and position
    state.vx += ax_i * dt;
    state.vy += ay_i * dt;
    state.vz += az_i * dt;

    state.x += state.vx * dt;
    state.y += state.vy * dt;
    state.z += state.vz * dt;

    // 4) Update angular rates
    state.wx = gyro[0];
    state.wy = gyro[1];
    state.wz = gyro[2];

    // 5) Covariance prediction: P = P + Qproc * dt
    for (int i=0;i<13;i++) {
        for (int j=0;j<13;j++) {
            P[idx(i,j)] += Qproc[idx(i,j)] * dt;
        }
    }
}

// GPS update (position)
void EKFUpdateGPS(const float gpsPos[3], State &state) {
    // Simple Kalman update on position only with assumed independent noise
    // K = Ppos * (Ppos + Rgps)^-1 ; we approximate using only diagonal terms for simplicity

    // innovation
    float innov0 = gpsPos[0] - state.x;
    float innov1 = gpsPos[1] - state.y;
    float innov2 = gpsPos[2] - state.z;

    // extract position variances
    float varX = P[idx(0,0)];
    float varY = P[idx(1,1)];
    float varZ = P[idx(2,2)];

    float kx = varX / (varX + Rgps[0]);
    float ky = varY / (varY + Rgps[4]);
    float kz = varZ / (varZ + Rgps[8]);

    state.x += kx * innov0;
    state.y += ky * innov1;
    state.z += kz * innov2;

    // update covariances (diagonal approx)
    P[idx(0,0)] *= (1 - kx);
    P[idx(1,1)] *= (1 - ky);
    P[idx(2,2)] *= (1 - kz);
}

// Barometer update (z only)
void EKFUpdateBaro(float altitude, State &state) {
    float innov = altitude - state.z;
    float varZ = P[idx(2,2)];
    float kz = varZ / (varZ + Rbaro);
    state.z += kz * innov;// GPS update (position)
    void EKFUpdateGPS(const float gpsPos[3], State &state) {
        // Simple Kalman update on position only with assumed independent noise
        // K = Ppos * (Ppos + Rgps)^-1 ; we approximate using only diagonal terms for simplicity

        // innovation
        float innov0 = gpsPos[0] - state.x;
        float innov1 = gpsPos[1] - state.y;
        float innov2 = gpsPos[2] - state.z;

        // extract position variances
        float varX = P[idx(0,0)];
        float varY = P[idx(1,1)];
        float varZ = P[idx(2,2)];

        float kx = varX / (varX + Rgps[0]);
        float ky = varY / (varY + Rgps[4]);
        float kz = varZ / (varZ + Rgps[8]);

        state.x += kx * innov0;
        state.y += ky * innov1;
        state.z += kz * innov2;

        // update covariances (diagonal approx)
        P[idx(0,0)] *= (1 - kx);
        P[idx(1,1)] *= (1 - ky);
        P[idx(2,2)] *= (1 - kz);
    }

    // Barometer update (z only)
    void EKFUpdateBaro(float altitude, State &state) {
        float innov = altitude - state.z;
        float varZ = P[idx(2,2)];
        float kz = varZ / (varZ + Rbaro);
        state.z += kz * innov;
        P[idx(2,2)] *= (1 - kz);
    }
    P[idx(2,2)] *= (1 - kz);
}
