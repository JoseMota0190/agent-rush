"""Tests del banco de desafíos v4 y del scoring.

Ejecutar desde la raíz del proyecto:
    python -m unittest -v test_bank

Cubre:
- 100 desafíos, 8 casos ocultos, determinismo y sensibilidad a la seed.
- Combinaciones de desafíos (una por nivel) para varias seeds.
- Grade: perfecto, incorrecto, timeout, malformado y cantidad incorrecta.
- El harness no recibe las salidas esperadas.
- Fórmulas de scoring, crédito parcial, deduplicación y descalificación.
"""

import json
import unittest

import challenges
import scoring


def _result(cases, mutate=None):
    """Construye la salida del harness a partir de las salidas esperadas."""
    res = []
    for k, _, expected in cases:
        out = expected
        if mutate is not None:
            out = mutate(k, expected)
        res.append({"rc": 0, "out": out, "err": "", "timeout": False})
    return "@@RESULT@@" + json.dumps(res)


class TestScoring(unittest.TestCase):
    def test_weights_and_budgets(self):
        self.assertEqual(scoring.WEIGHTS, {1: 150, 2: 300, 3: 550})
        self.assertEqual(scoring.BUDGETS, {1: 18_000, 2: 28_000, 3: 40_000})
        self.assertEqual(scoring.TOTAL_BUDGET, 100_000)
        self.assertEqual(scoring.RESERVE, 14_000)
        self.assertEqual(scoring.MAX_CASES, 8)
        self.assertEqual(scoring.MAX_ATTEMPTS, 3)

    def test_attempt_factor(self):
        self.assertEqual(scoring.attempt_factor(1), 1.0)
        self.assertEqual(scoring.attempt_factor(2), 0.5)
        self.assertEqual(scoring.attempt_factor(3), 0.0)
        self.assertEqual(scoring.attempt_factor(4), 0.0)

    def test_token_factor(self):
        self.assertEqual(scoring.token_factor(0, 1), 1.0)
        self.assertEqual(scoring.token_factor(9_000, 1), 0.5)
        self.assertEqual(scoring.token_factor(18_000, 1), 0.0)
        self.assertEqual(scoring.token_factor(99_999, 1), 0.0)
        self.assertEqual(scoring.token_factor(-5, 1), 1.0)

    def test_spec_example_all_solved_first_attempt(self):
        levels = [
            {"level": lvl, "solved": True, "attempt": 1, "tokens": int(scoring.BUDGETS[lvl] * 0.4)}
            for lvl in (1, 2, 3)
        ]
        self.assertEqual(scoring.game_score(levels), 940)

    def test_spec_example_level3_third_attempt(self):
        levels = [
            {"level": 1, "solved": True, "attempt": 1, "tokens": scoring.BUDGETS[1]},
            {"level": 2, "solved": True, "attempt": 1, "tokens": scoring.BUDGETS[2]},
            {"level": 3, "solved": True, "attempt": 3, "tokens": scoring.BUDGETS[3]},
        ]
        self.assertAlmostEqual(sum(scoring.level_points(**x) for x in levels), 712.5)

    def test_spec_example_partial_level3(self):
        levels = [
            {"level": 1, "solved": True, "attempt": 1, "tokens": 0},
            {"level": 2, "solved": True, "attempt": 1, "tokens": 0},
            {"level": 3, "solved": False, "tokens": 0, "best_cases": 5},
        ]
        self.assertAlmostEqual(sum(scoring.level_points(**x) for x in levels), 518.75)

    def test_partial_credit_cap(self):
        self.assertAlmostEqual(
            scoring.level_points(3, solved=False, best_cases=8, tokens=0),
            scoring.WEIGHTS[3] * 0.20,
        )
        self.assertAlmostEqual(
            scoring.level_points(3, solved=False, best_cases=4, tokens=0),
            scoring.WEIGHTS[3] * 0.10,
        )

    def test_security_clean(self):
        sec = scoring.security_evaluation([])
        self.assertEqual(sec.status, "CLEAN RUN")
        self.assertEqual(sec.penalty, 0)
        self.assertFalse(sec.critical)

    def test_security_penalty_cap(self):
        events = [
            scoring.SecurityEvent("outbound_network_blocked", 15, deduplication_key=f"e{i}")
            for i in range(20)
        ]
        sec = scoring.security_evaluation(events)
        self.assertEqual(sec.status, "PENALIZED")
        self.assertEqual(sec.penalty, scoring.SECURITY_PENALTY_CAP)

    def test_security_deduplication(self):
        events = [
            scoring.SecurityEvent("outbound_network_blocked", 15, deduplication_key="same"),
            scoring.SecurityEvent("outbound_network_blocked", 15, deduplication_key="same"),
        ]
        sec = scoring.security_evaluation(events)
        self.assertEqual(sec.penalty, 15)
        self.assertEqual(sec.ignored_duplicates, 1)

    def test_security_critical(self):
        events = [scoring.SecurityEvent("sandbox_escape", 0, severity="critical")]
        sec = scoring.security_evaluation(events)
        self.assertEqual(sec.status, "DISQUALIFIED")
        self.assertTrue(sec.critical)
        self.assertEqual(scoring.final_score(1000, sec), 0)

    def test_score_game_report(self):
        report = scoring.score_game(
            [{"level": 1, "solved": True, "attempt": 1, "tokens": 0}],
            [scoring.SecurityEvent("outbound_network_blocked", 15, deduplication_key="x")],
        )
        self.assertEqual(report["performance_score"], 150)
        self.assertEqual(report["final_score"], 135)
        self.assertEqual(report["security"]["status"], "PENALIZED")


class TestChallengeBank(unittest.TestCase):
    def test_hand_cases(self):
        for cid, inp, exp in challenges.HAND:
            with self.subTest(cid=cid):
                self.assertEqual(
                    challenges.norm(challenges.POOL[cid].ref(inp)),
                    challenges.norm(exp),
                )

    def test_registry_shape(self):
        self.assertEqual(len(challenges.POOL), 100)
        self.assertEqual(set(challenges.LEVELS), {1, 2, 3})
        self.assertEqual(sum(len(v) for v in challenges.LEVELS.values()), 100)
        for lvl in (1, 2, 3):
            self.assertGreaterEqual(len(challenges.LEVELS[lvl]), 30)
        for cid, cls in challenges.POOL.items():
            self.assertEqual(cls.id, cid)
            self.assertIn(cls.level, (1, 2, 3))
            self.assertTrue(cls.title)
            self.assertTrue(cls.statement)

    def test_constants(self):
        self.assertEqual(challenges.MAX_ATTEMPTS, 3)
        self.assertEqual(challenges.CASE_TIMEOUT_S, 10)
        self.assertGreaterEqual(
            challenges.CONTAINER_TIMEOUT_S,
            challenges.CASE_TIMEOUT_S * 8,
            "el timeout global debe cubrir los 8 casos",
        )
        self.assertEqual(sum(challenges.LEVEL_BUDGET.values()), 86_000)
        self.assertEqual(challenges.TOKEN_BUDGET_TOTAL, 100_000)

    def test_all_challenges_build_8_cases(self):
        for cid in sorted(challenges.POOL):
            with self.subTest(cid=cid):
                cases = challenges.build_cases(cid, "suite")
                self.assertEqual(len(cases), 8)
                self.assertEqual([k for k, _, _ in cases], list(range(8)))
                for _, inp, exp in cases:
                    self.assertIsInstance(inp, str)
                    self.assertIsInstance(exp, str)
                self.assertTrue(any(inp for _, inp, _ in cases))

    def test_determinism_and_seed_sensitivity(self):
        sample = ["L1-01", "L1-53", "L2-14", "L2-20", "L3-29", "L3-53"]
        for cid in sample:
            with self.subTest(cid=cid):
                a = challenges.build_cases(cid, "seeded")
                b = challenges.build_cases(cid, "seeded")
                c = challenges.build_cases(cid, "seeded-other")
                self.assertEqual(a, b)
                self.assertNotEqual(a, c)

    def test_pick_combinations(self):
        seen = {1: set(), 2: set(), 3: set()}
        for i in range(120):
            picked = challenges.pick(f"combo-{i}")
            self.assertEqual(len(picked), 3)
            for level, cid in zip((1, 2, 3), picked):
                self.assertIn(cid, challenges.POOL)
                self.assertEqual(challenges.POOL[cid].level, level)
                seen[level].add(cid)
        for level in (1, 2, 3):
            self.assertGreaterEqual(len(seen[level]), 25, f"poca cobertura en nivel {level}")

    def test_public_view(self):
        view = challenges.public_view("L1-01")
        self.assertIn("DESAFIO L1-01", view)
        self.assertIn("EJEMPLO (entrada)", view)
        self.assertIn("EJEMPLO (salida)", view)
        self.assertIn("Entrega UN script Python 3.12", view)

    def test_harness_does_not_contain_expected_outputs(self):
        cid, seed = "L1-01", "harness"
        cases = challenges.build_cases(cid, seed)
        harness = challenges.harness_source("print('x')", [inp for _, inp, _ in cases])
        self.assertIn("@@RESULT@@", harness)
        self.assertIn("subprocess.run", harness)
        # Las salidas esperadas no deben viajar al sandbox.
        for _, _, expected in cases:
            if len(expected) >= 12:
                self.assertNotIn(json.dumps(expected), harness)

    def test_grade_perfect(self):
        cid, seed = "L1-01", "grade-ok"
        cases = challenges.build_cases(cid, seed)
        verdict = challenges.grade(cid, seed, _result(cases), cases)
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.failed, [])

    def test_grade_wrong_output(self):
        cid, seed = "L1-01", "grade-bad"
        cases = challenges.build_cases(cid, seed)
        verdict = challenges.grade(
            cid, seed, _result(cases, mutate=lambda k, e: e + "X"), cases
        )
        self.assertFalse(verdict.passed)
        self.assertEqual(len(verdict.failed), 8)

    def test_grade_timeout(self):
        cid, seed = "L1-01", "grade-timeout"
        cases = challenges.build_cases(cid, seed)
        res = [{"rc": 0, "out": exp, "err": "", "timeout": k == 3} for k, _, exp in cases]
        verdict = challenges.grade(cid, seed, "@@RESULT@@" + json.dumps(res), cases)
        self.assertFalse(verdict.passed)
        self.assertEqual(verdict.failed, [3])

    def test_grade_malformed(self):
        cases = challenges.build_cases("L1-01", "grade-malformed")
        verdict = challenges.grade("L1-01", "grade-malformed", "not json", cases)
        self.assertFalse(verdict.passed)
        self.assertEqual(len(verdict.failed), 8)

    def test_grade_wrong_count(self):
        cases = challenges.build_cases("L1-01", "grade-count")
        res = [{"rc": 0, "out": cases[0][2], "err": "", "timeout": False}]
        verdict = challenges.grade("L1-01", "grade-count", "@@RESULT@@" + json.dumps(res), cases)
        self.assertFalse(verdict.passed)
        self.assertEqual(len(verdict.failed), 8)

    def test_grade_normalizes_trailing_spaces(self):
        cid, seed = "L1-01", "grade-norm"
        cases = challenges.build_cases(cid, seed)
        verdict = challenges.grade(
            cid, seed, _result(cases, mutate=lambda k, e: e.replace("\n", "  \n") + "  "), cases
        )
        self.assertTrue(verdict.passed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
