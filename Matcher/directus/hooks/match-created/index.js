// Hook: match-created
// Triggered when a new match record is created in Directus

module.exports = function registerHook({ filter, action }) {
  // After a match is created, notify both users
  action("matches.items.create", async ({ payload, key, collection }, { database, schema, accountability }) => {
    console.log(`[Matchgorithm] New match created: ${key}`)

    // TODO: Implement notification logic
    // - Send email to user_a and user_b
    // - Create notification records
    // - Trigger n8n workflow if configured

    return payload
  })
}
