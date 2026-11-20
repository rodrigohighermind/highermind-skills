import Foundation
import Testing

/// Interface text uses whole words: "segunda", "janeiro", "3 minutos", never "seg", "jan", "min".
/// Scans the sources for the formatter and literal patterns that abbreviate. An intentional exception
/// (a quoted code, a unit) is declared on its own line with `// abreviação: exceção <motivo>`.
@Suite struct WordsTests {
    static let patterns: [(String, String)] = [
        (#"\.abbreviated\b"#, "formatador abreviado"),
        (#""[^"]*(?<!E)EEE(?!E)[^"]*""#, "dia da semana curto (EEE)"),
        (#""[^"]*(?<!M)MMM(?!M)[^"]*""#, "mês curto (MMM)"),
        (#""[^"]*\b\d+\s?min\b[^"]*""#, "\"min\" no lugar de minutos"),
        (#""[^"]*\bex\.:"#, "\"ex.:\" no lugar de \"por exemplo\""),
        (#""(?:seg|ter|qua|qui|sex|sáb|dom|jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\.?""#, "dia ou mês abreviado"),
    ]

    @Test func interfaceTextIsNeverAbbreviated() throws {
        let sources = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().appendingPathComponent("Sources")
        var offenders: [String] = []
        for case let url as URL in FileManager.default.enumerator(at: sources, includingPropertiesForKeys: nil)! where url.pathExtension == "swift" {
            for (i, line) in try String(contentsOf: url, encoding: .utf8).components(separatedBy: "\n").enumerated()
            where !line.contains("abreviação: exceção") {
                for (pattern, why) in Self.patterns where line.range(of: pattern, options: .regularExpression) != nil {
                    offenders.append("\(url.lastPathComponent):\(i + 1) \(why)")
                }
            }
        }
        #expect(offenders.isEmpty, "palavra abreviada: \(offenders)")
    }

    @Test func patternsCatchTheUsualSuspects() {
        let bad = [#"f.dateFormat = "EEE, d MMM""#, #"Text("3 min")"#, #"placeholder: "ex.: reunião""#, #"Text("seg")"#, ".formatted(.dateTime.weekday(.abbreviated))"]
        let good = [#"f.dateFormat = "EEEE, d 'de' MMMM""#, #"Text("3 minutos")"#, "static let minWidth: CGFloat = 900"]
        for line in bad { #expect(Self.patterns.contains { line.range(of: $0.0, options: .regularExpression) != nil }, "\(line)") }
        for line in good { #expect(!Self.patterns.contains { line.range(of: $0.0, options: .regularExpression) != nil }, "\(line)") }
    }
}
