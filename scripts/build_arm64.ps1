# Fallback package build when Docker is unavailable. Runtime smoke verification remains required.
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
python scripts/package_cloud.py
if ($LASTEXITCODE) { throw 'Packaging failed' }
python -m pip wheel --no-deps --wheel-dir .build/wheels http-ece==1.2.1
if ($LASTEXITCODE) { throw 'Pure Python wheel build failed' }
python -m pip install --target .build/backend --platform manylinux2014_aarch64 --platform manylinux_2_28_aarch64 --python-version 3.12 --implementation cp --only-binary=:all: --find-links .build/wheels -r cloud/requirements.txt
if ($LASTEXITCODE) { throw 'Linux ARM64 dependency resolution failed' }
python scripts/verify_arm64_package.py
if ($LASTEXITCODE) { throw 'ARM64 package inspection failed' }
sam validate --lint --template-file template.yaml
if ($LASTEXITCODE) { throw 'Template validation failed' }
Write-Host 'Linux ARM64 dependencies prepared. This is not a Lambda runtime smoke test or a live deployment.'
