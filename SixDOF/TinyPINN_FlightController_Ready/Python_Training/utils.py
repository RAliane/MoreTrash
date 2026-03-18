import numpy as np

# Quaternion helpers
def quatNormalize(q):
    return q / np.linalg.norm(q)

def quatMultiply(q1, q2):
    w1,x1,y1,z1 = q1
    w2,x2,y2,z2 = q2
    w = w1*w2 - x1*x2 - y1*y2 - z1*z2
    x = w1*x2 + x1*w2 + y1*z2 - z1*y2
    y = w1*y2 - x1*z2 + y1*w2 + z1*x2
    z = w1*z2 + x1*y2 - y1*x2 + z1*w2
    return np.array([w,x,y,z])

def rigid_body_dynamics(state, control):
    # Placeholder 6DoF rigid body dynamics
    stateDot = np.zeros_like(state)
    stateDot[:3] = state[3:6]  # dx/dt = v
    stateDot[3:6] = control[:3]  # simplistic acceleration placeholder
    stateDot[6:10] = 0  # quaternion derivative placeholder
    stateDot[10:13] = control[1:4]  # angular velocity placeholder
    return stateDot
