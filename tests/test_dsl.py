import pytest

from engine.services.dsl import (
    create_dsl_evaluator,
    evaluate_expression,
    extract_dsl_identifiers,
    validate_expression,
)
from simpleeval import FeatureNotAvailable, FunctionNotDefined


class TestDslParity:
    @pytest.mark.parametrize(
        "expression,values,expected",
        [
            ("a + b", {"a": 2, "b": 3}, 5),
            ("items[0]", {"items": [9]}, 9),
            ('payload["score"]', {"payload": {"score": 5}}, 5),
            ("a if flag else b", {"a": 1, "flag": True, "b": 2}, 1),
            ("not flag", {"flag": False}, True),
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
            "max(a, b)",
            "__import__('os')",
            "obj.__class__",
            "1 in [1, 2, 3]",
        ],
    )
    def test_runtime_and_preflight_both_reject(self, expression):
        names = {"a", "b", "obj", "values"}
        preflight = validate_expression(expression, names, "strict")
        assert preflight.ok is False
        with pytest.raises(Exception):
            evaluate_expression(expression, {n: 1 for n in names})

    def test_function_call_reports_simpleeval_error(self):
        result = validate_expression("max(a, b)", ["a", "b"], "strict")
        assert result.ok is False
        assert any("max" in err.lower() for err in result.errors)

    def test_list_literal_reports_simpleeval_error(self):
        result = validate_expression("1 in [1, 2, 3]", [], "syntax_only")
        assert result.ok is False
        assert any("list" in err.lower() for err in result.errors)

    def test_unknown_checkpoint_identifier_fails_strict(self):
        result = validate_expression("age_check and mystery_signal", ["age_check"], "strict")
        assert result.ok is False
        assert any("mystery_signal" in err for err in result.errors)

    def test_unknown_signal_expression_identifier_warns(self):
        result = validate_expression("request_score > 10", [], "warn_unknown")
        assert result.ok is True
        assert any("request_score" in warn for warn in result.warnings)

    def test_extract_identifiers_uses_ast_not_string_literals(self):
        names = extract_dsl_identifiers('region == "US" and age_check')
        assert names == {"region", "age_check"}

    def test_create_dsl_evaluator_disables_functions(self):
        evaluator = create_dsl_evaluator({"x": 1})
        with pytest.raises((FunctionNotDefined, FeatureNotAvailable, Exception)):
            evaluator.eval("__import__('os')")
