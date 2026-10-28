#!/usr/bin/env python3
"""Check all device/Simulator slices, install names, and public C module headers."""
import argparse, plistlib, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--artifacts', type=Path, default=ROOT / 'dist')
p.add_argument('--device-only', action='store_true')
a = p.parse_args(); frameworks = {}
for name in ['libEGL', 'libGLESv2']:
    artifact = a.artifacts / (name + '.xcframework')
    info = plistlib.loads((artifact / 'Info.plist').read_bytes())
    libraries = info['AvailableLibraries']
    assert len(libraries) == (1 if a.device_only else 2), libraries
    frameworks[name] = {}
    for library in libraries:
        assert library['SupportedPlatform'] == 'ios'
        simulator = library.get('SupportedPlatformVariant') == 'simulator'
        assert set(library['SupportedArchitectures']) == ({'arm64', 'x86_64'} if simulator else {'arm64'})
        folder = artifact / library['LibraryIdentifier']
        framework = folder / library['LibraryPath']
        binary = framework / name
        subprocess.run(['lipo', str(binary), '-verify_arch', *library['SupportedArchitectures']], check=True)
        identifier = subprocess.check_output(['otool', '-D', str(binary)], text=True)
        assert f'@rpath/{name}.framework/{name}' in identifier, identifier
        assert (framework / 'Modules/module.modulemap').is_file()
        frameworks[name]['simulator' if simulator else 'device'] = folder
for environment, architectures in [('device', ['arm64'])] + ([] if a.device_only else [('simulator', ['arm64', 'x86_64'])]):
    sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos' if environment == 'device' else 'iphonesimulator', '--show-sdk-path'], text=True).strip()
    for arch in architectures:
        triple = f'{arch}-apple-ios18.0' + ('-simulator' if environment == 'simulator' else '')
        with tempfile.TemporaryDirectory(prefix='angle-modules-') as cache:
            client = Path(cache) / 'client.c'
            client.write_text('#include "ANGLE.h"\nint main(void) { return (int)eglGetError() + (int)glGetError(); }\n')
            subprocess.run(['xcrun', 'clang', '-target', triple, '-isysroot', sdk, '-fmodules', '-fmodules-cache-path=' + cache,
                '-F' + str(frameworks['libEGL'][environment]), '-F' + str(frameworks['libGLESv2'][environment]),
                '-I' + str(ROOT / 'apple/SPM/include'), str(client), '-framework', 'libEGL', '-framework', 'libGLESv2',
                '-o', str(Path(cache) / 'client')], check=True)
print('PASS: slices, platforms, framework IDs and public headers/modules and linked clients')
