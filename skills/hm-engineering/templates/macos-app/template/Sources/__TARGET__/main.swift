import AppKit

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    private let main = MainWindowController()

    func applicationDidFinishLaunching(_ notification: Notification) {
        MainMenu.install(appName: "__APP_NAME__")
        main.show()
        // Smoke hook: APP_SMOKE=1 opens the window and quits cleanly after 2 s (exit 0 = launch works).
        if ProcessInfo.processInfo.environment["APP_SMOKE"] == "1" {
            DispatchQueue.main.asyncAfter(deadline: .now() + 2) { NSApp.terminate(nil) }
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        main.show()
        return false
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
