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
    private var titleClickMonitor: Any?
    private var preZoomFrame: NSRect?

    /// Maximize to the usable screen, or back. The size before maximizing survives relaunch; without it the window
    /// returns to the default size centered, so a double-click always changes the size.
    private func toggleZoom(_ w: NSWindow) {
        guard let screen = w.screen?.visibleFrame else { return }
        let saved = UserDefaults.standard.string(forKey: "preZoomFrame").map(NSRectFromString)
        let target = ZoomToggle.next(frame: w.frame, screen: screen, previous: preZoomFrame ?? saved)
        if ZoomToggle.isMaximized(target, in: screen) {
            preZoomFrame = w.frame
            UserDefaults.standard.set(NSStringFromRect(w.frame), forKey: "preZoomFrame")
        } else {
            preZoomFrame = nil
            UserDefaults.standard.removeObject(forKey: "preZoomFrame")
        }
        w.setFrame(target, display: true, animate: true)
    }

    /// With a transparent title bar and content underneath, SwiftUI swallows the double-click the system uses to zoom.
    /// A double-click in the free band does what the user chose in System Settings (zoom by default, minimize, or
    /// nothing). Returns true when the click was handled.
    private func titleMouseDown(_ e: NSEvent) -> Bool {
        guard let w = window, e.windowNumber == w.windowNumber,
              TitleBand.contains(e.locationInWindow, windowSize: w.frame.size) else { return false }
        if e.clickCount == 1 {  // the title band moves the window; the rest of the content keeps its drags
            w.performDrag(with: e)
            return true
        }
        return titleDoubleClick(clicks: e.clickCount, at: e.locationInWindow, windowNumber: e.windowNumber)
    }

    private func titleDoubleClick(clicks: Int, at p: NSPoint, windowNumber: Int) -> Bool {
        guard let w = window, windowNumber == w.windowNumber, clicks == 2,
              TitleBand.contains(p, windowSize: w.frame.size) else { return false }
        switch UserDefaults.standard.string(forKey: "AppleActionOnDoubleClick") {
        case "Minimize": w.miniaturize(nil)
        case "None": return false
        default: toggleZoom(w)
        }
        return true
    }

    /// QA hook: APP_DEMO_TITLE_DOUBLE_CLICK=1 sends two real double-clicks through the event queue (zoom, then back)
    /// and prints the window frame before, between and after, so the behavior is proven without touching the pointer.
    private func runTitleDoubleClickDemo() {
        guard ProcessInfo.processInfo.environment["APP_DEMO_TITLE_DOUBLE_CLICK"] == "1", let w = window else { return }
        func frame(_ label: String) { print("\(label): \(NSStringFromRect(w.frame))"); fflush(stdout) }
        func doubleClick() {
            let at = NSPoint(x: w.frame.width / 2, y: w.frame.height - WindowLayout.titleBarHeight / 2)
            if let e = NSEvent.mouseEvent(with: .leftMouseDown, location: at, modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime,
                                          windowNumber: w.windowNumber, context: nil, eventNumber: 0, clickCount: 2, pressure: 1) {
                NSApp.postEvent(e, atStart: false)
            }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { frame("before"); doubleClick() }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) { frame("zoomed"); doubleClick() }
        DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) { frame("restored"); NSApp.terminate(nil) }
    }

    func show() {
        if window == nil {
            let w = NSWindow(contentRect: NSRect(origin: .zero, size: WindowLayout.defaultSize),
                             styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
                             backing: .buffered, defer: false)
            w.titlebarAppearsTransparent = true
            w.titleVisibility = .hidden
            w.titlebarSeparatorStyle = .none
            // Only the title band drags the window (see titleMouseDown). Dragging by the whole background
            // steals every drag from the content: selecting text moved the window instead.
            w.isMovableByWindowBackground = false
            w.minSize = NSSize(width: WindowLayout.minWidth, height: WindowLayout.minHeight)
            w.title = "__APP_NAME__"
            w.contentView = NSHostingView(rootView: RootView())
            w.center()
            w.setFrameAutosaveName("MainWindow")
            w.delegate = self
            w.isReleasedWhenClosed = false
            window = w
            titleClickMonitor = NSEvent.addLocalMonitorForEvents(matching: .leftMouseDown) { [weak self] e in
                let handled = MainActor.assumeIsolated { self?.titleMouseDown(e) ?? false }
                return handled ? nil : e
            }
            applyAppearance()
            runTitleDoubleClickDemo()
            appearanceObserver = NotificationCenter.default.addObserver(
                forName: UserDefaults.didChangeNotification, object: nil, queue: .main) { [weak self] _ in
                MainActor.assumeIsolated { self?.applyAppearance() }
            }
        }
        // QA hook: APP_BACKGROUND=1 opens the window behind everything and never takes focus,
        // so screens can be captured while someone is using the Mac.
        if ProcessInfo.processInfo.environment["APP_BACKGROUND"] == "1" {
            window?.orderBack(nil)
        } else {
            window?.makeKeyAndOrderFront(nil)
            NSApp.activate()
        }
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
    @State private var settingsSection = SettingsSection.appearance
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
                    .textSelection(.enabled)  // content text is selectable and copyable, like any Mac document
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
                SettingsModal(section: $settingsSection, onClose: closeModal)
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
        .onReceive(NotificationCenter.default.publisher(for: MainMenu.openSettings)) { _ in withAnimation { modalOpen = true } }
    }

    private func closeModal() { withAnimation { modalOpen = false } }

    /// QA hook: APP_DEMO_MODAL=1 opens and closes the settings layer on a timer (record it frame by frame).
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
        .buttonStyle(.clickable)
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
        .buttonStyle(.clickable)
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
                Text("Ponto de partida: janela nativa, barra lateral recolhível, tema claro e escuro e Ajustes numa camada por cima (⌘,), com transição correta.")
                    .font(Typography.body).foregroundStyle(Tokens.ink2).lineSpacing(3)
                    .frame(maxWidth: 640, alignment: .leading).padding(.top, 8)
                Button(action: openModal) {
                    Text("Abrir ajustes").font(Typography.bodyEmphasis).foregroundStyle(Tokens.canvas)
                        .padding(.horizontal, 16).frame(height: 36)
                        .background(RoundedRectangle(cornerRadius: 9, style: .continuous).fill(Tokens.ink))
                }
                .buttonStyle(.clickable)
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
            .onTapGesture(perform: onTap)  // pointer: exceção, é o fundo da janela inteira, não um alvo
    }
}

// MARK: - Settings

/// The house settings layer: a 960 x 660 card over the dimmed window, a 220 pt section column on the left,
/// one control per row on the right. Add sections to the enum; the column and the page pick them up.
enum SettingsSection: String, CaseIterable, Identifiable {
    case appearance, about
    var id: String { rawValue }
    var title: String {
        switch self {
        case .appearance: return "Aparência"
        case .about: return "Sobre"
        }
    }
    var symbol: String {
        switch self {
        case .appearance: return "circle.lefthalf.filled"
        case .about: return "info.circle"
        }
    }
}

private struct SettingsModal: View {
    @Binding var section: SettingsSection
    let onClose: () -> Void
    @AppStorage("appearance") private var appearance = Appearance.system.rawValue

    var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 4) {
                Text("AJUSTES").font(Typography.caption.weight(.medium)).tracking(1.1).foregroundStyle(Tokens.ink3)
                    .padding(.leading, 10).padding(.bottom, 8)
                ForEach(SettingsSection.allCases) { s in
                    NavItem(title: s.title, symbol: s.symbol, selected: s == section) {
                        withAnimation(Motion.crossfade) { section = s }
                    }
                }
                Spacer()
                Text("__APP_NAME__").font(Typography.caption.weight(.medium)).foregroundStyle(Tokens.ink3).padding(.leading, 10)
            }
            .padding(.vertical, 22).padding(.horizontal, 12)
            .frame(width: SettingsLayout.sidebarWidth)
            .background(Tokens.chrome)

            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    HStack {
                        Text(section.title).font(Typography.pageTitle).foregroundStyle(Tokens.ink)
                        Spacer()
                        Button(action: onClose) {
                            Image(systemName: "xmark").font(.system(size: 13, weight: .medium)).foregroundStyle(Tokens.ink2)
                                .frame(width: 28, height: 28).contentShape(Rectangle())
                        }
                        .buttonStyle(.clickable)
                        .keyboardShortcut(.cancelAction)
                        .help("Fechar (Esc)")
                    }
                    .padding(.bottom, 22)
                    content.id(section).transition(.opacity)
                }
                .padding(28)
            }
            .frame(maxWidth: .infinity)
            .background(Tokens.canvas)
        }
        .frame(maxWidth: SettingsLayout.width, maxHeight: SettingsLayout.height)
        .clipShape(RoundedRectangle(cornerRadius: SettingsLayout.radius, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: SettingsLayout.radius, style: .continuous).strokeBorder(Tokens.border, lineWidth: 1))
        .shadow(color: .black.opacity(0.18), radius: 40, y: 12)
        .padding(SettingsLayout.windowMargin)
    }

    @ViewBuilder private var content: some View {
        switch section {
        case .appearance:
            SettingRow(title: "Tema", detail: "Claro, escuro ou igual ao sistema. A moldura da janela segue o sistema; o conteúdo segue esta escolha.") {
                Picker("Tema", selection: $appearance) {
                    Text("Claro").tag(Appearance.light.rawValue)
                    Text("Escuro").tag(Appearance.dark.rawValue)
                    Text("Sistema").tag(Appearance.system.rawValue)
                }
                .pickerStyle(.segmented).labelsHidden().frame(width: 240).clickable()
            }
        case .about:
            SettingRow(title: "__APP_NAME__", detail: "Versão \(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "de desenvolvimento")") {
                EmptyView()
            }
        }
    }
}

/// One setting: title and a line of detail on the left, a single control on the right.
private struct SettingRow<Trailing: View>: View {
    let title: String
    let detail: String
    @ViewBuilder let trailing: Trailing

    var body: some View {
        HStack(alignment: .center, spacing: 20) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title).font(Typography.bodyEmphasis).foregroundStyle(Tokens.ink)
                Text(detail).font(Typography.caption).foregroundStyle(Tokens.ink3).fixedSize(horizontal: false, vertical: true)
            }
            Spacer()
            trailing
        }
        .padding(.vertical, 16)
    }
}
