#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

deploy_env="${1:-.env.deploy}"
if [[ ! -f "$deploy_env" ]]; then
  echo "Missing deployment configuration: $deploy_env" >&2
  exit 1
fi

retention_days="${BACKUP_RETENTION_DAYS:-30}"
if [[ ! "$retention_days" =~ ^[1-9][0-9]*$ ]]; then
  echo "BACKUP_RETENTION_DAYS must be a positive integer." >&2
  exit 1
fi

backup_dir="$project_dir/backups"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
final_file="$backup_dir/food_saver_${timestamp}.sql.gz"
temporary_file="${final_file}.partial"
trap 'rm -f "$temporary_file"' EXIT

docker compose --env-file "$deploy_env" exec -T mysql \
  sh -c 'exec mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers --events "$MYSQL_DATABASE"' \
  | gzip -9 > "$temporary_file"

if [[ ! -s "$temporary_file" ]]; then
  echo "Backup failed: output file is empty." >&2
  exit 1
fi

mv "$temporary_file" "$final_file"
sha256sum "$final_file" > "${final_file}.sha256"
chmod 600 "$final_file" "${final_file}.sha256"
trap - EXIT

find "$backup_dir" -maxdepth 1 -type f \
  \( -name 'food_saver_*.sql.gz' -o -name 'food_saver_*.sql.gz.sha256' \) \
  -mtime "+$retention_days" -print -delete

echo "Backup created: $final_file"
echo "Copy both the backup and checksum to storage outside this server."
