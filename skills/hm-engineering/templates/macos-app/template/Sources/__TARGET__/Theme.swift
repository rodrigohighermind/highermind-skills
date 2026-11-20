import AppKit
import SwiftUI

/// Design tokens: every color resolves per appearance (light/dark) in one place, so no view
/// hard-codes a hex. Replace the values with the product's palette; keep the roles.
enum Tokens {
    // Surfaces
    static let chrome = dyn(0xF5F4F0, 0x141413)      // window background + sidebar
    static let canvas = dyn(0xFCFCFB, 0x1A1A1A)      // the rounded content sheet
    static let panel = dyn(0xF5F4F0, 0x202020)       // secondary cards
    static let hover = dyn(0xEEEBE3, 0x2A2A29)       // selection, hover
    static let border = dyn(0xEEEBE3, 0x30302F)

    // Ink
    static let ink = dyn(0x1A1A1A, 0xE9E8E1)
    static let ink2 = dyn(0x30302F, 0xC8C8C2)
    static let ink3 = dyn(0x71716E, 0x9D9C98)        // >= 4.5:1 on canvas (WCAG AA), use for placeholders too

    // Accent
    static let accent = Color(nsColor: NSColor.controlAccentColor)

    private static func dyn(_ light: UInt32, _ dark: UInt32) -> Color {
        Color(nsColor: NSColor(name: nil) { ap in
            let isDark = ap.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
            return NSColor(hex: isDark ? dark : light)
        })
    }
}

/// Type roles. Views use roles, never raw sizes, so a type change happens here once.
enum Typography {
    static let pageTitle = Font.system(size: 25, weight: .semibold)
    static let sectionTitle = Font.system(size: 17, weight: .semibold)
    static let body = Font.system(size: 14.5)
    static let bodyEmphasis = Font.system(size: 14.5, weight: .medium)
    static let nav = Font.system(size: 14, weight: .medium)
    static let caption = Font.system(size: 12.5)
}

/// Motion: one named curve for state changes; durations stretch under APP_SLOW_MOTION for QA.
enum Motion {
    /// QA hook: APP_SLOW_MOTION=8 slows every animation so transitions can be checked frame by frame.
    static let slow = max(0.1, Double(ProcessInfo.processInfo.environment["APP_SLOW_MOTION"] ?? "") ?? 1)
    /// Settled, never bouncy: selection, reveal, switch.
    static let state = Animation.spring(response: 0.3, dampingFraction: 0.9)
    static let crossfade = Animation.easeOut(duration: 0.16)
    static func scaled(_ seconds: Double) -> Double { seconds * slow }
}

/// Every clickable shows the pointing hand. One style for every button (never `.plain` item by item);
/// disabled falls back to the arrow. Rows and cards that are not a Button use `.clickable()`.
struct ClickableStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View { Pressable(configuration: configuration) }

    private struct Pressable: View {
        let configuration: ButtonStyleConfiguration
        @Environment(\.isEnabled) private var enabled
        var body: some View {
            configuration.label
                .opacity(configuration.isPressed ? 0.85 : 1)
                .pointerStyle(enabled ? .link : nil)
        }
    }
}

extension ButtonStyle where Self == ClickableStyle {
    static var clickable: ClickableStyle { ClickableStyle() }
}

extension View {
    /// Pointing hand for a clickable that is not a Button (row, card, custom control).
    func clickable(_ enabled: Bool = true) -> some View { pointerStyle(enabled ? .link : nil) }
}

extension NSColor {
    convenience init(hex: UInt32) {
        self.init(srgbRed: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
                  blue: CGFloat(hex & 0xFF) / 255, alpha: 1)
    }
}
