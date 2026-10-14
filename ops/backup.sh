#!/usr/bin/env sh
set -eu

: "${DB_HOST:?Set DB_HOST}"
: "${DB_NAME:?Set DB_NAME}"
: "${DB_USER:?Set DB_USER}"
: "${DB_PASSWORD:?Set DB_PASSWORD}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="$BACKUP_DIR/$STAMP"
mkdir -p "$DEST"

MYSQL_PWD="$DB_PASSWORD" mysqldump \
  --host="$DB_HOST" --user="$DB_USER" --single-transaction \
  --routines --triggers --databases "$DB_NAME" > "$DEST/$DB_NAME.sql"

if [ -d "${ML_MODEL_DIR:-backend/app/ml/models}" ]; then
  tar -czf "$DEST/ml-artifacts.tar.gz" -C "${ML_MODEL_DIR:-backend/app/ml/models}" .
fi
printf 'Backup created at %s\n' "$DEST"
