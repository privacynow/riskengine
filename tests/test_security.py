"""Tests for secret handling and outbound URL policy."""

import pytest

from engine.services.security import (
    admin_signal_secret_fields,
    create_restricted_evaluator,
    resolve_bearer_token_for_persist,
    validate_outbound_signal_url,
)


class TestBearerTokenPersist:
    def test_empty_incoming_keeps_existing(self):
        assert resolve_bearer_token_for_persist("secret", "") == "secret"
        assert resolve_bearer_token_for_persist("secret", None) == "secret"

    def test_new_incoming_replaces(self):
        assert resolve_bearer_token_for_persist("secret", "new") == "new"

    def test_admin_fields_never_expose_value(self):
        fields = admin_signal_secret_fields("secret-token")
        assert fields == {"has_bearer_token": True}
        assert "secret-token" not in fields.values()


class TestOutboundUrlPolicy:
    def test_allows_loopback_demo_mocks(self):
        validate_outbound_signal_url("http://127.0.0.1:8000/mock/kyc_score")

    def test_blocks_metadata_endpoint(self):
        with pytest.raises(ValueError, match="not allowed"):
            validate_outbound_signal_url("http://169.254.169.254/latest/meta-data")

    def test_blocks_private_ip_literals(self):
        with pytest.raises(ValueError, match="not allowed"):
            validate_outbound_signal_url("http://10.0.0.5/internal")

    def test_allows_public_hostnames(self):
        validate_outbound_signal_url("https://api.example.com/v1/score")


class TestTemplateRedaction:
    def test_redacts_authorization_header_line(self):
        from engine.services.security import redact_template_for_response

        raw = "Authorization: Bearer super-secret\nContent-Type: application/json"
        redacted = redact_template_for_response(raw)
        assert "super-secret" not in redacted
        assert "Authorization: [REDACTED]" in redacted
        assert "Content-Type: application/json" in redacted

    def test_detects_embedded_credentials(self):
        from engine.services.security import contains_embedded_credential

        assert contains_embedded_credential('{"api_key": "abc123"}')
        assert not contains_embedded_credential("Content-Type: application/json")

    def test_rejects_sensitive_placeholder_names(self):
        from engine.services.security import contains_embedded_credential

        assert contains_embedded_credential("X-Custom: %api_key%")
        assert contains_embedded_credential('{"key": "%token%"}')
        assert not contains_embedded_credential("userId=%applicant_id%")


class TestParamMapRedaction:
    def test_redacts_sensitive_param_names(self):
        from engine.services.security import redact_param_map_for_response

        redacted = redact_param_map_for_response(
            {
                "Authorization": "Bearer leaked-token",
                "api_key": "secret-key",
                "user_id": "12345",
            }
        )
        assert redacted["Authorization"] == "[REDACTED]"
        assert redacted["api_key"] == "[REDACTED]"
        assert redacted["user_id"] == "12345"
        assert "leaked-token" not in str(redacted)
        assert "secret-key" not in str(redacted)

    def test_redacts_credential_like_values(self):
        from engine.services.security import redact_param_map_for_response

        redacted = redact_param_map_for_response(
            {"note": "Authorization: Bearer embedded-secret"}
        )
        assert "embedded-secret" not in redacted["note"]
        assert "[REDACTED]" in redacted["note"]

    def test_redacts_nested_json_credential_values(self):
        from engine.services.security import redact_param_map_for_response

        raw = '{"headers": {"Authorization": "Bearer secret"}}'
        redacted = redact_param_map_for_response({"payload": raw})["payload"]
        assert "secret" not in redacted
        assert '"Authorization": "[REDACTED]"' in redacted


class TestRestrictedEvaluator:
    def test_allows_boolean_logic(self):
        evaluator = create_restricted_evaluator({"kyc_score": 85})
        assert evaluator.eval("kyc_score >= 80") is True

    def test_blocks_function_calls(self):
        evaluator = create_restricted_evaluator({})
        with pytest.raises(Exception):
            evaluator.eval("__import__('os').system('echo pwned')")
