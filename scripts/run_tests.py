"""Run portable, offline test suites without live source queries."""
import os
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
temporary=root/'tmp'/'tests'
temporary.mkdir(parents=True,exist_ok=True)
env={**os.environ,'TMP':str(temporary),'TEMP':str(temporary),'TMPDIR':str(temporary)}
scripts=root/'skills'/'solar-site-land-soil'/'scripts'
for name in ('self_test.py','self_test_full.py','self_test_terrain.py','self_test_pipeline.py','self_test_standard.py'):
    subprocess.run([sys.executable,str(scripts/name)],cwd=root,env=env,check=True)
subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_solar_agents.py','-v'],cwd=root,env=env,check=True)
print('All offline test suites passed.')
