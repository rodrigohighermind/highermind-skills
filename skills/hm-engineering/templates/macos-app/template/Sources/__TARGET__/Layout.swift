import CoreGraphics

/// Window geometry in points, measured once and kept as named constants (never eyeballed per view).
enum WindowLayout {
    /// Honest minimum: the size the content actually fits. Verify by shrinking the window in QA:
    /// if any page forces the window larger, raise this instead of letting it lie.
    static let minWidth: CGFloat = 900
    static let minHeight: CGFloat = 600
    static let defaultSize = CGSize(width: 1200, height: 780)
    static let sidebarWidth: CGFloat = 218
    /// Title-bar row height (the content sheet starts below it).
    static let titleBarHeight: CGFloat = 45
    /// Content column measure; centered when the window is wider (symmetric margins).
    static let contentMaxWidth: CGFloat = 960
    static let sheetInset: CGFloat = 8
    static let sheetRadius: CGFloat = 18
}

/// Native window controls placed at a fixed geometry (like Electron's trafficLightPosition).
/// AppKit relayouts the title bar, so the controller reapplies this on every resize.
enum TrafficLightLayout {
    static let firstCenterX: CGFloat = 22.75
    static let spacing: CGFloat = 23
    static let centerYFromTop: CGFloat = 21.75
    /// The sidebar toggle sits right after the three controls, on the same center line.
    static let sidebarToggleCenter = CGPoint(x: 99.75, y: 21.75)
    /// Right-hand title-bar icons mirror the left inset.
    static let trailingIconCenterFromEdge: CGFloat = 22.25

    static func center(index: Int) -> CGPoint {
        CGPoint(x: firstCenterX + spacing * CGFloat(index), y: centerYFromTop)
    }
}

/// The free band of the title bar: a double-click there does what the user chose in System Settings
/// (zoom by default). Never on the window controls nor on the right-hand icons.
enum TitleBand {
    /// Past the last window control, plus half a hit area and a gap.
    static let start: CGFloat = TrafficLightLayout.center(index: 2).x + 11 + 6
    /// Clear of the right-hand icon's 22 pt hit area.
    static let trailingReserve: CGFloat = TrafficLightLayout.trailingIconCenterFromEdge + 11 + 6

    /// `point` in window coordinates (origin bottom-left), as AppKit reports clicks.
    static func contains(_ point: CGPoint, windowSize: CGSize) -> Bool {
        let fromTop = windowSize.height - point.y
        return fromTop >= 0 && fromTop <= WindowLayout.titleBarHeight
            && point.x > start && point.x < windowSize.width - trailingReserve
    }
}

/// Double-click zoom as a pure decision: maximize to the usable screen, or go back. Going back uses the size the
/// window had before maximizing, saved across launches; with nothing saved (the window was relaunched maximized,
/// or maximized by another path) it falls back to the default size centered, never to "nothing happens".
enum ZoomToggle {
    static func isMaximized(_ frame: CGRect, in screen: CGRect) -> Bool {
        abs(frame.minX - screen.minX) < 2 && abs(frame.maxY - screen.maxY) < 2
            && abs(frame.width - screen.width) < 2 && abs(frame.height - screen.height) < 2
    }

    static func next(frame: CGRect, screen: CGRect, previous: CGRect?) -> CGRect {
        guard isMaximized(frame, in: screen) else { return screen }
        if let previous, !isMaximized(previous, in: screen), screen.contains(previous.insetBy(dx: 1, dy: 1)) {
            return previous
        }
        let size = CGSize(width: min(WindowLayout.defaultSize.width, screen.width),
                          height: min(WindowLayout.defaultSize.height, screen.height))
        return CGRect(x: screen.midX - size.width / 2, y: screen.midY - size.height / 2, width: size.width, height: size.height)
    }
}

/// The settings layer, measured on the house reference (card, section column, margin to the window edge).
enum SettingsLayout {
    static let width: CGFloat = 960
    static let height: CGFloat = 660
    static let sidebarWidth: CGFloat = 220
    static let radius: CGFloat = 14
    /// The card shrinks to keep this margin when the window is smaller than card + margins.
    static let windowMargin: CGFloat = 24
}
