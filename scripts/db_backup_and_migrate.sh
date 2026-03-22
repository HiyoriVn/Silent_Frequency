#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/db_backup_and_migrate.sh backup
#   ./scripts/db_backup_and_migrate.sh migrate
#   ./scripts/db_backup_and_migrate.sh restore
#
# Environment:
#   DB_CONTAINER   - postgres container name/id (auto-detected if empty)
#   PGUSER         - postgres user (default: postgres)
#   PGDATABASE     - database name (default: silent_frequency)
#   MIGRATION_FILE - migration file path
#   BACKUP_FILE    - local SQL backup path

ACTION="${1:-}"
PGUSER="${PGUSER:-postgres}"
PGDATABASE="${PGDATABASE:-silent_frequency}"
MIGRATION_FILE="${MIGRATION_FILE:-backend/app/db/migrations/20260321_gameplay_v2.sql}"
BACKUP_FILE="${BACKUP_FILE:-/tmp/pre_migration.sql}"

if [[ -z "${ACTION}" ]]; then
  echo "Usage: $0 [backup|migrate|restore]"
  exit 1
fi

resolve_container() {
  if [[ -n "${DB_CONTAINER:-}" ]]; then
    echo "${DB_CONTAINER}"
    return
  fi

  local detected
  detected="$(docker ps --filter "ancestor=postgres" --format "{{.Names}}" | head -n1 || true)"
  if [[ -z "${detected}" ]]; then
    echo "ERROR: Could not auto-detect postgres container. Set DB_CONTAINER." >&2
    exit 1
  fi
  echo "${detected}"
}

DB_CONTAINER="$(resolve_container)"

run_backup() {
  echo "[backup] container=${DB_CONTAINER} db=${PGDATABASE} user=${PGUSER} -> ${BACKUP_FILE}"
  docker exec -i "${DB_CONTAINER}" pg_dump -U "${PGUSER}" -d "${PGDATABASE}" > "${BACKUP_FILE}"
  echo "[backup] complete"
}

run_migrate() {
  if [[ ! -f "${MIGRATION_FILE}" ]]; then
    echo "ERROR: migration file not found: ${MIGRATION_FILE}" >&2
    exit 1
  fi

  echo "[migrate] This will apply ${MIGRATION_FILE} to ${PGDATABASE} in ${DB_CONTAINER}."
  read -r -p "Are you sure? (yes/no): " ans
  if [[ "${ans}" != "yes" ]]; then
    echo "[migrate] aborted"
    exit 0
  fi

  docker cp "${MIGRATION_FILE}" "${DB_CONTAINER}:/tmp/20260321_gameplay_v2.sql"
  docker exec -i "${DB_CONTAINER}" psql -U "${PGUSER}" -d "${PGDATABASE}" -f /tmp/20260321_gameplay_v2.sql
  echo "[migrate] complete"
}

run_restore() {
  if [[ ! -f "${BACKUP_FILE}" ]]; then
    echo "ERROR: backup file not found: ${BACKUP_FILE}" >&2
    exit 1
  fi

  echo "[restore] restoring ${BACKUP_FILE} into ${PGDATABASE} on ${DB_CONTAINER}"
  docker exec -i "${DB_CONTAINER}" psql -U "${PGUSER}" -d "${PGDATABASE}" < "${BACKUP_FILE}"
  echo "[restore] complete"
}

case "${ACTION}" in
  backup)
    run_backup
    ;;
  migrate)
    run_migrate
    ;;
  restore)
    run_restore
    ;;
  *)
    echo "Usage: $0 [backup|migrate|restore]"
    exit 1
    ;;
esac
