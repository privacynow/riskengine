from engine.services.dsl_preflight import extract_dsl_identifiers, preflight_dsl


class TestDslPreflight:
    def test_empty_expression_fails(self):
        result = preflight_dsl("")
        assert result["ok"] is False
        assert "empty" in result["errors"][0].lower()

    def test_valid_expression_with_signal_names(self):
        result = preflight_dsl(
            "age_check and kyc_score > 80",
            signal_names=["age_check", "kyc_score"],
        )
        assert result["ok"] is True
        assert result["errors"] == []

    def test_invalid_syntax_fails(self):
        result = preflight_dsl("age_check and (", signal_names=["age_check"])
        assert result["ok"] is False
        assert result["errors"]

    def test_unknown_signal_identifier_fails(self):
        result = preflight_dsl(
            "age_check and mystery_signal",
            signal_names=["age_check"],
        )
        assert result["ok"] is False
        assert any("mystery_signal" in err for err in result["errors"])

    def test_arithmetic_expression_passes(self):
        result = preflight_dsl("a + b", signal_names=["a", "b"])
        assert result["ok"] is True
        assert result["errors"] == []

    def test_signal_expression_unknown_warns(self):
        result = preflight_dsl(
            "request_score > 10",
            expression_kind="signal_expression",
        )
        assert result["ok"] is True
        assert any("request_score" in warn for warn in result["warnings"])

    def test_disallowed_call_fails(self):
        result = preflight_dsl("max(age_check, 1)", signal_names=["age_check"])
        assert result["ok"] is False
        assert result["errors"]

    def test_extract_identifiers_ignores_keywords(self):
        names = extract_dsl_identifiers("age_check and not blocklist_check")
        assert names == {"age_check", "blocklist_check"}
