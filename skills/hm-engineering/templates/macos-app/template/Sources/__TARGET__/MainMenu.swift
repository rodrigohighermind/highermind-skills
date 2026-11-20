import AppKit

/// The menu bar. Without it, ⌘V, ⌘C, ⌘X, ⌘A and ⌘Z never reach a text field: AppKit delivers them through the
/// Edit menu items and the responder chain, so an app with no menu swallows them in silence (for the keyboard and
/// for anything that pastes into it, like dictation).
@MainActor
enum MainMenu {
    static func install(appName: String) {
        let main = NSMenu()

        let app = NSMenu()
        app.addItem(withTitle: "Sobre o \(appName)", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        app.addItem(.separator())
        app.addItem(withTitle: "Ocultar o \(appName)", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        let others = app.addItem(withTitle: "Ocultar outros", action: #selector(NSApplication.hideOtherApplications(_:)), keyEquivalent: "h")
        others.keyEquivalentModifierMask = [.command, .option]
        app.addItem(withTitle: "Mostrar todos", action: #selector(NSApplication.unhideAllApplications(_:)), keyEquivalent: "")
        app.addItem(.separator())
        app.addItem(withTitle: "Sair do \(appName)", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        add(app, title: appName, to: main)

        let edit = NSMenu(title: "Editar")
        edit.addItem(withTitle: "Desfazer", action: Selector(("undo:")), keyEquivalent: "z")
        let redo = edit.addItem(withTitle: "Refazer", action: Selector(("redo:")), keyEquivalent: "z")
        redo.keyEquivalentModifierMask = [.command, .shift]
        edit.addItem(.separator())
        edit.addItem(withTitle: "Recortar", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        edit.addItem(withTitle: "Copiar", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        edit.addItem(withTitle: "Colar", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        edit.addItem(withTitle: "Selecionar tudo", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        add(edit, title: "Editar", to: main)

        let window = NSMenu(title: "Janela")
        window.addItem(withTitle: "Minimizar", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        window.addItem(withTitle: "Ampliar", action: #selector(NSWindow.performZoom(_:)), keyEquivalent: "")
        window.addItem(withTitle: "Fechar", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        add(window, title: "Janela", to: main)
        NSApp.windowsMenu = window

        NSApp.mainMenu = main
    }

    private static func add(_ menu: NSMenu, title: String, to main: NSMenu) {
        let item = NSMenuItem(title: title, action: nil, keyEquivalent: "")
        item.submenu = menu
        main.addItem(item)
    }

    /// The shortcuts every text field depends on. Read by the test that keeps the menu from regressing.
    static func editShortcuts() -> [String] {
        guard let edit = NSApp.mainMenu?.items.first(where: { $0.submenu?.title == "Editar" })?.submenu else { return [] }
        return edit.items.filter { !$0.isSeparatorItem }.map { ($0.keyEquivalentModifierMask.contains(.shift) ? "⇧" : "") + "⌘" + $0.keyEquivalent.uppercased() }
    }
}
