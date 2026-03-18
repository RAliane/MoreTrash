/**
 * Course Seeding Script for Directus
 * 
 * Seeds 5 university courses with deterministic 384-dimensional embeddings.
 * Uses a simple hash-based algorithm to generate embeddings without external APIs.
 * 
 * Courses:
 * 1. Computer Science - high math, low humanities, tech career
 * 2. Aerospace Engineering - very high math, engineering career
 * 3. Mechanical Engineering - high math, engineering career
 * 4. Data Science - high math, medium humanities, tech career
 * 5. Philosophy - low math, very high humanities, academic career
 * 
 * Usage:
 *   node seed-courses.js
 * 
 * Environment Variables:
 *   - DIRECTUS_URL: Directus API URL (default: http://localhost:8055)
 *   - DIRECTUS_ADMIN_EMAIL: Admin email
 *   - DIRECTUS_ADMIN_PASSWORD: Admin password
 *   - DB_HOST, DB_PORT, DB_DATABASE, DB_USER, DB_PASSWORD: PostgreSQL connection
 */

const { createDirectus, rest, authentication, readItems, createItem } = require('@directus/sdk');
const crypto = require('crypto');
const { Client } = require('pg');

// ============================================
// COURSE DATA
// ============================================

const COURSES = [
  {
    name: "Computer Science",
    description: "Fundamentals of computing, algorithms, data structures, and software engineering. Covers programming paradigms, computer architecture, and theoretical foundations.",
    department: "cs",
    credits: 4,
    math_intensity: 0.75,
    humanities_intensity: 0.20,
    career_paths: ["software_engineer", "systems_architect", "tech_lead", "startup_founder"]
  },
  {
    name: "Aerospace Engineering",
    description: "Design and analysis of aircraft and spacecraft. Covers aerodynamics, propulsion systems, orbital mechanics, and flight dynamics.",
    department: "engineering",
    credits: 4,
    math_intensity: 0.95,
    humanities_intensity: 0.10,
    career_paths: ["aerospace_engineer", "flight_engineer", "research_scientist", "defense_contractor"]
  },
  {
    name: "Mechanical Engineering",
    description: "Study of mechanical systems, thermodynamics, fluid mechanics, and materials science. Includes design and manufacturing processes.",
    department: "engineering",
    credits: 4,
    math_intensity: 0.85,
    humanities_intensity: 0.15,
    career_paths: ["mechanical_engineer", "design_engineer", "manufacturing_engineer", "robotics_engineer"]
  },
  {
    name: "Data Science",
    description: "Interdisciplinary field using scientific methods, processes, algorithms and systems to extract knowledge from data. Combines statistics, machine learning, and domain expertise.",
    department: "data_science",
    credits: 4,
    math_intensity: 0.80,
    humanities_intensity: 0.40,
    career_paths: ["data_scientist", "ml_engineer", "business_analyst", "research_scientist"]
  },
  {
    name: "Philosophy",
    description: "Critical examination of fundamental questions about existence, knowledge, values, reason, mind, and language. Emphasizes logical reasoning and ethical analysis.",
    department: "philosophy",
    credits: 3,
    math_intensity: 0.15,
    humanities_intensity: 0.95,
    career_paths: ["academic", "lawyer", "ethicist", "writer", "policy_analyst"]
  }
];

// ============================================
// DETERMINISTIC EMBEDDING GENERATION
// ============================================

/**
 * Generate a deterministic 384-dimensional embedding for a course.
 * 
 * This algorithm creates embeddings based on course characteristics:
 * - Math intensity (dims 0-95): higher values for math-heavy courses
 * - Humanities intensity (dims 96-191): higher values for humanities-heavy courses
 * - Career paths (dims 192-287): encoded career trajectory
 * - Department signature (dims 288-383): unique department fingerprint
 * 
 * @param {Object} course - Course object with properties
 * @returns {number[]} - 384-dimensional embedding array
 */
function generateEmbedding(course) {
  const embedding = new Array(384).fill(0.0);
  
  // Section 1: Math intensity (indices 0-95)
  // Higher math intensity = higher values in this section
  const mathBase = course.math_intensity;
  for (let i = 0; i < 96; i++) {
    // Add some variation based on index
    const variation = Math.sin(i * 0.1) * 0.1;
    embedding[i] = mathBase + variation * (1 - mathBase);
    // Normalize to [-1, 1]
    embedding[i] = Math.max(-1, Math.min(1, embedding[i]));
  }
  
  // Section 2: Humanities intensity (indices 96-191)
  const humanitiesBase = course.humanities_intensity;
  for (let i = 96; i < 192; i++) {
    const variation = Math.cos((i - 96) * 0.1) * 0.1;
    embedding[i] = humanitiesBase + variation * (1 - humanitiesBase);
    embedding[i] = Math.max(-1, Math.min(1, embedding[i]));
  }
  
  // Section 3: Career paths encoding (indices 192-287)
  // Hash career paths into this section
  const careerHash = hashString(course.career_paths.join(','));
  for (let i = 192; i < 288; i++) {
    const hashByte = careerHash[(i - 192) % careerHash.length];
    embedding[i] = (hashByte / 255) * 2 - 1; // Normalize to [-1, 1]
  }
  
  // Section 4: Department signature (indices 288-383)
  // Create unique signature based on department and name
  const signatureSeed = `${course.department}:${course.name}`;
  const signatureHash = hashString(signatureSeed);
  for (let i = 288; i < 384; i++) {
    const hashByte = signatureHash[(i - 288) % signatureHash.length];
    // Mix with a sinusoidal pattern for uniqueness
    const wave = Math.sin(i * 0.05) * 0.3;
    embedding[i] = ((hashByte / 255) * 2 - 1) * 0.7 + wave;
    embedding[i] = Math.max(-1, Math.min(1, embedding[i]));
  }
  
  // Normalize the entire embedding to unit length (L2 normalization)
  return normalizeEmbedding(embedding);
}

/**
 * Create SHA-256 hash of string and return as byte array.
 * @param {string} str - Input string
 * @returns {number[]} - Array of byte values (0-255)
 */
function hashString(str) {
  const hash = crypto.createHash('sha256').update(str).digest();
  return Array.from(hash);
}

/**
 * L2 normalize an embedding vector.
 * @param {number[]} embedding - Input embedding
 * @returns {number[]} - Normalized embedding
 */
function normalizeEmbedding(embedding) {
  const sumSquares = embedding.reduce((sum, val) => sum + val * val, 0);
  const magnitude = Math.sqrt(sumSquares);
  
  if (magnitude === 0) {
    return embedding;
  }
  
  return embedding.map(val => val / magnitude);
}

// ============================================
// DATABASE OPERATIONS
// ============================================

/**
 * Get PostgreSQL client configuration.
 */
function getPostgresConfig() {
  return {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432', 10),
    database: process.env.DB_DATABASE || 'directus',
    user: process.env.DB_USER || 'directus',
    password: process.env.DB_PASSWORD || 'directus',
  };
}

/**
 * Ensure pgvector extension is enabled.
 */
async function enablePgvector() {
  const config = getPostgresConfig();
  const client = new Client(config);
  
  try {
    await client.connect();
    await client.query('CREATE EXTENSION IF NOT EXISTS vector;');
    console.log('✓ pgvector extension enabled');
    
    // Verify extension
    const result = await client.query(
      "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
    );
    if (result.rows.length > 0) {
      console.log(`  Version: ${result.rows[0].extversion}`);
    }
  } catch (error) {
    console.error('✗ Failed to enable pgvector:', error.message);
    throw error;
  } finally {
    await client.end();
  }
}

/**
 * Seed courses into PostgreSQL with pgvector embeddings.
 */
async function seedCourses() {
  const config = getPostgresConfig();
  const client = new Client(config);
  
  try {
    await client.connect();
    console.log('\n📚 Seeding courses...\n');
    
    for (const course of COURSES) {
      // Generate embedding
      const embedding = generateEmbedding(course);
      
      // Convert to pgvector format
      const embeddingVector = `[${embedding.join(',')}]`;
      
      // Insert course with embedding
      const query = `
        INSERT INTO courses (
          id, name, description, department, credits,
          math_intensity, humanities_intensity, career_paths, embedding
        ) VALUES (
          gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7::jsonb, $8::vector
        )
        ON CONFLICT (name) DO UPDATE SET
          description = EXCLUDED.description,
          department = EXCLUDED.department,
          credits = EXCLUDED.credits,
          math_intensity = EXCLUDED.math_intensity,
          humanities_intensity = EXCLUDED.humanities_intensity,
          career_paths = EXCLUDED.career_paths,
          embedding = EXCLUDED.embedding,
          updated_at = CURRENT_TIMESTAMP
        RETURNING id, name;
      `;
      
      const values = [
        course.name,
        course.description,
        course.department,
        course.credits,
        course.math_intensity,
        course.humanities_intensity,
        JSON.stringify(course.career_paths),
        embeddingVector
      ];
      
      const result = await client.query(query, values);
      console.log(`✓ ${course.name}`);
      console.log(`  ID: ${result.rows[0].id}`);
      console.log(`  Department: ${course.department}`);
      console.log(`  Math: ${course.math_intensity}, Humanities: ${course.humanities_intensity}`);
      console.log(`  Embedding: 384 dimensions (norm = 1.0)`);
      console.log('');
    }
    
    console.log(`✓ Successfully seeded ${COURSES.length} courses\n`);
    
    // Show embedding similarity matrix
    await showSimilarityMatrix(client);
    
  } catch (error) {
    console.error('✗ Failed to seed courses:', error.message);
    throw error;
  } finally {
    await client.end();
  }
}

/**
 * Display cosine similarity matrix between courses.
 */
async function showSimilarityMatrix(client) {
  console.log('📊 Course Similarity Matrix (Cosine):\n');
  
  const courses = await client.query(
    'SELECT id, name, embedding FROM courses ORDER BY name;'
  );
  
  // Header
  const names = courses.rows.map(c => c.name.substring(0, 8).padEnd(8));
  console.log('         ' + names.join('  '));
  
  // Matrix
  for (let i = 0; i < courses.rows.length; i++) {
    const rowName = courses.rows[i].name.substring(0, 8).padEnd(8);
    const similarities = [];
    
    for (let j = 0; j < courses.rows.length; j++) {
      const sim = await client.query(
        'SELECT 1 - ($1::vector <=> $2::vector) AS cosine_sim;',
        [courses.rows[i].embedding, courses.rows[j].embedding]
      );
      similarities.push(sim.rows[0].cosine_sim.toFixed(2).padStart(6));
    }
    
    console.log(`${rowName}  ${similarities.join('  ')}`);
  }
  console.log('');
}

// ============================================
// MAIN EXECUTION
// ============================================

async function main() {
  console.log('╔════════════════════════════════════════════════════════╗');
  console.log('║     Directus Course Seeding with pgvector              ║');
  console.log('╚════════════════════════════════════════════════════════╝\n');
  
  try {
    // Step 1: Enable pgvector
    await enablePgvector();
    
    // Step 2: Seed courses
    await seedCourses();
    
    console.log('✅ Seeding completed successfully!');
    console.log('\nNext steps:');
    console.log('  1. Start Directus: npm run start');
    console.log('  2. Sync to Neo4j: python src/integrations/directus_neo4j_bridge.py');
    
  } catch (error) {
    console.error('\n❌ Seeding failed:', error.message);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

// Export for testing
module.exports = {
  COURSES,
  generateEmbedding,
  hashString,
  normalizeEmbedding,
  seedCourses
};
