// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "ANGLE",
    platforms: [.iOS("18.0")],
    products: [.library(name: "ANGLE", targets: ["ANGLE"])],
    targets: [
        .binaryTarget(name: "libEGL", url: "https://github.com/mkrasnorutsky/ANGLE/releases/download/0.1.0/libEGL.xcframework.zip", checksum: "894faf03eae77cefbb4008940d4a5e3927504a2544c5c86ad6ecf68bc0013cf1"),
        .binaryTarget(name: "libGLESv2", url: "https://github.com/mkrasnorutsky/ANGLE/releases/download/0.1.0/libGLESv2.xcframework.zip", checksum: "acd2e421576fd13493689a1f30f8d08121e4e4a2fbcd9028ffb86d85fe2e114c"),
        .target(name: "ANGLE", dependencies: ["libEGL", "libGLESv2"],
                path: "apple/SPM", publicHeadersPath: "include")
    ]
)
