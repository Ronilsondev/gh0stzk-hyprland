#!/usr/bin/env python3
"""Atualiza inventário versionado; --check apenas verifica, sem escrever."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inventory(root):
    resources = {}
    for folder in ('assets', 'themes'):
        for path in sorted((root / folder).rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts:
                continue
            if path.is_relative_to(root / 'assets/fonts') and not path.is_relative_to(root / 'assets/fonts/MapleMono-NF'):
                continue
            resources[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return resources


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true', help='Conferir sem reescrever resources.json')
    args = ap.parse_args(argv)
    resources = inventory(ROOT)
    manifest = ROOT / 'resources.json'
    if args.check:
        try:
            recorded = json.loads(manifest.read_text())
        except (OSError, ValueError) as error:
            print('Manifesto inválido: ' + str(error))
            return 1
        if recorded != resources:
            print('resources.json diverge dos recursos; revise e regenere o manifesto explicitamente.')
            return 1
        print(f'resources.json: {len(resources)} recursos conferidos, sem alterações.')
        return 0
    manifest.write_text(json.dumps(resources, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
