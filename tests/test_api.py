import pytest


@pytest.mark.asyncio
async def test_root_endpoint(async_client):
    res = await async_client.get("/")
    assert res.status_code == 200
    assert "Voice AI Platform" in res.text or "<!DOCTYPE html>" in res.text or "<html" in res.text


@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    res = await async_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_metrics_endpoint(async_client):
    res = await async_client.get("/metrics")
    assert res.status_code == 200
    assert "voice_ai" in res.text or "# HELP" in res.text


@pytest.mark.asyncio
async def test_outbound_call_and_details_endpoint(async_client):
    payload = {
        "to_phone_number": "+15550199",
        "prompt_id": "sales_outbound",
    }
    create_res = await async_client.post("/api/v1/calls/outbound", json=payload)
    assert create_res.status_code == 201
    data = create_res.json()
    assert "call_id" in data
    call_id = data["call_id"]
    assert data["to_phone_number"] == "+15550199"

    # Fetch call details
    get_res = await async_client.get(f"/api/v1/calls/{call_id}")
    assert get_res.status_code == 200
    details = get_res.json()
    assert details["call_id"] == call_id
    assert details["direction"] == "outbound"

    # Fetch non-existent call
    not_found = await async_client.get("/api/v1/calls/nonexistent-call-12345")
    assert not_found.status_code == 404


@pytest.mark.asyncio
async def test_twilio_inbound_and_status_webhooks(async_client):
    # Inbound voice webhook
    res = await async_client.post("/api/v1/webhooks/twilio/inbound")
    assert res.status_code == 200
    assert "application/xml" in res.headers["content-type"]
    assert "<Connect>" in res.text

    # Status callback webhook
    status_res = await async_client.post(
        "/api/v1/webhooks/twilio/status",
        data={"CallSid": "CA123", "CallStatus": "completed"},
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_prompt_crud_endpoints(async_client):
    # Retrieve pre-loaded prompt
    res = await async_client.get("/api/v1/prompts/healthcare_appointment")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "healthcare_appointment"

    # Upload new prompt
    upload_res = await async_client.post(
        "/api/v1/prompts/",
        json={
            "prompt_id": "api_test_prompt",
            "name": "API Test Prompt",
            "content_yaml": "stages:\n  greeting:\n    prompt: Testing",
            "description": "Uploaded via API test",
        },
    )
    assert upload_res.status_code == 201
    assert upload_res.json()["status"] == "saved"
