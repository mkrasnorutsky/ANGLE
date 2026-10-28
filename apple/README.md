# ANGLE for iOS / Swift Package Manager

This repository preserves the complete tracked ANGLE source and upstream history, based on `dbd678c224bb034ac569a23f83ceba359b4a66ca`. Third-party source checkouts are restored at their upstream-pinned revisions through `DEPS`, not committed a second time. Generated files, cached toolchains, old build output and `_bad_scm` recovery folders are not source distribution contents.

## Download / add as an SPM dependency

Release [0.1.0](https://github.com/mkrasnorutsky/ANGLE/releases/tag/0.1.0) contains both XCFramework ZIP archives. Add `https://github.com/mkrasnorutsky/ANGLE.git` in Xcode, select version **0.1.0** or later, and add the **ANGLE** product. The release manifest downloads checksum-verified binaries; consumers do not need GN or Chromium dependencies.

## Build

Use macOS, Xcode with both iPhoneOS and iPhoneSimulator SDKs, Python 3 and Git. Allow substantial disk space for Chromium dependencies and three build directories. Source/framework builds require no Apple signing identity; Xcode signs frameworks when embedding them into an app.

```sh
git clone https://github.com/mkrasnorutsky/ANGLE.git
cd ANGLE
apple/scripts/bootstrap.sh
python3 apple/scripts/build_xcframeworks.py
python3 apple/scripts/validate_xcframeworks.py
```

The default builds **arm64 iPhone + arm64 Simulator + x86_64 Simulator** with the Metal backend and iOS 18 minimum. It produces `dist/libEGL.xcframework` and `dist/libGLESv2.xcframework`, each containing a device framework and a universal Simulator framework. Headers and Clang module maps are added to distribution copies; upstream headers are left intact. GLES/EGL install names remain `@rpath/libGLESv2.framework/libGLESv2` and `@rpath/libEGL.framework/libEGL`.

Set `--jobs N` to control parallelism. `--device-only` is an explicit reduced build and does not support Simulator. `--device-dir`, `--sim-arm64-dir`, and `--sim-x64-dir` reuse existing framework outputs; their platforms and CPU architectures are checked. `--source-dir` builds another bootstrapped checkout, recording its Git revision in `dist/build-manifest.json`. `--dry-run` lists the requested slices without compiling.

A manually triggered GitHub Actions workflow builds and validates the same three architectures. It stores downloadable workflow artifacts and does not publish a release automatically.

## Use locally with SPM

After building the XCFrameworks, copy `apple/Package.local.swift` to `Package.swift`, then add this repository folder as a local package in Xcode and select the **ANGLE** product. The product includes EGL and GLES modules and exports their public headers through `ANGLE.h`. Do not also manually link the old frameworks. The local-development manifest uses local binary paths; a fresh clone must build artifacts before resolving it. The release manifest in the repository root uses downloadable ZIP archives once a binary release is published.

This is a binary-backed Swift package: GN/Ninja compile ANGLE, and SPM integrates the resulting XCFrameworks. SPM does not run GN during package resolution.

## Prepare a downloadable release package

```sh
python3 apple/scripts/package_release.py --tag 0.2.0
```

This creates two ZIP archives, SHA-256 checksums, and `dist/Package.swift` with immutable GitHub release URLs. Upload the ZIP files to that tag's GitHub release, replace the root manifest with the generated manifest and commit/tag that distribution revision. Preserve `apple/SPM` at that revision. Never replace archive contents under an existing release tag: checksums are immutable. The reusable local-path template remains in `apple/Package.local.swift`.

All original ANGLE licenses and third-party license notices remain in the source tree. Distribution frameworks include ANGLE's root LICENSE; downstream distributions must retain applicable third-party notices as well.

Version 0.1.1 removes mirrored Git submodule entries from the package checkout so SPM does not recursively clone build dependencies. Source builds still use the pinned DEPS file and bootstrap script. The validated 0.1.0 XCFramework archives remain unchanged.
