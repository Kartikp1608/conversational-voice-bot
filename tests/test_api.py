import pytest


@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    res = await async_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "service" in data


@pytest.mark.asyncio
async def test_outbound_call_endpoint(async_client):
    payload = {
        "to_phone_number": "+15550199",
        "prompt_id": "sales_outbound",
    }
    res = await async_client.post("/api/v1/calls/outbound", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert "call_id" in data
    assert data["to_phone_number"] == "+15550199"


@pytest.mark.asyncio
async def test_twilio_inbound_webhook(async_client):
    res = await async_client.post("/api/v1/webhooks/twilio/inbound")
    assert res.status_code == 200
    assert "application/xml" in res.headers["content-type"]
    assert "<Connect>" in res.text


@pytest.mark.asyncio
async def test_prompt_retrieval(async_client):
    res = await async_client.get("/api/v1/prompts/healthcare_appointment")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "healthcare_appointment"
