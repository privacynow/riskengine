import pytest

from engine.services.dsl import evaluate_expression, validate_expression


class TestDslParity:
    @pytest.mark.parametrize(
        "expression,values,expected",
        [
            ("a + b", {"a": 2, "b": 3}, 5),
            ("a - b", {"a": 5, "b": 2}, 3),
            ("a * b", {"a": 4, "b": 2}, 8),
            ("a / b", {"a": 9, "b": 3}, 3),
            ("a // b", {"a": 7, "b": 2}, 3),
            ("a % b", {"a": 7, "b": 3}, 1),
            ("a ** b", {"a": 2, "b": 3}, 8),
            ("not flag", {"flag": False}, True),
            ("-a", {"a": 4}, -4),
            ("age_check and score > 80", {"age_check": True, "score": 90}, True),
            ('region == "US"', {"region": "US"}, True),
            ("1 in values", {"values": [1, 2, 3]}, True),
        ],
    )
    def test_runtime_and_preflight_both_accept(self, expression, values, expected):
        preflight = validate_expression(expression, values.keys(), "strict")
        assert preflight.ok, preflight.errors
        assert evaluate_expression(expression, values) == expected

    @pytest.mark.parametrize(
        "expression",
        [
            "a in [1, 2, 3]",
            "a in (1, 2, 3)",
            "items[0]",
            "a if flag else b",
            "max(a, b)",
        ],
    )
    def test_runtime_and_preflight_both_reject(self, expression):
        preflight = validate_expression(expression, ["a", "items", "flag", "b"], "strict")
        assert preflight.ok is False
        with pytest.raises(Exception):
            evaluate_expression(expression, {"a": 1, "items": [1], "flag": True, "b": 2})

    def test_unknown_checkpoint_identifier_fails_strict(self):
        result = validate_expression("age_check and mystery_signal", ["age_check"], "strict")
        assert result.ok is False
        assert any("mystery_signal" in err for err in result.errors)

    def test_unknown_signal_expression_identifier_warns(self):
        result = validate_expression("request_score > 10", [], "warn_unknown")
        assert result.ok is True
        assert any("request_score" in warn for warn in result.warnings)
