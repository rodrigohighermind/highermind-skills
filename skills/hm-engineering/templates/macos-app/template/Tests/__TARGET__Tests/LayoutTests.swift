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

    @Test func slowMotionDefaultsToRealSpeed() {
        #expect(Motion.slow == 1 || ProcessInfo.processInfo.environment["APP_SLOW_MOTION"] != nil)
        #expect(Motion.scaled(0.2) == 0.2 * Motion.slow)
    }
}
