import AppKit
import SwiftUI

// MARK: - Window controller

enum Appearance: String, CaseIterable, Identifiable {
    case light, dark, system
    var id: String { rawValue }
}

@MainActor
final class MainWindowController: NSObject, NSWindowDelegate {
    private var window: NSWindow?
    private var appearanceObserver: NSObjectProtocol?

    func show() {
        if window == nil {
            let w = NSWindow(contentRect: NSRect(origin: .zero, size: WindowLayout.defaultSize),
                             styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
                             backing: .buffered, defer: false)
            w.titlebarAppearsTransparent = true
            w.titleVisibility = .hidden
            w.titlebarSeparatorStyle = .none
            w.isMovableByWindowBackground = true
            w.minSize = NSSize(width: WindowLayout.minWidth, height: WindowLayout.minHeight)
            w.title = "__APP_NAME__"
            w.contentView = NSHostingView(rootView: RootView())
            w.center()
            w.setFrameAutosaveName("MainWindow")
            w.delegate = self
            w.isReleasedWhenClosed = false
            window = w
            applyAppearance()
            appearanceObserver = NotificationCenter.default.addObserver(
                forName: UserDefaults.didChangeNotification, object: nil, queue: .main) { [weak self] _ in
                MainActor.assumeIsolated { self?.applyAppearance() }
            }
        }
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate()
        placeTrafficLights()
        DispatchQueue.main.async { [weak self] in self?.placeTrafficLights() }  // after the first layout pass
    }

    /// The app theme applies to the content; the window chrome follows the system (native behavior).
    private func applyAppearance() {
        window?.appearance = nil
        let choice = Appearance(rawValue: UserDefaults.standard.string(forKey: "appearance") ?? "") ?? .system
        switch choice {
        case .light: window?.contentView?.appearance = NSAppearance(named: .aqua)
        case .dark: window?.contentView?.appearance = NSAppearance(named: .darkAqua)
        case .system: window?.contentView?.appearance = nil
        }
    }

    /// Native window controls at the layout geometry, in window coordinates (origin bottom-left).
    func placeTrafficLights() {
        guard let w = window else { return }
        let kinds: [NSWindow.ButtonType] = [.closeButton, .miniaturizeButton, .zoomButton]
        for (i, kind) in kinds.enumerated() {
            guard let b = w.standardWindowButton(kind), let sv = b.superview else { continue }
            let c = TrafficLightLayout.center(index: i)
            let target = NSPoint(x: c.x, y: w.frame.height - c.y)
            let now = sv.convert(b.frame, to: nil)
            let dx = target.x - now.midX, dy = target.y - now.midY
            b.setFrameOrigin(NSPoint(x: b.frame.origin.x + dx, y: b.frame.origin.y + (sv.isFlipped ? -dy : dy)))
        }
    }

    func windowDidResize(_ notification: Notification) { placeTrafficLights() }
    func windowDidBecomeKey(_ notification: Notification) { placeTrafficLights() }
    func windowDidResignKey(_ notification: Notification) { placeTrafficLights() }
    func windowDidExitFullScreen(_ notification: Notification) { placeTrafficLights() }
}

// MARK: - Root

enum Page: String, CaseIterable, Identifiable {
    case home  // add cases here; the sidebar and the crossfade pick them up
    var id: String { rawValue }
    var title: String {
        switch self {
        case .home: return "Início"
        }
    }
    var symbol: String {
        switch self {
        case .home: return "square.grid.2x2"
        }
    }
}

struct RootView: View {
    @State private var page = Page(rawValue: ProcessInfo.processInfo.environment["APP_PREVIEW"] ?? "") ?? .home
    @State private var modalOpen = false
    @AppStorage("sidebarCollapsed") private var sidebarCollapsed = false
    @AppStorage("appearance") private var appearance = Appearance.system.rawValue
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        ZStack {
            HStack(spacing: 0) {
                if !sidebarCollapsed {
                    Sidebar(page: $page)
                        .frame(width: WindowLayout.sidebarWidth)
                        .transition(.move(edge: .leading).combined(with: .opacity))
                }
                VStack(spacing: 0) {
                    Color.clear.frame(height: WindowLayout.titleBarHeight)
                    ZStack {
                        switch page {
                        case .home: HomePage(openModal: { withAnimation { modalOpen = true } })
                        }
                    }
                    .id(page)
                    .transition(.opacity)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Tokens.canvas)
                    .clipShape(RoundedRectangle(cornerRadius: WindowLayout.sheetRadius, style: .continuous))
                    .overlay(RoundedRectangle(cornerRadius: WindowLayout.sheetRadius, style: .continuous)
                        .strokeBorder(Tokens.border, lineWidth: 1))
                    .padding(.trailing, WindowLayout.sheetInset)
                    .padding(.bottom, WindowLayout.sheetInset)
                    .padding(.leading, sidebarCollapsed ? WindowLayout.sheetInset : 0)
                }
            }
            TitleBarControls(sidebarCollapsed: $sidebarCollapsed, appearance: $appearance)
            // A layer above the window: scrim and card are separate layers. The scrim only fades and always
            // covers the whole window (scaling it with the card exposes undimmed edges mid-transition).
            if modalOpen {
                Scrim(onTap: closeModal)
                    .transition(.opacity.animation(.easeOut(duration: Motion.scaled(0.24))))
                    .zIndex(1)
                ExampleModal(onClose: closeModal)
                    .transition(reduceMotion ? .opacity : .asymmetric(
                        // Per-property animations: opacity is quick (no ghosting of the page behind),
                        // scale and lift carry the motion; exit leaves together with the scrim.
                        insertion: AnyTransition.opacity.animation(.easeOut(duration: Motion.scaled(0.08)))
                            .combined(with: AnyTransition.scale(scale: 0.96).combined(with: .offset(y: 8))
                                .animation(.spring(response: Motion.scaled(0.34), dampingFraction: 0.86))),
                        removal: AnyTransition.opacity.animation(.easeIn(duration: Motion.scaled(0.16)))
                            .combined(with: AnyTransition.scale(scale: 0.97)
                                .animation(.easeOut(duration: Motion.scaled(0.2))))))
                    .zIndex(2)
            }
        }
        .background(Tokens.chrome)
        .ignoresSafeArea()
        .animation(Motion.crossfade, value: page)
        .animation(Motion.state, value: sidebarCollapsed)
        .transaction { t in  // QA: APP_SLOW_MOTION slows every animation in the window
            if Motion.slow != 1 { t.animation = t.animation?.speed(1 / Motion.slow) }
        }
        .onAppear(perform: runDemoIfRequested)
    }

    private func closeModal() { withAnimation { modalOpen = false } }

    /// QA hook: APP_DEMO_MODAL=1 opens and closes the modal on a timer (record it frame by frame).
    private func runDemoIfRequested() {
        guard ProcessInfo.processInfo.environment["APP_DEMO_MODAL"] == "1" else { return }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { withAnimation { modalOpen = true } }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5 + 4 * Motion.slow) { closeModal() }
    }
}

// MARK: - Title bar

private struct TitleBarControls: View {
    @Binding var sidebarCollapsed: Bool
    @Binding var appearance: String

    var body: some View {
        ZStack(alignment: .topLeading) {
            BarIcon(help: sidebarCollapsed ? "Mostrar barra lateral" : "Esconder barra lateral") {
                withAnimation(Motion.state) { sidebarCollapsed.toggle() }
            } label: { SidebarGlyph() }
            .position(TrafficLightLayout.sidebarToggleCenter)
            BarIcon(help: "Alternar tema") {
                appearance = isDark ? Appearance.light.rawValue : Appearance.dark.rawValue
            } label: {
                Image(systemName: isDark ? "sun.max" : "moon").font(.system(size: 15, weight: .regular))
            }
            .frame(maxWidth: .infinity, alignment: .trailing)
            .padding(.trailing, TrafficLightLayout.trailingIconCenterFromEdge - 11)
            .frame(height: TrafficLightLayout.centerYFromTop * 2)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    @Environment(\.colorScheme) private var scheme
    private var isDark: Bool { scheme == .dark }
}

/// A title-bar glyph in a 22 pt hit area with a quiet hover.
private struct BarIcon<Label: View>: View {
    let help: String
    let action: () -> Void
    @ViewBuilder let label: Label
    @State private var hovering = false

    var body: some View {
        Button(action: action) {
            label
                .foregroundStyle(Tokens.ink)
                .frame(width: 22, height: 22)
                .background(RoundedRectangle(cornerRadius: 6, style: .continuous).fill(hovering ? Tokens.hover : .clear))
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .help(help)
        .onHover { hovering = $0 }
        .animation(.easeOut(duration: 0.12), value: hovering)
    }
}

/// Panel glyph: rounded rectangle with a left divider, 1.5 pt stroke.
private struct SidebarGlyph: View {
    var body: some View {
        Canvas { ctx, size in
            let r = CGRect(x: 0.75, y: 0.75, width: size.width - 1.5, height: size.height - 1.5)
            ctx.stroke(Path(roundedRect: r, cornerRadius: 3.2), with: .foreground, lineWidth: 1.5)
            var line = Path()
            line.move(to: CGPoint(x: size.width * 0.38, y: 0.75))
            line.addLine(to: CGPoint(x: size.width * 0.38, y: size.height - 0.75))
            ctx.stroke(line, with: .foreground, lineWidth: 1.5)
        }
        .frame(width: 15.5, height: 15.5)
    }
}

// MARK: - Sidebar

private struct Sidebar: View {
    @Binding var page: Page

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Spacer().frame(height: 61)
            Text("__APP_NAME__").font(.system(size: 21, weight: .semibold)).foregroundStyle(Tokens.ink)
                .lineLimit(1).minimumScaleFactor(0.7)
                .padding(.leading, 10).padding(.bottom, 23)
            ForEach(Page.allCases) { p in
                NavItem(title: p.title, symbol: p.symbol, selected: p == page) {
                    withAnimation(Motion.crossfade) { page = p }
                }
            }
            Spacer()
        }
        .padding(.horizontal, 12)
    }
}

private struct NavItem: View {
    let title: String
    let symbol: String
    let selected: Bool
    let action: () -> Void
    @State private var hovering = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 11) {
                Image(systemName: symbol).font(.system(size: 14, weight: .medium)).frame(width: 18)
                Text(title).font(Typography.nav)
                Spacer()
            }
            .foregroundStyle(Tokens.ink)
            .padding(.horizontal, 10)
            .frame(height: 35)
            .background(RoundedRectangle(cornerRadius: 8, style: .continuous)
                .fill(selected ? Tokens.hover : (hovering ? Tokens.hover.opacity(0.55) : .clear)))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { hovering = $0 }
    }
}

// MARK: - Example page and modal

private struct HomePage: View {
    let openModal: () -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Text("Início").font(Typography.pageTitle).foregroundStyle(Tokens.ink)
                Text("Ponto de partida: janela nativa, barra lateral recolhível, tema claro e escuro e uma camada por cima com transição correta.")
                    .font(Typography.body).foregroundStyle(Tokens.ink2).lineSpacing(3)
                    .frame(maxWidth: 640, alignment: .leading).padding(.top, 8)
                Button(action: openModal) {
                    Text("Abrir exemplo").font(Typography.bodyEmphasis).foregroundStyle(Tokens.canvas)
                        .padding(.horizontal, 16).frame(height: 36)
                        .background(RoundedRectangle(cornerRadius: 9, style: .continuous).fill(Tokens.ink))
                }
                .buttonStyle(.plain)
                .padding(.top, 24)
            }
            .padding(.horizontal, 48).padding(.top, 44).padding(.bottom, 48)
            .frame(maxWidth: WindowLayout.contentMaxWidth, alignment: .leading)
            .frame(maxWidth: .infinity, alignment: .center)
        }
    }
}

/// Dims the whole window behind a modal; tap to dismiss.
private struct Scrim: View {
    let onTap: () -> Void
    @Environment(\.colorScheme) private var scheme
    var body: some View {
        Color.black.opacity(scheme == .dark ? 0.5 : 0.3)
            .ignoresSafeArea()
            .contentShape(Rectangle())
            .onTapGesture(perform: onTap)
    }
}

private struct ExampleModal: View {
    let onClose: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Exemplo").font(Typography.sectionTitle).foregroundStyle(Tokens.ink)
                Spacer()
                Button(action: onClose) {
                    Image(systemName: "xmark").font(.system(size: 13, weight: .medium)).foregroundStyle(Tokens.ink2)
                        .frame(width: 28, height: 28).contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .keyboardShortcut(.cancelAction)
                .help("Fechar (Esc)")
            }
            Text("Uma camada por cima: o fundo só escurece e cobre a janela inteira; a caixa aparece sem deixar o texto de trás vazar e sai junto com o fundo.")
                .font(Typography.body).foregroundStyle(Tokens.ink2).lineSpacing(3)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(24)
        .frame(width: 480)
        .background(RoundedRectangle(cornerRadius: 14, style: .continuous).fill(Tokens.canvas))
        .overlay(RoundedRectangle(cornerRadius: 14, style: .continuous).strokeBorder(Tokens.border, lineWidth: 1))
        .shadow(color: .black.opacity(0.18), radius: 40, y: 12)
    }
}
