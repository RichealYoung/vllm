"""Compile only this experiment's CPython extension; no packages installed."""
import json
import subprocess
import sysconfig
from pathlib import Path

cmd = ['gcc', '-O3', '-Wall', '-Wextra', '-Wno-unused-parameter', '-shared', '-fPIC',
       '-I'+sysconfig.get_paths()['include'], 'matcher.c',
       '-o', 'matcher'+sysconfig.get_config_var('EXT_SUFFIX')]
Path('build-command.json').write_text(json.dumps(cmd, indent=2))
subprocess.run(cmd, check=True)
