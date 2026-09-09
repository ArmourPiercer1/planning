# Test entry point for the planning-evals suite: set a workspace-local uv
# cache (the sandbox denies the default user cache) and run the
# zero-dependency tests.
#
# Usage:  pwsh .\tests\planning-evals\run_all.ps1
$ErrorActionPreference = "Stop"

$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$env:UV_CACHE_DIR = Join-Path $root ".cache\uv"
New-Item -ItemType Directory -Force -Path $env:UV_CACHE_DIR | Out-Null

& uv run --no-project python (Join-Path $PSScriptRoot "run_tests.py")
exit $LASTEXITCODE
