#!/bin/sh
set -eu

# Ensure correct ownership/permissions for writable directories when using volumes
mkdir -p /app/uploaded_cvs

# Only adjust ownership/permissions if running as root
if [ "$(id -u)" = "0" ]; then
  chown -R appuser:appuser /app/uploaded_cvs || true
  chmod -R u+rwX,go-rwx /app/uploaded_cvs || true
fi

# Exec the passed command (gunicorn by default)
exec "$@"
