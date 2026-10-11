"""Inspect dependency wheel tags and ELF architecture; does not execute Lambda code."""
import hashlib
import json
from pathlib import Path
import struct

root = Path(__file__).resolve().parents[1]
package = root / '.build' / 'backend'
errors, native, wheels = [], [], []
for wheel in sorted(package.glob('*.dist-info/WHEEL')):
    tags = [line[5:].strip() for line in wheel.read_text().splitlines() if line.startswith('Tag: ')]
    wheels.append({'distribution': wheel.parent.name, 'tags': tags})
    if not any(tag.endswith('-any') or ('aarch64' in tag and ('manylinux' in tag or 'linux' in tag)) for tag in tags):
        errors.append('Incompatible wheel: ' + wheel.parent.name)
for path in sorted(package.rglob('*.so')):
    header = path.read_bytes()[:20]
    valid = len(header) >= 20 and header[:4] == b'\x7fELF' and header[4] == 2 and header[5] == 1 and struct.unpack('<H', header[18:20])[0] == 183
    native.append({'path': str(path.relative_to(package)), 'elfArm64': valid})
    if not valid:
        errors.append('Non-ARM64 native binary: ' + str(path.relative_to(package)))
for path in package.rglob('*.pyd'):
    errors.append('Windows binary: ' + str(path.relative_to(package)))
for required in ('boto3', 'botocore', 'pywebpush', 'cryptography', 'aws_lambda_powertools'):
    if not (package / required).exists():
        errors.append('Missing dependency: ' + required)
digest = hashlib.sha256()
for path in sorted(package.rglob('*')):
    if path.is_file():
        digest.update(path.relative_to(package).as_posix().encode())
        digest.update(path.read_bytes())
report = {'passed': not errors, 'packageSha256': digest.hexdigest(), 'nativeBinaries': native, 'wheels': wheels,
          'errors': errors, 'runtimeSmokeVerified': False,
          'note': 'Static architecture inspection only. Execute imports in Linux ARM64 Lambda before enrollment.'}
target = root / '.test-output' / 'arm64-package-verification.json'
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'passed': not errors, 'nativeBinaries': len(native), 'wheels': len(wheels), 'errors': errors, 'evidence': str(target)}))
raise SystemExit(int(bool(errors)))
