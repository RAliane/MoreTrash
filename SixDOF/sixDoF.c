#include <stdio.h>
#include <math.h>
#include <string.h>

/*
 * 6 DoF Flight Dynamics Module with Quaternion-based Orientation
 * Designed for ESP32/ESP8266 distributed embedded systems
 * 
 * This module implements aircraft flight dynamics including:
 * - Mass management (fuel consumption, payload tracking)
 * - Engine thrust and fuel flow modeling
 * - Aerodynamic forces (lift, drag, weight)
 * - Quaternion-based attitude representation and updates
 * - Position and velocity integration
 */

/* ============================================================================
 * CONSTANTS AND CONFIGURATION
 * ============================================================================ */

// Standard atmosphere (sea level)
#define GRAVITY_ACCEL 9.80665          // m/s²
#define AIR_DENSITY_SEA_LEVEL 1.225    // kg/m³
#define TEMP_SEA_LEVEL 288.15          // K
#define PRESSURE_SEA_LEVEL 101325.0    // Pa

// Default aerodynamic parameters
#define DEFAULT_SPECIFIC_FUEL_CONSUMPTION 0.5  // kg/(N·s)

// Quaternion indices for clarity
#define QUAT_W 0
#define QUAT_X 1
#define QUAT_Y 2
#define QUAT_Z 3

// Vector component indices
#define VEC_X 0
#define VEC_Y 1
#define VEC_Z 2

/* ============================================================================
 * TYPE DEFINITIONS
 * ============================================================================ */

typedef struct {
    double pilotMass;
    double fuelMass;
    double armamentMass;
    double airframeMass;
    double totalMass;
} MassState;

typedef struct {
    double maxThrust;           // N
    double maxFuelFlow;         // kg/s
    double currentThrust;       // N
    double currentFuelFlow;     // kg/s
    double specificFuelConsumption;  // kg/(N·s)
} EngineState;

typedef struct {
    double wingArea;            // m²
    double coefficientLift;     // Dimensionless
    double coefficientDrag;     // Dimensionless
} AerodynamicCoefficients;

typedef struct {
    double velocity[3];         // m/s: [vx, vy, vz]
    double position[3];         // m: [x, y, z]
    double orientation[4];      // Quaternion: [w, x, y, z]
    double angularVelocity[3];  // rad/s: [roll_rate, pitch_rate, yaw_rate]
} DynamicState;

typedef struct {
    MassState mass;
    EngineState engine;
    AerodynamicCoefficients aero;
    DynamicState dynamics;
} AircraftState;

typedef struct {
    double density;             // kg/m³
    double temperature;         // K
    double pressure;            // Pa
} AtmosphericConditions;

/* ============================================================================
 * GLOBAL ATMOSPHERE STATE
 * ============================================================================ */

static AtmosphericConditions atmosphere = {
    .density = AIR_DENSITY_SEA_LEVEL,
    .temperature = TEMP_SEA_LEVEL,
    .pressure = PRESSURE_SEA_LEVEL
};

/* ============================================================================
 * UTILITY FUNCTIONS - VECTOR OPERATIONS
 * ============================================================================ */

/**
 * Calculate magnitude of a 3D vector
 */
static double vectorMagnitude(const double *vec) {
    return sqrt(vec[VEC_X] * vec[VEC_X] + 
                vec[VEC_Y] * vec[VEC_Y] + 
                vec[VEC_Z] * vec[VEC_Z]);
}

/**
 * Clamp a value between min and max
 */
static double clamp(double value, double minVal, double maxVal) {
    if (value < minVal) return minVal;
    if (value > maxVal) return maxVal;
    return value;
}

/* ============================================================================
 * QUATERNION OPERATIONS
 * ============================================================================ */

/**
 * Normalize quaternion to unit length (prevents drift)
 */
static void quaternionNormalize(double *q) {
    double norm = sqrt(q[QUAT_W] * q[QUAT_W] + 
                      q[QUAT_X] * q[QUAT_X] + 
                      q[QUAT_Y] * q[QUAT_Y] + 
                      q[QUAT_Z] * q[QUAT_Z]);
    
    // Avoid division by zero
    if (norm > 1e-10) {
        for (int i = 0; i < 4; i++) {
            q[i] /= norm;
        }
    }
}

/**
 * Update quaternion based on angular velocity
 * Uses Euler method (can be replaced with RK4 for higher accuracy)
 * 
 * @param q Current quaternion [w, x, y, z]
 * @param angularVel Angular velocity [p, q, r] (rad/s)
 * @param deltaTime Integration time step (s)
 */
static void quaternionUpdateEuler(double *q, const double *angularVel, double deltaTime) {
    double dq[4];
    
    // Quaternion derivative: dq/dt = 0.5 * Ω * q
    // where Ω is the skew-symmetric matrix of angular velocity
    dq[QUAT_W] = 0.5 * (-q[QUAT_X] * angularVel[0] - 
                         q[QUAT_Y] * angularVel[1] - 
                         q[QUAT_Z] * angularVel[2]);
    
    dq[QUAT_X] = 0.5 * ( q[QUAT_W] * angularVel[0] + 
                         q[QUAT_Y] * angularVel[2] - 
                         q[QUAT_Z] * angularVel[1]);
    
    dq[QUAT_Y] = 0.5 * ( q[QUAT_W] * angularVel[1] - 
                         q[QUAT_X] * angularVel[2] + 
                         q[QUAT_Z] * angularVel[0]);
    
    dq[QUAT_Z] = 0.5 * ( q[QUAT_W] * angularVel[2] + 
                         q[QUAT_X] * angularVel[1] - 
                         q[QUAT_Y] * angularVel[0]);
    
    // Integrate: q_new = q_old + dq * dt
    for (int i = 0; i < 4; i++) {
        q[i] += dq[i] * deltaTime;
    }
    
    // Normalize to prevent drift
    quaternionNormalize(q);
}

/* ============================================================================
 * ATMOSPHERIC MODEL
 * ============================================================================ */

/**
 * Update atmospheric conditions based on altitude
 * Uses simplified barometric formula
 * 
 * @param altitudeMeters Altitude in meters
 */
static void atmosphereUpdateByAltitude(double altitudeMeters) {
    const double tempLapseRate = 0.0065;  // K/m (standard atmosphere)
    
    // Temperature decreases with altitude
    atmosphere.temperature = TEMP_SEA_LEVEL - (tempLapseRate * altitudeMeters);
    
    // Pressure decreases exponentially
    double exponent = -(GRAVITY_ACCEL * altitudeMeters) / (287.05 * atmosphere.temperature);
    atmosphere.pressure = PRESSURE_SEA_LEVEL * exp(exponent);
    
    // Density from ideal gas law: ρ = p / (R * T)
    atmosphere.density = atmosphere.pressure / (287.05 * atmosphere.temperature);
}

/**
 * Get current atmospheric conditions
 */
static const AtmosphericConditions* atmosphereGetCurrent(void) {
    return &atmosphere;
}

/* ============================================================================
 * MASS MANAGEMENT
 * ============================================================================ */

/**
 * Update total mass after fuel consumption
 */
static void massRecalculateTotal(MassState *mass) {
    mass->totalMass = mass->pilotMass + mass->fuelMass + 
                     mass->armamentMass + mass->airframeMass;
}

/**
 * Consume fuel based on engine fuel flow
 * 
 * @param mass Mass state structure
 * @param fuelFlowRate Current fuel flow rate (kg/s)
 * @param deltaTime Time step (s)
 */
static void massConsumeFuel(MassState *mass, double fuelFlowRate, double deltaTime) {
    double fuelBurned = fuelFlowRate * deltaTime;
    
    mass->fuelMass -= fuelBurned;
    
    // Prevent negative fuel
    if (mass->fuelMass < 0.0) {
        mass->fuelMass = 0.0;
    }
    
    massRecalculateTotal(mass);
}

/**
 * Initialize mass state with component masses
 */
static void massInitialize(MassState *mass, double pilot, double fuel, 
                          double armament, double airframe) {
    mass->pilotMass = pilot;
    mass->fuelMass = fuel;
    mass->armamentMass = armament;
    mass->airframeMass = airframe;
    
    massRecalculateTotal(mass);
}

/* ============================================================================
 * ENGINE MODEL
 * ============================================================================ */

/**
 * Update engine state based on throttle command
 * 
 * @param engine Engine state structure
 * @param throttleCommand Throttle setting [0.0, 1.0]
 */
static void engineUpdateThrottle(EngineState *engine, double throttleCommand) {
    // Clamp throttle to valid range
    throttleCommand = clamp(throttleCommand, 0.0, 1.0);
    
    engine->currentThrust = throttleCommand * engine->maxThrust;
    engine->currentFuelFlow = throttleCommand * engine->maxFuelFlow;
}

/**
 * Initialize engine parameters
 */
static void engineInitialize(EngineState *engine, double maxThrust, 
                            double maxFuelFlow, double sfc) {
    engine->maxThrust = maxThrust;
    engine->maxFuelFlow = maxFuelFlow;
    engine->currentThrust = 0.0;
    engine->currentFuelFlow = 0.0;
    engine->specificFuelConsumption = sfc;
}

/* ============================================================================
 * AERODYNAMIC FORCE CALCULATIONS
 * ============================================================================ */

/**
 * Calculate lift force
 * L = 0.5 * ρ * v² * S * Cl
 * 
 * @param airspeedMs Airspeed magnitude (m/s)
 * @param wingAreaM2 Wing planform area (m²)
 * @param coefficientLift Lift coefficient (dimensionless)
 * @param densityKgM3 Air density (kg/m³)
 * @return Lift force (N)
 */
static double aeroCalculateLift(double airspeedMs, double wingAreaM2, 
                               double coefficientLift, double densityKgM3) {
    double velocitySquared = airspeedMs * airspeedMs;
    return 0.5 * densityKgM3 * velocitySquared * wingAreaM2 * coefficientLift;
}

/**
 * Calculate drag force
 * D = 0.5 * ρ * v² * S * Cd
 * 
 * @param airspeedMs Airspeed magnitude (m/s)
 * @param wingAreaM2 Wing planform area (m²)
 * @param coefficientDrag Drag coefficient (dimensionless)
 * @param densityKgM3 Air density (kg/m³)
 * @return Drag force (N)
 */
static double aeroCalculateDrag(double airspeedMs, double wingAreaM2, 
                               double coefficientDrag, double densityKgM3) {
    double velocitySquared = airspeedMs * airspeedMs;
    return 0.5 * densityKgM3 * velocitySquared * wingAreaM2 * coefficientDrag;
}

/**
 * Calculate gravitational force
 * W = m * g
 * 
 * @param massKg Aircraft total mass (kg)
 * @return Weight force (N)
 */
static double aeroCalculateWeight(double massKg) {
    return massKg * GRAVITY_ACCEL;
}

/* ============================================================================
 * POSITION AND VELOCITY INTEGRATION
 * ============================================================================ */

/**
 * Update position using current velocity (Euler integration)
 * 
 * @param position Current position [x, y, z] (m)
 * @param velocity Current velocity [vx, vy, vz] (m/s)
 * @param deltaTime Time step (s)
 */
static void positionUpdate(double *position, const double *velocity, double deltaTime) {
    for (int i = 0; i < 3; i++) {
        position[i] += velocity[i] * deltaTime;
    }
}

/**
 * Update velocity based on acceleration (Euler integration)
 * 
 * @param velocity Current velocity [vx, vy, vz] (m/s)
 * @param acceleration Current acceleration [ax, ay, az] (m/s²)
 * @param deltaTime Time step (s)
 */
static void velocityUpdate(double *velocity, const double *acceleration, double deltaTime) {
    for (int i = 0; i < 3; i++) {
        velocity[i] += acceleration[i] * deltaTime;
    }
}

/**
 * Update angular velocity based on angular acceleration
 * 
 * @param angularVelocity Current angular velocity [p, q, r] (rad/s)
 * @param angularAcceleration Angular acceleration [dp, dq, dr] (rad/s²)
 * @param deltaTime Time step (s)
 */
static void angularVelocityUpdate(double *angularVelocity, 
                                 const double *angularAcceleration, double deltaTime) {
    for (int i = 0; i < 3; i++) {
        angularVelocity[i] += angularAcceleration[i] * deltaTime;
    }
}

/* ============================================================================
 * CONTROL AND DYNAMICS
 * ============================================================================ */

/**
 * Placeholder for LQRI (Linear Quadratic Regulator Integral) controller
 * Returns throttle command based on aircraft state
 * 
 * @param aircraft Current aircraft state
 * @return Throttle command [0.0, 1.0]
 */
static double controlGetThrottleCommand(const AircraftState *aircraft) {
    // TODO: Implement LQRI control logic
    // For now, return a constant throttle value
    return 0.5;
}

/**
 * Main flight dynamics integration step
 * Updates all aircraft state variables based on physics
 * 
 * @param aircraft Aircraft state to update
 * @param deltaTime Integration time step (s)
 */
void flightDynamicsStep(AircraftState *aircraft, double deltaTime) {
    // Get throttle command from controller
    double throttleCommand = controlGetThrottleCommand(aircraft);
    
    // Update engine state
    engineUpdateThrottle(&aircraft->engine, throttleCommand);
    
    // Update mass due to fuel consumption
    massConsumeFuel(&aircraft->mass, aircraft->engine.currentFuelFlow, deltaTime);
    
    // Calculate airspeed magnitude
    double airspeed = vectorMagnitude(aircraft->dynamics.velocity);
    
    // Calculate aerodynamic forces
    double liftForce = aeroCalculateLift(airspeed, aircraft->aero.wingArea, 
                                        aircraft->aero.coefficientLift, 
                                        atmosphere.density);
    
    double dragForce = aeroCalculateDrag(airspeed, aircraft->aero.wingArea, 
                                        aircraft->aero.coefficientDrag, 
                                        atmosphere.density);
    
    double weightForce = aeroCalculateWeight(aircraft->mass.totalMass);
    
    // Calculate net forces (simplified - assumes thrust acts along velocity vector)
    double thrustMinusDrag = aircraft->engine.currentThrust - dragForce;
    double netVerticalForce = liftForce - weightForce;
    
    // Calculate accelerations
    double accelerationX = thrustMinusDrag / aircraft->mass.totalMass;
    double accelerationZ = netVerticalForce / aircraft->mass.totalMass;
    
    double acceleration[3] = {accelerationX, 0.0, accelerationZ};
    
    // Update velocity
    velocityUpdate(aircraft->dynamics.velocity, acceleration, deltaTime);
    
    // Update position
    positionUpdate(aircraft->dynamics.position, 
                  aircraft->dynamics.velocity, deltaTime);
    
    // Update attitude (orientation)
    quaternionUpdateEuler(aircraft->dynamics.orientation, 
                         aircraft->dynamics.angularVelocity, deltaTime);
    
    // Debug output
    debugPrintFlightState(aircraft);
}

/* ============================================================================
 * DEBUG AND MONITORING
 * ============================================================================ */

/**
 * Print current flight state for debugging
 */
static void debugPrintFlightState(const AircraftState *aircraft) {
    printf("=== Flight State ===\n");
    printf("Throttle: %.3f | Thrust: %.2f N | Fuel Flow: %.3f kg/s\n",
           aircraft->engine.currentThrust / aircraft->engine.maxThrust,
           aircraft->engine.currentThrust,
           aircraft->engine.currentFuelFlow);
    
    printf("Position: [%.2f, %.2f, %.2f] m\n",
           aircraft->dynamics.position[VEC_X],
           aircraft->dynamics.position[VEC_Y],
           aircraft->dynamics.position[VEC_Z]);
    
    printf("Velocity: [%.2f, %.2f, %.2f] m/s\n",
           aircraft->dynamics.velocity[VEC_X],
           aircraft->dynamics.velocity[VEC_Y],
           aircraft->dynamics.velocity[VEC_Z]);
    
    printf("Airspeed: %.2f m/s | Mass: %.2f kg | Fuel: %.2f kg\n",
           vectorMagnitude(aircraft->dynamics.velocity),
           aircraft->mass.totalMass,
           aircraft->mass.fuelMass);
    
    printf("Quaternion: [%.4f, %.4f, %.4f, %.4f]\n\n",
           aircraft->dynamics.orientation[QUAT_W],
           aircraft->dynamics.orientation[QUAT_X],
           aircraft->dynamics.orientation[QUAT_Y],
           aircraft->dynamics.orientation[QUAT_Z]);
}

/* ============================================================================
 * INITIALIZATION
 * ============================================================================ */

/**
 * Initialize complete aircraft state with default values
 */
void aircraftStateInitialize(AircraftState *aircraft) {
    // Initialize mass components (example values - adjust for your aircraft)
    massInitialize(&aircraft->mass, 100.0, 50.0, 20.0, 500.0);
    
    // Initialize engine (example values)
    engineInitialize(&aircraft->engine, 50000.0, 2.0, 
                    DEFAULT_SPECIFIC_FUEL_CONSUMPTION);
    
    // Initialize aerodynamic coefficients
    aircraft->aero.wingArea = 25.0;
    aircraft->aero.coefficientLift = 0.4;
    aircraft->aero.coefficientDrag = 0.02;
    
    // Initialize dynamics
    memset(aircraft->dynamics.velocity, 0, sizeof(aircraft->dynamics.velocity));
    memset(aircraft->dynamics.position, 0, sizeof(aircraft->dynamics.position));
    memset(aircraft->dynamics.angularVelocity, 0, sizeof(aircraft->dynamics.angularVelocity));
    
    // Initialize quaternion to identity (no rotation)
    aircraft->dynamics.orientation[QUAT_W] = 1.0;
    aircraft->dynamics.orientation[QUAT_X] = 0.0;
    aircraft->dynamics.orientation[QUAT_Y] = 0.0;
    aircraft->dynamics.orientation[QUAT_Z] = 0.0;
}

/* ============================================================================
 * MAIN PROGRAM
 * ============================================================================ */

int main(void) {
    // Create aircraft state
    AircraftState aircraft;
    
    // Initialize aircraft with default parameters
    aircraftStateInitialize(&aircraft);
    
    // Simulation parameters
    const double timeStep = 0.01;  // 10 ms integration step
    const double simulationDuration = 60.0;  // 60 second simulation
    int iterations = (int)(simulationDuration / timeStep);
    
    printf("Starting flight dynamics simulation...\n");
    printf("Simulation time: %.1f seconds | Time step: %.3f s\n\n", 
           simulationDuration, timeStep);
    
    // Run simulation loop
    for (int i = 0; i < iterations; i++) {
        // Update atmosphere based on current altitude
        atmosphereUpdateByAltitude(aircraft.dynamics.position[VEC_Z]);
        
        // Perform flight dynamics step
        flightDynamicsStep(&aircraft, timeStep);
        
        // Optional: Add periodic logging or event handling here
    }
    
    printf("Simulation complete.\n");
    
    return 0;
}

int loop(void) {
    // This function can be called periodically in embedded systems
    // For now, keeping it as a placeholder for external integration
    return 0;
}