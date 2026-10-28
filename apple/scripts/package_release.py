#!/usr/bin/env python3
"""Zip XCFrameworks and generate an SPM manifest with immutable release URLs/checksums."""
from pathlib import Path
import argparse, hashlib, json, subprocess
ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--tag', required=True, help='GitHub release tag, e.g. apple-0.1.0')
p.add_argument('--repository', default='mkrasnorutsky/ANGLE')
p.add_argument('--artifacts', type=Path, default=ROOT / 'dist')
a = p.parse_args(); artifacts = a.artifacts.resolve(); checksums = {}
for name in ['libEGL', 'libGLESv2']:
    source = artifacts / (name + '.xcframework')
    if not source.is_dir(): raise SystemExit(f'Missing {source}; build XCFrameworks first.')
    archive = artifacts / (name + '.xcframework.zip')
    if archive.exists(): archive.unlink()
    subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(source), str(archive)], check=True)
    checksums[name] = hashlib.sha256(archive.read_bytes()).hexdigest()
manifest = (ROOT / 'apple/Package.local.swift').read_text()
for name, checksum in checksums.items():
    local = f'.binaryTarget(name: "{name}", path: "dist/{name}.xcframework")'
    remote = f'.binaryTarget(name: "{name}", url: "https://github.com/{a.repository}/releases/download/{a.tag}/{name}.xcframework.zip", checksum: "{checksum}")'
    if local not in manifest: raise SystemExit('Invalid apple/Package.local.swift template.')
    manifest = manifest.replace(local, remote)
(artifacts / 'Package.swift').write_text(manifest)
(artifacts / 'checksums.json').write_text(json.dumps(checksums, indent=2) + '\n')
print('Release files prepared in', artifacts)
print('Upload the two ZIP files to the matching GitHub release, then commit the generated Package.swift at the release revision.')
