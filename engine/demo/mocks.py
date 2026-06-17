from typing import Any, Dict, List, Optional

MOCK_ENDPOINT_RESPONSES: Dict[str, Dict[str, Any]] = {
    "doc-verify": {"value": True},
    "sanction-screen": {"value": True},
    "kyc_score": {"value": 85},
    "credit_score": {"value": 742},
    "onboarding": {"value": True},
    "compliance": {"value": True},
    "underwriting": {"value": True},
    "disbursement": {"value": True},
    "servicing": {"value": True},
}


async def mock_service_response(mock_name: str) -> Dict[str, Any]:
    return MOCK_ENDPOINT_RESPONSES.get(mock_name, {"value": True})
