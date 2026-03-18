#!/bin/bash
# Verify all data stays in UK

# Check DB location
DB_LOCATION=$(podman inspect matchgorithm_db | jq -r '.[0].Config.Labels["com.docker.compose.project.working_dir"]')
if [[ ! "$DB_LOCATION" =~ "MysteryiousHounslow" ]]; then
  echo "❌ Database not in expected UK location"
  exit 1
fi

# Check timezone
DB_TZ=$(psql -U postgres -d matchgorithm -t -c "SHOW timezone")
if [ "$DB_TZ" != "Europe/London" ]; then
  echo "❌ Database not using UK timezone"
  exit 1
fi

echo "✅ UK data residency verified"