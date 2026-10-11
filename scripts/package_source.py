"""Package source and documentation only; exclude credentials, caches and local records."""
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import os

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT.parent/'artifacts'
SOURCE_EXTENSIONS={'.html','.css','.js','.mjs','.cjs','.py','.json','.md','.yaml','.yml','.txt','.webmanifest','.ino','.h','.sh','.ps1'}
ASSET_EXTENSIONS={'.svg','.png','.webp','.jpg','.jpeg','.woff2'}
DIRECTORIES={'assets','backend','cloud','scripts','sensors','tests','.github','docs'}
EXCLUDED={'__pycache__','vendor','.local','.aws-sam','.build','.test-output','dist','.git','.aws','.codex','.agents','node_modules','test-results','playwright-report'}


def source_paths():
    # Prune installed packages before traversal; enumerating them can stall an export.
    for directory, folders, files in os.walk(ROOT,followlinks=False):
        current=Path(directory)
        folders[:]=sorted(name for name in folders if name not in EXCLUDED
                         and (current!=ROOT or name in DIRECTORIES)
                         and not (current/name).is_symlink())
        for name in sorted(files): yield current/name


def package():
    OUTPUT.mkdir(exist_ok=True)
    target=OUTPUT/'air-guardian-upgraded-local-demo.zip'
    if target.exists(): target=OUTPUT/('air-guardian-upgraded-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.zip')
    count=0
    with ZipFile(target,'x',ZIP_DEFLATED) as archive:
        for path in source_paths():
            if not path.is_file() or path.is_symlink() or ROOT not in path.resolve().parents: continue
            relative=path.relative_to(ROOT)
            if any(part in EXCLUDED for part in relative.parts): continue
            if len(relative.parts)>1 and relative.parts[0] not in DIRECTORIES: continue
            if path.name=='cloud-config.js' or path.name=='.env' or path.suffix=='.log': continue
            allowed=path.suffix in SOURCE_EXTENSIONS or path.name in ('.gitignore','.env.example','LICENSE')
            if relative.parts[0]=='assets': allowed=allowed or path.suffix in ASSET_EXTENSIONS
            if not allowed: continue
            archive.write(path,'air-guardian/'+relative.as_posix());count+=1
    with ZipFile(target) as archive:
        assert archive.testzip() is None
        assert not any(Path(n).name in ('.env','cloud-config.js') for n in archive.namelist())
        assert 'air-guardian/home.html' in archive.namelist()
        assert 'air-guardian/cloud/local_engine.py' in archive.namelist()
    print(f'{target}\n{count} source/assets/docs files; no credentials, installed packages or local database.')
    return target


if __name__=='__main__': package()
