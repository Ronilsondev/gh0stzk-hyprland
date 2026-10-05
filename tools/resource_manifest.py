#!/usr/bin/env python3
"""Atualiza inventário versionado; execute conscientemente após editar/importar recursos."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
resources = {}
for folder in ('assets', 'themes'):
    for path in sorted((ROOT / folder).rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts:
            continue
        if path.is_relative_to(ROOT / 'assets/fonts') and not path.is_relative_to(ROOT / 'assets/fonts/MapleMono-NF'):
            continue
        resources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
(ROOT / 'resources.json').write_text(json.dumps(resources, indent=2) + '\n')
