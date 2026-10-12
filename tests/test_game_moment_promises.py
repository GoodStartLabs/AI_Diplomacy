"""Offline checks for the distinction between an attack and a no-attack promise.

Expected labels were reviewed with a Diplomacy player: issuing an attack is an
attempt, even when the move bounces. Deception remains legal game strategy.
"""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import patch

import pytest


@pytest.fixture(scope="module")
def analyzer_module():
    # The promise methods need no model providers. Isolate the unused factory so
    # these tests do not require every provider SDK, API keys or network access.
    client_module = ModuleType("ai_diplomacy.clients")

    def no_model_calls(*args, **kwargs):
        raise AssertionError("Promise checks must not call a model provider")

    client_module.load_model_client = no_model_calls
    source = Path(__file__).resolve().parents[1] / "analyze_game_moments.py"
    spec = importlib.util.spec_from_file_location("_promise_analyzer_test", source)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {
        "ai_diplomacy.clients": client_module,
        spec.name: module,
    }):
        spec.loader.exec_module(module)
    return module


@pytest.fixture
def analyzer(analyzer_module, tmp_path):
    return analyzer_module.GameAnalyzer(str(tmp_path))


@pytest.mark.parametrize("message", [
    "I will attack BEL this turn.",
    "France will attack BEL.",
    "I WILL ATTACK BEL.",
])
def test_announced_attack_is_not_a_no_attack_promise(analyzer, message):
    promises = analyzer.extract_promises_from_message(message)
    assert not any(p["type"] == "no_attack" for p in promises)


@pytest.mark.parametrize("message", [
    "I won't attack BEL this turn.",
    "I will not attack BEL this turn.",
    "I WILL NOT ATTACK BEL.",
])
def test_negative_attack_promise_is_still_detected(analyzer, message):
    promises = analyzer.extract_promises_from_message(message)
    no_attack = [p for p in promises if p["type"] == "no_attack"]
    assert len(no_attack) == 1
    assert no_attack[0]["details"] == ("bel",)


@pytest.mark.parametrize("message", [
    "I will attack BEL, but I will not attack HOL.",
    "I won't attack HOL, but I will attack BEL.",
])
def test_mixed_statement_keeps_only_the_negative_commitment(analyzer, message):
    promises = analyzer.extract_promises_from_message(message)
    no_attack = [p for p in promises if p["type"] == "no_attack"]
    assert [p["details"] for p in no_attack] == [("hol",)]


@pytest.mark.parametrize("message", [
    "No moves on BEL.",
    "No attacks against BEL.",
    "Stay out of BEL.",
])
def test_other_no_attack_phrasings_are_preserved(analyzer, message):
    promises = analyzer.extract_promises_from_message(message)
    no_attack = [p for p in promises if p["type"] == "no_attack"]
    assert [p["details"] for p in no_attack] == [("bel",)]


@pytest.mark.parametrize("message", [
    "I won't attack BEL this turn.",
    "I will not attack BEL this turn.",
])
@pytest.mark.parametrize("order, expected_lie", [
    ("A PIC H", False),
    ("A PIC - BEL", True),
])
def test_negative_commitment_is_judged_by_order(analyzer, message, order, expected_lie):
    promise = next(p for p in analyzer.extract_promises_from_message(message)
                   if p["type"] == "no_attack")
    lie = analyzer.check_promise_against_orders(
        promise, [order], "", "FRANCE", "GERMANY", "S1901M"
    )
    assert (lie is not None) == expected_lie


@pytest.mark.parametrize("result", [[], ["bounce"]])
def test_announced_attack_does_not_create_a_lie_even_if_blocked(analyzer, result):
    phase = {
        "name": "S1901M",
        "messages": [{
            "sender": "FRANCE", "recipient": "GERMANY",
            "message": "I will attack BEL this turn.",
        }],
        "orders": {"FRANCE": ["A PIC - BEL"]},
        "results": {"A PIC": result},
    }
    assert analyzer.detect_lies_in_phase(phase) == []


@pytest.mark.parametrize("result", [[], ["bounce"]])
def test_forbidden_attack_is_a_broken_promise_even_if_blocked(analyzer, result):
    phase = {
        "name": "S1901M",
        "messages": [{
            "sender": "FRANCE", "recipient": "GERMANY",
            "message": "I will not attack BEL this turn.",
        }],
        "orders": {"FRANCE": ["A PIC - BEL"]},
        "results": {"A PIC": result},
    }
    lies = analyzer.detect_lies_in_phase(phase)
    assert len(lies) == 1
    assert lies[0].liar == "FRANCE"
    assert lies[0].recipient == "GERMANY"
