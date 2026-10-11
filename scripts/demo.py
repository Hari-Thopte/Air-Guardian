"""Launch fictional, loopback-only preview. No cloud data is changed."""
import argparse
import subprocess
import sys
import webbrowser
import time
import urllib.request
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=5187);args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
url=f'http://127.0.0.1:{args.port}/home.html?story=1'
process=subprocess.Popen([sys.executable,str(root/'scripts/preview_cloud.py'),'--port',str(args.port)],cwd=root)
try:
    for _ in range(100):
        if process.poll() is not None:
            raise SystemExit('Preview could not start; choose a free port.')
        try:
            with urllib.request.urlopen(url,timeout=.5):
                break
        except OSError:
            time.sleep(.1)
    else:
        raise SystemExit('Preview startup timed out.')
    webbrowser.open(url)
    process.wait()
finally:
    if process.poll() is None:
        process.terminate()
