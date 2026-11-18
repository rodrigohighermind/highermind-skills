"""Stdlib tests for the council's safety and protocol mechanics. Run: python3 -m unittest discover -s tests"""
from __future__ import annotations

import http.server
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any, ClassVar
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import council as c

FAKE_ANTHROPIC = "sk-ant-api03-" + "a" * 40  # hm-gate: sentinel fake key proving redaction, never a real credential


def member(**kw: Any) -> c.Member:
    base: dict[str, Any] = {"name": "m", "lineage": "x", "policy": "api", "kind": "http", "price": [3.0, 15.0],
                            "cap_usd": 1.0}
    base.update(kw)
    return c.Member.from_dict(base)


class RedactionTest(unittest.TestCase):
    def test_secrets_are_removed_irreversibly(self) -> None:
        r = c.Redactor()
        text = (f"key {FAKE_ANTHROPIC} aws AKIA{'B' * 16} jwt eyJ{'x' * 12}.{'y' * 12}.{'z' * 12} "
                "password = hunter2 -----BEGIN RSA PRIVATE KEY-----\nabc\n-----END RSA PRIVATE KEY-----")
        out = r.redact(text)
        for leaked in (FAKE_ANTHROPIC, "AKIA", "eyJ", "hunter2", "abc\n"):
            self.assertNotIn(leaked, out)
        self.assertEqual(r.restore(out).count("[SECRET]"), out.count("[SECRET]"))  # secrets never come back

    def test_pii_and_terms_become_stable_pseudonyms_restored_locally(self) -> None:
        r = c.Redactor(terms=["Acme Corp"])
        fake = (  # publish-guard: fixture (invented data that proves the redaction)
            "Mail ana@acme.com and ana@acme.com about Acme Corp, "  # publish-guard: fixture
            "CPF 123.456.789-09, CNPJ 12.345.678/0001-95, "  # publish-guard: fixture
            "tel (11) 98765-4321, fixo (11) 3456-7890, +55 11 91234-5678."  # publish-guard: fixture
        )
        out = r.redact(fake)
        leaks = ("ana@acme.com", "Acme Corp", "123.456.789-09",  # publish-guard: fixture
                 "12.345.678/0001-95", "98765-4321", "3456-7890", "91234-5678")  # publish-guard: fixture
        for leaked in leaks:
            self.assertNotIn(leaked, out)
        self.assertEqual(out.count("[EMAIL_1]"), 2)  # same value, same pseudonym
        self.assertIn("ana@acme.com", r.restore(out))  # publish-guard: fixture

    def test_counterproof_ordinary_text_is_untouched(self) -> None:
        text = "Latência p50 caiu de 700 ms para 450 ms em 40 amostras; versão 2.3.1; build 4471."
        self.assertEqual(c.Redactor().redact(text), text)


class ConfigTest(unittest.TestCase):
    def test_example_config_is_the_builtin_default_and_valid(self) -> None:
        members = c.load_members(c.SKILL_ROOT / "members.example.toml")
        self.assertEqual([m.name for m in members], ["claude", "codex", "gemini", "grok", "local"])
        paid = [m for m in members if m.policy == "api"]
        self.assertTrue(all(m.enabled_env and m.cap_usd > 0 for m in paid))  # paid members are opt-in and capped

    def test_invalid_member_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            c.Member.from_dict({"name": "x", "lineage": "y", "policy": "cloud", "kind": "http"})
        with self.assertRaises(ValueError):
            c.Member.from_dict({"name": "x", "policy": "api", "kind": "http"})

    def test_duplicate_names_rejected(self) -> None:
        f = Path(tempfile.mkdtemp()) / "m.toml"
        f.write_text('[[member]]\nname="a"\nlineage="x"\npolicy="local"\nkind="http"\n' * 2, encoding="utf-8")
        with self.assertRaises(ValueError):
            c.load_members(f)

    def test_dig_paths(self) -> None:
        data = {"candidates": [{"content": {"parts": [{"text": "a"}, {"text": "b"}]}}], "u": {"n": 3}}
        self.assertEqual(c.dig(data, "candidates.0.content.parts.*.text"), "ab")
        self.assertEqual(c.dig(data, "u.n"), 3)
        self.assertIsNone(c.dig(data, "candidates.5.content"))


class PolicyTest(unittest.TestCase):
    API = member(name="grok", policy="api")
    CLI = member(name="claude", policy="subscription", kind="cli")
    LOCAL = member(name="local", policy="local")

    def test_confidential_never_reaches_third_party_api(self) -> None:
        for allow_api in (False, True):
            ok, why = c.allowed(self.API, "confidential", allow_api=allow_api, allow_cli=True)
            self.assertFalse(ok)
            self.assertIn("never", why)

    def test_internal_needs_explicit_api_opt_in(self) -> None:
        self.assertFalse(c.allowed(self.API, "internal", allow_api=False, allow_cli=False)[0])
        self.assertTrue(c.allowed(self.API, "internal", allow_api=True, allow_cli=False)[0])  # counterproof

    def test_confidential_cli_needs_opt_in_and_local_always_allowed(self) -> None:
        self.assertFalse(c.allowed(self.CLI, "confidential", allow_api=False, allow_cli=False)[0])
        self.assertTrue(c.allowed(self.CLI, "confidential", allow_api=False, allow_cli=True)[0])
        self.assertTrue(c.allowed(self.LOCAL, "confidential", allow_api=False, allow_cli=False)[0])

    def test_counterproof_public_goes_everywhere(self) -> None:
        for m in (self.API, self.CLI, self.LOCAL):
            self.assertTrue(c.allowed(m, "public", allow_api=False, allow_cli=False)[0])

    def test_paid_member_is_opt_in_by_env_and_needs_its_key(self) -> None:
        m = member(name="grok", enabled_env="COUNCIL_ENABLE_GROK", requires={"env": ["XAI_API_KEY"]})
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COUNCIL_ENABLE_GROK", None)
            os.environ.pop("XAI_API_KEY", None)
            self.assertFalse(c.configured(m)[0])
            os.environ["COUNCIL_ENABLE_GROK"] = "1"
            self.assertFalse(c.configured(m)[0])  # still no key
            os.environ["XAI_API_KEY"] = "x"
            self.assertTrue(c.configured(m)[0])  # counterproof

    def test_paid_member_without_cap_is_never_enabled(self) -> None:
        self.assertFalse(c.configured(member(cap_usd=0.0))[0])


class BudgetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = c.Ledger(Path(tempfile.mkdtemp()) / "ledger.jsonl")

    def test_reservation_over_cap_is_refused(self) -> None:
        self.assertIsNotNone(self.ledger.reserve("grok", 0.6, limit=1.0))
        self.assertIsNone(self.ledger.reserve("grok", 0.6, limit=1.0))  # 1.2 > 1.0

    def test_counterproof_settled_cost_frees_the_unused_part(self) -> None:
        rid = self.ledger.reserve("grok", 0.6, limit=1.0)
        assert rid is not None
        self.ledger.settle("grok", rid, 0.05)
        self.assertAlmostEqual(self.ledger.committed("grok"), 0.05)
        self.assertIsNotNone(self.ledger.reserve("grok", 0.6, limit=1.0))  # 0.65 <= 1.0

    def test_caps_are_per_member(self) -> None:
        self.assertIsNotNone(self.ledger.reserve("grok", 0.9, limit=1.0))
        self.assertIsNotNone(self.ledger.reserve("gemini", 0.9, limit=1.0))

    def test_parallel_reservations_never_cross_the_cap(self) -> None:
        got: list[str | None] = []
        def take() -> None:
            got.append(self.ledger.reserve("grok", 0.3, limit=1.0))
        threads = [threading.Thread(target=take) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(sum(1 for g in got if g), 3)  # 3 * 0.3 = 0.9; the 4th would be 1.2

    def test_over_budget_member_is_skipped_not_called(self) -> None:
        with mock.patch.object(c, "call_member") as call:
            ans = c._ask(member(name="grok", cap_usd=0.0001), "brief", self.ledger, "grok")
        call.assert_not_called()
        self.assertFalse(ans.ok)
        self.assertIn("budget", ans.error)

    def test_failed_call_settles_the_full_reservation(self) -> None:
        m = member(name="grok")
        with mock.patch.object(c, "call_member", side_effect=RuntimeError("timeout")):
            c._ask(m, "brief", self.ledger, "grok")
        full = c.worst_case_usd(m, len("brief") + len(c.MEMBER_SYSTEM))
        self.assertAlmostEqual(self.ledger.committed("grok"), full)


ANSWER = {"summary": "s", "recommendation": "do x", "claims": [{"text": "c1", "basis": "hypothesis"}]}


class _Stub(http.server.BaseHTTPRequestHandler):
    last: ClassVar[dict[str, Any]] = {}

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Stub.last = {"body": body, "auth": self.headers.get("Authorization")}
        out = json.dumps({"choices": [{"message": {"content": json.dumps(ANSWER)}}],
                          "usage": {"prompt_tokens": 1000, "completion_tokens": 2000}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *_: Any) -> None:
        return


class MemberCallTest(unittest.TestCase):
    def test_cli_member_gets_system_and_prompt_and_no_paid_keys(self) -> None:
        script = ("import json,os,sys; print(json.dumps({'recommendation': sys.argv[2], 'claims': [], "
                  "'leak': os.environ.get('ANTHROPIC_API_KEY')}))")
        m = member(name="fake", policy="subscription", kind="cli",
                   command=[sys.executable, "-c", script, "{system}", "{prompt}"])
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "real-looking"}):
            text, usd = c.call_member(m, "SYS", "the brief")
        data = c.parse_answer(text)
        self.assertEqual(data["recommendation"], "the brief")
        self.assertIsNone(data["leak"])
        self.assertEqual(usd, 0.0)

    def test_http_member_template_auth_text_and_cost(self) -> None:
        srv = http.server.HTTPServer(("127.0.0.1", 0), _Stub)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            m = member(name="stub", url=f"http://127.0.0.1:{srv.server_port}/v1",
                       headers={"Authorization": "Bearer ${STUB_KEY}"},
                       body={"model": "x", "max_tokens": "{max_tokens}",
                             "messages": [{"role": "system", "content": "{system}"},
                                          {"role": "user", "content": "{prompt}"}]},
                       text="choices.0.message.content", usage_in="usage.prompt_tokens",
                       usage_out=["usage.completion_tokens"])
            with mock.patch.dict(os.environ, {"STUB_KEY": "k123"}):
                text, usd = c.call_member(m, "SYS", "hello")
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertEqual(c.parse_answer(text)["recommendation"], "do x")
        self.assertEqual(_Stub.last["auth"], "Bearer k123")
        self.assertIsInstance(_Stub.last["body"]["max_tokens"], int)
        self.assertEqual(_Stub.last["body"]["messages"][1]["content"], "hello")
        self.assertAlmostEqual(usd, (1000 * 3.0 + 2000 * 15.0) / 1e6)


class ProtocolTest(unittest.TestCase):
    def test_parse_answer_extracts_json_from_fenced_text(self) -> None:
        d = c.parse_answer('Here:\n```json\n{"recommendation": "x", "claims": [{"text": "a"}]}\n```')
        self.assertEqual(d["recommendation"], "x")

    def test_non_json_answer_is_kept_as_a_hypothesis_not_dropped(self) -> None:
        d = c.parse_answer("Just prose, no JSON at all.")
        self.assertEqual(d["claims"][0]["basis"], "hypothesis")
        self.assertIn("prose", d["claims"][0]["text"])

    def test_divergence(self) -> None:
        a = c.Answer("a", "x", True, data={"recommendation": "migrate the encoder to buckets of five seconds"})
        b = c.Answer("b", "y", True, data={"recommendation": "migrate the encoder to buckets of five seconds now"})
        d = c.Answer("d", "z", True, data={"recommendation": "rewrite the service in another language entirely"})
        self.assertFalse(c.diverged([a, b]))
        self.assertTrue(c.diverged([a, d]))
        self.assertTrue(c.diverged([a]))  # a missing member is not agreement

    def test_single_lineage_is_declared_degraded_and_lineages_come_first(self) -> None:
        ms = [member(name="a1", lineage="a", policy="local"), member(name="a2", lineage="a", policy="local")]
        self.assertTrue(c.plan_members(ms, "internal", allow_api=False, allow_cli=False).degraded)
        ms = [member(name="a1", lineage="a", policy="local"), member(name="a2", lineage="a", policy="local"),
              member(name="b1", lineage="b", policy="local")]
        plan = c.plan_members(ms, "internal", allow_api=False, allow_cli=False)
        self.assertFalse(plan.degraded)
        self.assertEqual([m.name for m in plan.members][:2], ["a1", "b1"])  # first two = two lineages

    def test_records_are_private(self) -> None:
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": tempfile.mkdtemp()}):
            d = c.state_dir()
            f = d / "x.json"
            c._write_private(f, "{}")
            self.assertEqual(d.stat().st_mode & 0o777, 0o700)
            self.assertEqual(f.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
