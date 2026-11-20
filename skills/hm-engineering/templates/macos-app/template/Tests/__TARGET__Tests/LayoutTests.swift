import AppKit
import Foundation
import Testing
@testable import __TARGET__

@Suite struct LayoutTests {
    @Test func windowControlsSitOnOneLineAtFixedSpacing() {
        let centers = (0..<3).map { TrafficLightLayout.center(index: $0) }
        #expect(centers.map(\.y) == [21.75, 21.75, 21.75])
        #expect(centers[1].x - centers[0].x == TrafficLightLayout.spacing)
        #expect(centers[2].x - centers[1].x == TrafficLightLayout.spacing)
    }

    @Test func sidebarToggleSharesTheControlsCenterLine() {
        #expect(TrafficLightLayout.sidebarToggleCenter.y == TrafficLightLayout.centerYFromTop)
        #expect(TrafficLightLayout.sidebarToggleCenter.x > TrafficLightLayout.center(index: 2).x)
    }

    @Test func minimumWindowFitsSidebarAndContent() {
        #expect(WindowLayout.minWidth >= WindowLayout.sidebarWidth + 600)
        #expect(WindowLayout.defaultSize.width >= WindowLayout.minWidth)
        #expect(WindowLayout.defaultSize.height >= WindowLayout.minHeight)
    }

    @Test func doubleClickZoomsOnlyInTheFreeBandOfTheTitleBar() {
        let size = CGSize(width: 1040, height: 720)
        #expect(TitleBand.contains(CGPoint(x: 520, y: 700), windowSize: size))          // middle of the bar
        #expect(TitleBand.contains(CGPoint(x: 200, y: 720 - 44), windowSize: size))     // bottom of the bar
        #expect(!TitleBand.contains(CGPoint(x: 520, y: 720 - 46), windowSize: size))    // the page below it
        for i in 0..<3 {                                                                // never on a window control
            #expect(!TitleBand.contains(CGPoint(x: TrafficLightLayout.center(index: i).x + 10, y: 700), windowSize: size))
        }
        #expect(!TitleBand.contains(CGPoint(x: 1040 - TrafficLightLayout.trailingIconCenterFromEdge - 10, y: 700), windowSize: size))
    }

    @Test func doubleClickAlwaysChangesTheSize() {
        let screen = CGRect(x: 0, y: 0, width: 1440, height: 870)
        let small = CGRect(x: 200, y: 75, width: 1040, height: 720)
        #expect(ZoomToggle.next(frame: small, screen: screen, previous: nil) == screen)            // grows
        #expect(ZoomToggle.next(frame: screen, screen: screen, previous: small) == small)          // back to what it was
        let fallback = ZoomToggle.next(frame: screen, screen: screen, previous: nil)               // relaunched maximized
        #expect(fallback != screen && fallback.width <= WindowLayout.defaultSize.width)
        #expect(ZoomToggle.next(frame: screen, screen: screen, previous: screen) != screen)        // stale saved frame
    }

    @MainActor @Test func menuBarCarriesTheEditShortcuts() {
        _ = NSApplication.shared
        MainMenu.install(appName: "Teste")
        #expect(MainMenu.editShortcuts() == ["⌘Z", "⇧⌘Z", "⌘X", "⌘C", "⌘V", "⌘A"])
    }

    /// Every clickable shows the pointing hand: no `.plain` button and no bare tap gesture
    /// (an exception is declared on its own line with `// pointer: exceção`).
    @Test func everyClickableUsesThePointerStyle() throws {
        let sources = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().appendingPathComponent("Sources")
        var offenders: [String] = []
        for case let url as URL in FileManager.default.enumerator(at: sources, includingPropertiesForKeys: nil)! where url.pathExtension == "swift" {
            for (i, line) in try String(contentsOf: url, encoding: .utf8).components(separatedBy: "\n").enumerated() {
                let bad = line.contains(".buttonStyle(.plain)") || line.contains(".buttonStyle(.borderless)")
                    || (line.contains(".onTapGesture") && !line.contains("pointer: exceção") && !line.contains(".clickable("))
                if bad { offenders.append("\(url.lastPathComponent):\(i + 1)") }
            }
        }
        #expect(offenders.isEmpty, "clicável sem mãozinha: \(offenders)")
    }

    @Test func slowMotionDefaultsToRealSpeed() {
        #expect(Motion.slow == 1 || ProcessInfo.processInfo.environment["APP_SLOW_MOTION"] != nil)
        #expect(Motion.scaled(0.2) == 0.2 * Motion.slow)
    }
}
