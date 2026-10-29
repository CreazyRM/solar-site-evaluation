"""Export a clean, tracked Site checkout without deployment identity or local state."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,help='Clean local Site Git checkout')
    args=parser.parse_args()
    source=Path(args.source).resolve()
    if not (source/'public/solar/index.html').is_file() or not (source/'.openai/hosting.json').is_file():
        raise ValueError('Source must be the Solar Atlas Site checkout.')
    repository=Path(__file__).resolve().parent.parent
    destination=(repository/'website').resolve()
    if not destination.is_relative_to(repository):
        raise ValueError('Destination must stay inside this repository.')
    git=lambda *items:subprocess.check_output(['git','-C',str(source),*items]).decode('utf-8')
    if git('status','--porcelain').strip():
        raise ValueError('Commit or save the Site source first; only clean snapshots are exported.')
    files=git('ls-files','-z').split('\0')
    copied=0
    for name in filter(None,files):
        relative=Path(name)
        if any(p in {'.git','node_modules','dist','.wrangler','.sites-runtime','.vinext','.codex','.agents'} for p in relative.parts):
            continue
        if relative.name.startswith(('.env','.dev.vars')) or relative.suffix in {'.pem','.key'}:
            continue
        original=(source/relative).resolve()
        target=(destination/('README.sites.md' if name=='README.md' else relative)).resolve()
        if not original.is_relative_to(source) or not target.is_relative_to(destination):
            raise ValueError('A source or destination path escapes its intended directory.')
        target.parent.mkdir(parents=True,exist_ok=True)
        if name=='.openai/hosting.json':
            target.write_text(json.dumps({'d1':None,'r2':None},indent=2)+'\n',encoding='utf-8')
        elif name=='package.json':
            package=json.loads(original.read_text(encoding='utf-8'))
            package['scripts']['dev:standalone']='node standalone-server.mjs'
            target.write_text(json.dumps(package,indent=2)+'\n',encoding='utf-8')
        else:
            shutil.copy2(original,target)
        copied+=1
    manifest={'source_commit':git('rev-parse','HEAD').strip(),'exported_files':copied,'hosting_identity_removed':True,'note':'Source snapshot only. No Site Git credentials, runtime secrets, local caches or private deployment identity are included.'}
    (destination/'SOURCE.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest))

if __name__=='__main__':
    main()
