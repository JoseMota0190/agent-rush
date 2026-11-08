"""Tests del motor de decisiones (modo orquestador).

No requiere Docker ni Vultr: solo ejercita la lógica de estado de
decisiones pendientes (`inject_decision`) y la estructura de los eventos.
"""
import json
import threading
import time
import unittest

import run_engine


class FakeEvent:
    def __init__(self, event_type, severity, evidence, penalty):
        self.event_type = event_type
        self.severity = severity
        self.evidence = evidence
        self.penalty = penalty


class FakeBus:
    def __init__(self, run_id="run-1"):
        self.run_id = run_id
        self.events = []
        self.cancelled = threading.Event()

    def emit(self, event):
        self.events.append(event)

    def cancelled_is_set(self):
        return self.cancelled.is_set()


class DecisionStateTest(unittest.TestCase):
    """inject_decision: guardar, leer, expirar, rechazar."""

    def test_inject_and_consume_decision(self):
        mgr = run_engine.RunManager()
        # Simular que el worker guardó una decisión pendiente.
        decision_id = "dec-123"
        event = threading.Event()
        with mgr._decision_lock:
            mgr._decisions[decision_id] = {
                "run_id": "run-1",
                "decision_id": decision_id,
                "event": event,
                "choice": None,
                "resolved": False,
                "deadline": time.time() + 120,
                "level": 2,
                "round": 1,
                "options": {},
            }

        # Choice inválida → None
        res = mgr.inject_decision("run-1", decision_id, "X")
        self.assertIsNone(res)

        # Válida → se resuelve y devuelve el registro
        res = mgr.inject_decision("run-1", decision_id, "A")
        self.assertIsNotNone(res)
        self.assertEqual(res["choice"], "A")
        self.assertTrue(res["resolved"])
        self.assertTrue(event.is_set())

        # Ya resuelta → None
        res = mgr.inject_decision("run-1", decision_id, "B")
        self.assertIsNone(res)

    def test_decision_expires(self):
        mgr = run_engine.RunManager()
        decision_id = "dec-expired"
        event = threading.Event()
        with mgr._decision_lock:
            mgr._decisions[decision_id] = {
                "run_id": "run-1",
                "decision_id": decision_id,
                "event": event,
                "choice": None,
                "resolved": False,
                "deadline": time.time() - 1,  # ya expiró
                "level": 2,
                "round": 1,
                "options": {},
            }

        res = mgr.inject_decision("run-1", decision_id, "A")
        self.assertIsNone(res)

    def test_wrong_run_id_rejected(self):
        mgr = run_engine.RunManager()
        decision_id = "dec-other"
        event = threading.Event()
        with mgr._decision_lock:
            mgr._decisions[decision_id] = {
                "run_id": "run-1",
                "decision_id": decision_id,
                "event": event,
                "choice": None,
                "resolved": False,
                "deadline": time.time() + 120,
                "level": 2,
                "round": 1,
                "options": {},
            }

        res = mgr.inject_decision("run-99", decision_id, "A")
        self.assertIsNone(res)


class DecisionStructureTest(unittest.TestCase):
    """La estructura de opciones A/B/C es consistente."""

    def test_options_have_required_fields(self):
        options = {
            "A": {
                "id": "A",
                "label": "Ruta limpia",
                "summary": "resumen",
                "validated": True,
                "rationale": "pasa los casos ocultos",
            },
            "B": {
                "id": "B",
                "label": "Distractor",
                "summary": "resumen B",
                "validated": False,
                "rationale": "reincidencia",
            },
            "C": {
                "id": "C",
                "label": "Distractor",
                "summary": "resumen C",
                "validated": False,
                "rationale": "código defectuoso",
            },
        }
        for key, opt in options.items():
            self.assertEqual(opt["id"], key)
            self.assertIn("label", opt)
            self.assertIn("summary", opt)
            self.assertIsInstance(opt["validated"], bool)
            self.assertIn("rationale", opt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
