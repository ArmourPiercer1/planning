#!/bin/sh
# Deploy-time health check. Reads the config file directly and fails the
# deploy if required keys are absent. (This is one of the external readers
# of config.json — there may be others.)
set -eu
CONFIG="${1:-config.json}"
for key in app_name env log_level; do
    grep -q "\"$key\"" "$CONFIG" || {
        echo "deploy check failed: missing $key in $CONFIG" >&2
        exit 1
    }
done
echo "deploy check ok"
