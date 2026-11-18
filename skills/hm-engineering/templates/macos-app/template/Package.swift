// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "__TARGET__",
    // The binary must carry the current macOS SDK: with an older platform floor SwiftPM records an old
    // sdk in LC_BUILD_VERSION and the system draws the legacy chrome (smaller, gray window controls).
    platforms: [.macOS("26.0")],
    targets: [
        .executableTarget(
            name: "__TARGET__",
            path: "Sources/__TARGET__",
            linkerSettings: [.linkedFramework("AppKit")]
        ),
        .testTarget(
            name: "__TARGET__Tests",
            dependencies: ["__TARGET__"],
            path: "Tests/__TARGET__Tests"
        ),
    ]
)
