"""Tests for the LLM-JSON parser (processors/signal_detector.parse_llm_json).

This parser handles untrusted, fence-wrapped model output and used to be copy-pasted,
untested, across 5 files. It is the single riskiest pure-logic path in Hermes: a bad parse
silently drops a supplier signal. These tests pin its behavior.
"""
import json

import pytest

from processors.signal_detector import parse_llm_json


def test_plain_json():
    assert parse_llm_json('{"signal_type": "FUNDING", "is_significant": true}') == {
        "signal_type": "FUNDING", "is_significant": True
    }


def test_json_fence():
    raw = '```json\n{"signal_type": "ACQUISITION"}\n```'
    assert parse_llm_json(raw)["signal_type"] == "ACQUISITION"


def test_bare_fence():
    raw = '```\n{"urgency": "HIGH"}\n```'
    assert parse_llm_json(raw)["urgency"] == "HIGH"


def test_leading_and_trailing_whitespace():
    assert parse_llm_json('   \n {"a": 1}\n  ')["a"] == 1


def test_fence_with_language_and_spaces():
    assert parse_llm_json('```json   {"a": 2}   ```')["a"] == 2


def test_procurement_shape_roundtrips():
    # The procurement classifier emits affected_suppliers, not tickers.
    payload = {
        "signal_type": "PRICING_CHANGE",
        "is_significant": True,
        "significance_reason": "SaaS list price up 20% — renewal leverage risk",
        "urgency": "HIGH",
        "affected_suppliers": ["Datadog"],
    }
    parsed = parse_llm_json(f"```json\n{json.dumps(payload)}\n```")
    assert parsed["affected_suppliers"] == ["Datadog"]
    assert "affected_tickers" not in parsed  # no trading framing in the model output


def test_empty_raises():
    with pytest.raises(ValueError):
        parse_llm_json("")


def test_none_raises():
    with pytest.raises(ValueError):
        parse_llm_json(None)


def test_garbage_raises_valueerror_not_jsondecode():
    # Callers catch ValueError; a raw JSONDecodeError would slip through.
    with pytest.raises(ValueError):
        parse_llm_json("not json at all {oops")
