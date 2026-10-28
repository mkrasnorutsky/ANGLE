#!/usr/bin/env python3
"""Build ANGLE for Apple iOS and package module-enabled EGL/GLES XCFrameworks."""
import argparse, hashlib, json, os, plistlib, re, shutil, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def run(*args, **kwargs):
    print('+', ' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kwargs)

def prepare_framework(source, destination, name):
    if destination.exists(): shutil.rmtree(destination)
    shutil.copytree(source, destination, symlinks=True)
    signature = destination / '_CodeSignature'
    if signature.exists(): shutil.rmtree(signature)
    headers = destination / 'Headers'; headers.mkdir(exist_ok=True)
    groups = ['EGL', 'KHR'] if name == 'libEGL' else ['GLES2', 'GLES3']
    # Preserve original source headers; qualify includes only in packaged copies.
    for group in groups:
        for original in (ROOT / 'include' / group).glob('*.h'):
            text = original.read_text()
            text = re.sub(r'([<"])(EGL|KHR)/([^>"\n]+)([>"])', r'<libEGL/\3>', text)
            text = re.sub(r'([<"])(GLES2|GLES3)/([^>"\n]+)([>"])', r'<libGLESv2/\3>', text)
            (headers / original.name).write_text(text)
    includes = ['egl.h', 'eglext.h'] if name == 'libEGL' else ['gl2.h', 'gl3.h', 'gl31.h', 'gl32.h', 'gl2ext.h']
    (headers / (name + '.h')).write_text('#pragma once\n' + ''.join(f'#include <{name}/{header}>\n' for header in includes))
    modules = destination / 'Modules'; modules.mkdir(exist_ok=True)
    (modules / 'module.modulemap').write_text(f'framework module {name} {{\n umbrella header "{name}.h"\n export *\n module * {{ export * }}\n}}\n')
    run('install_name_tool', '-id', f'@rpath/{name}.framework/{name}', destination / name)
    for line in subprocess.check_output(['otool', '-L', str(destination / name)], text=True).splitlines()[1:]:
        dependency = line.strip().split(' (', 1)[0]
        for library in ['libEGL', 'libGLESv2']:
            if f'{library}.framework/' in dependency:
                target = f'@rpath/{library}.framework/{library}'
                if target != dependency: run('install_name_tool', '-change', dependency, target, destination / name)
    # Frameworks are unsigned distribution artifacts. Xcode signs on embedding.
    run('codesign', '--remove-signature', destination / name)
    shutil.copy2(ROOT / 'LICENSE', destination / 'LICENSE')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, default=ROOT, help='Bootstrapped checkout used for GN compilation')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    parser.add_argument('--device-only', action='store_true', help='Produce device-only artifacts; no Simulator support')
    parser.add_argument('--device-dir', type=Path, help='Reuse already built device frameworks from this directory')
    parser.add_argument('--sim-arm64-dir', type=Path, help='Reuse prebuilt arm64 Simulator frameworks')
    parser.add_argument('--sim-x64-dir', type=Path, help='Reuse prebuilt x86_64 Simulator frameworks')
    parser.add_argument('--jobs', type=int, default=int(os.environ.get('JOBS', '6')))
    parser.add_argument('--deployment-target', default='18.0')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    source = args.source_dir.resolve(); output = args.output.resolve()
    configs = [('ios-arm64', 'arm64', 'device', args.device_dir)]
    if not args.device_only:
        configs += [('ios-simulator-arm64', 'arm64', 'simulator', args.sim_arm64_dir), ('ios-simulator-x86_64', 'x64', 'simulator', args.sim_x64_dir)]
    if args.dry_run:
        print(json.dumps({'source': str(source), 'output': str(output), 'slices': [x[:3] for x in configs], 'deployment_target': args.deployment_target}, indent=2)); return
    output.mkdir(parents=True, exist_ok=True)
    staging = output / 'staging'
    if staging.exists(): shutil.rmtree(staging)
    staging.mkdir()
    built = {}
    for label, cpu, environment, prebuilt in configs:
        folder = prebuilt.resolve() if prebuilt else source / 'out' / ('xcframework-' + label)
        if not prebuilt:
            gn = source / 'buildtools/mac/gn'
            ninja = source / 'third_party/ninja/ninja'
            if not gn.is_file() or not ninja.is_file():
                raise SystemExit('Missing GN/Ninja. Run apple/scripts/bootstrap.sh first.')
            arguments = f'target_os="ios" target_cpu="{cpu}" target_environment="{environment}" is_debug=false angle_build_tests=false angle_enable_metal=true ios_enable_code_signing=false ios_deployment_target="{args.deployment_target}"'
            run(gn, 'gen', folder, '--args=' + arguments, cwd=source)
            run(ninja, '-C', folder, '-j', args.jobs, 'libEGL', 'libGLESv2')
        built[label] = {}
        for name in ['libEGL', 'libGLESv2']:
            framework = folder / (name + '.framework')
            if not framework.is_dir(): raise SystemExit(f'Missing {framework}')
            info = plistlib.loads((framework / 'Info.plist').read_bytes())
            expected = 'iPhoneOS' if environment == 'device' else 'iPhoneSimulator'
            if expected not in info.get('CFBundleSupportedPlatforms', []): raise SystemExit(f'Wrong platform in {framework}')
            arch = 'x86_64' if cpu == 'x64' else cpu
            run('lipo', framework / name, '-verify_arch', arch)
            destination = staging / label / (name + '.framework'); destination.parent.mkdir(parents=True, exist_ok=True)
            prepare_framework(framework, destination, name); built[label][name] = destination
    for name in ['libEGL', 'libGLESv2']:
        frameworks = [built['ios-arm64'][name]]
        if not args.device_only:
            universal = staging / 'ios-simulator' / (name + '.framework'); universal.parent.mkdir(exist_ok=True)
            shutil.copytree(built['ios-simulator-arm64'][name], universal)
            run('lipo', '-create', built['ios-simulator-arm64'][name] / name, built['ios-simulator-x86_64'][name] / name, '-output', universal / name)
            frameworks.append(universal)
        artifact = output / (name + '.xcframework')
        if artifact.exists(): shutil.rmtree(artifact)
        command = ['xcodebuild', '-create-xcframework']
        for framework in frameworks: command += ['-framework', str(framework)]
        run(*command, '-output', artifact)
    # Preserve upstream notices alongside redistributable binaries.
    notices = output / 'Licenses'
    if notices.exists(): shutil.rmtree(notices)
    notices.mkdir()
    shutil.copy2(ROOT / 'LICENSE', notices / 'ANGLE-LICENSE')
    for directory, subdirs, files in os.walk(source / 'third_party'):
        subdirs[:] = [x for x in subdirs if x not in ['.git', 'out', '__pycache__', 'node_modules']]
        for filename in files:
            if filename.upper().startswith(('LICENSE', 'COPYING', 'NOTICE')) or filename == 'README.chromium':
                original = Path(directory) / filename
                if original.is_file():
                    destination = notices / 'third_party' / original.relative_to(source / 'third_party')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(original, destination)
    for name in ['libEGL', 'libGLESv2']:
        shutil.copytree(notices, output / (name + '.xcframework') / 'Licenses')
    revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    source_revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    (output / 'build-manifest.json').write_text(json.dumps({'packaging_revision': revision, 'source_revision': source_revision, 'device_only': args.device_only, 'deployment_target': args.deployment_target, 'slices': list(built)}, indent=2) + '\n')
    print('Created XCFrameworks in', output)

if __name__ == '__main__': main()
