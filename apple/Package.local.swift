// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "ANGLE",
    platforms: [.iOS("18.0")],
    products: [.library(name: "ANGLE", targets: ["ANGLE"])],
    targets: [
        .binaryTarget(name: "libEGL", path: "dist/libEGL.xcframework"),
        .binaryTarget(name: "libGLESv2", path: "dist/libGLESv2.xcframework"),
        .target(name: "ANGLE", dependencies: ["libEGL", "libGLESv2"],
                path: "apple/SPM", publicHeadersPath: "include")
    ]
)
