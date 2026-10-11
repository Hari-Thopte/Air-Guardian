"""Create allowlisted cloud artifacts. Never copy .env, SQLite, credentials or demo accounts."""
import argparse
import json
from pathlib import Path
import shutil
import hashlib
import re

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / '.build' / 'backend'
WEB = ROOT / 'dist'


def package():
    BACKEND.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'cloud' / 'requirements.txt', BACKEND / 'requirements.txt')
    WEB.mkdir(exist_ok=True)
    for source_dir, pattern in [(ROOT / 'cloud', '*.py')]:
        for source in source_dir.glob(pattern):
            target = BACKEND / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    # Pure engines only; never package the local SQLite store or demo account seed.
    for obsolete in ['alert_engine.py', 'guardian_store.py']:
        (BACKEND / 'backend' / 'functions' / obsolete).unlink(missing_ok=True)
    for name in ['air_engine.py', 'guardian_rules.py']:
        source = ROOT / 'backend' / 'functions' / name
        target = BACKEND / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (BACKEND / 'assets').mkdir(exist_ok=True)
    shutil.copy2(ROOT / 'assets' / 'catalogue.json', BACKEND / 'assets' / 'catalogue.json')
    for name in ['offline.html', 'cloud-manifest.webmanifest', 'landing.js', 'landing-scenarios.json', 'home.html', 'home.css', 'home.js', 'portal-design.css', 'brand-refresh.css', 'cloud-theme.js', 'brand-entry.js', 'brand-entry.css', 'cloud.html', 'cloud-app.js', 'cloud-auth.js', 'cloud.css', 'cloud-sw.js']:
        shutil.copy2(ROOT / name, WEB / name)
    (WEB / 'assets').mkdir(exist_ok=True)
    for name in ['story.js', 'pwa-upgrade.js', 'resilient-fetch.js', 'upgrade.css', 'upgrade-controls.js', 'ui.css', 'ui.js', 'day-ui.js', 'consistency-ui.js', 'role-ui.js', 'locale.js', 'catalogue.json', 'kid-ui.js', 'planning-upgrade.js', 'safe-html.js', 'operations-ui.js', 'setup-ui.js', 'architecture.svg', 'landing.css']:
        shutil.copy2(ROOT / 'assets' / name, WEB / 'assets' / name)
    shutil.copy2(ROOT / 'assets' / 'logo.svg', WEB / 'assets' / 'logo.svg')
    shutil.copy2(ROOT / 'assets' / 'guardian-emblem.png', WEB / 'assets' / 'guardian-emblem.png')
    for name in ['guardian-emblem-small.webp','guardian-emblem-2x.webp','favicon.png']:
        shutil.copy2(ROOT/'assets'/name,WEB/'assets'/name)
    shutil.copytree(ROOT/'assets'/'fonts',WEB/'assets'/'fonts',dirs_exist_ok=True)
    shutil.copy2(ROOT / 'assets' / 'campus-landscape.webp', WEB / 'assets' / 'campus-landscape.webp')
    shutil.copy2(ROOT / 'cloud-config.example.js', WEB / 'cloud-config.js')
    digest = hashlib.sha256()
    for asset in sorted(WEB.rglob('*')):
        if asset.is_file() and asset.name not in ('cloud-sw.js', 'cloud-config.js'):
            digest.update(str(asset.relative_to(WEB)).encode())
            digest.update(asset.read_bytes())
    worker=WEB/'cloud-sw.js'
    worker.write_text(re.sub(r"const BUILD='[^']+';", "const BUILD='"+digest.hexdigest()[:16]+"';",worker.read_text(encoding='utf-8')),encoding='utf-8')
    print('Created allowlisted .build/backend and dist. Dependencies must be installed into .build/backend before deployment.')


def write_config(stack, region):
    import sys
    deps = ROOT / '.test-output' / 'deps'
    if deps.exists():
        sys.path.insert(0, str(deps))
    import boto3
    outputs = boto3.client('cloudformation', region_name=region).describe_stacks(StackName=stack)['Stacks'][0]['Outputs']
    values = {r['OutputKey']: r['OutputValue'] for r in outputs}
    config = {'apiUrl': values['ApiUrl'], 'clientId': values['ClientId'], 'authDomain': values['AuthDomain'],
              'redirectUri': values['Website'] + '/cloud.html'}
    (WEB / 'cloud-config.js').write_text('export const config = ' + json.dumps(config) + ';\n', encoding='utf-8')
    print(json.dumps({'website': values['Website'], 'bucket': values.get('WebBucketName'), 'distribution': values.get('DistributionId'),
                      'hostingDeployed': bool(values.get('DistributionId'))}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stack')
    parser.add_argument('--region', default='ap-south-1')
    args = parser.parse_args()
    if args.stack:
        write_config(args.stack, args.region)
    else:
        package()
