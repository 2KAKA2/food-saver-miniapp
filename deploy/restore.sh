#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

backup_file="${1:-}"
confirmation="${2:-}"
deploy_env="${3:-.env.deploy}"
backup_dir="$project_dir/backups"

if [[ -z "$backup_file" || "$confirmation" != "--confirm-restore" ]]; then
  echo "Usage: deploy/restore.sh backups/FILE.sql.gz --confirm-restore [.env.deploy]" >&2
  exit 1
fi
if [[ ! -f "$deploy_env" ]]; then
  echo "Missing deployment configuration: $deploy_env" >&2
  exit 1
fi
if [[ ! -f "$backup_file" ]]; then
  echo "Backup file does not exist: $backup_file" >&2
  exit 1
fi

resolved_backup="$(realpath "$backup_file")"
resolved_dir="$(realpath "$backup_dir")"
case "$resolved_backup" in
  "$resolved_dir"/*.sql.gz) ;;
  *)
    echo "For safety, restore files must be .sql.gz files inside $backup_dir" >&2
    exit 1
    ;;
esac

if [[ -f "${resolved_backup}.sha256" ]]; then
  (cd "$(dirname "$resolved_backup")" && sha256sum -c "$(basename "$resolved_backup").sha256")
else
  echo "Missing checksum file: ${resolved_backup}.sha256" >&2
  exit 1
fi

echo "Creating a recovery point before restore..."
"$project_dir/deploy/backup.sh" "$deploy_env"

gzip -dc "$resolved_backup" \
  | docker compose --env-file "$deploy_env" exec -T mysql \
      sh -c 'exec mysql -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"'

echo "Restore completed. Verify /health/ready and core business data now."
