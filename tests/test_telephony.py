import json
import base64
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telephony.twilio_adapter import TwilioAdapter
from telephony.sip_adapter import SIPAdapter
from telephony.base_telephony import BaseTelephonyAdapter
from utils.audio_utils import AudioUtils


@pytest.mark.asyncio
async def test_twilio_adapter_simulated_outbound_call():
    adapter = TwilioAdapter()
    res = await adapter.make_outbound_call(
        to_phone_number="+15550199",
        from_phone_number="+18005550100",
        websocket_url="wss://example.com/ws/twilio/call-1",
    )
    assert res["status"] == "queued"
    assert res["to"] == "+15550199"
    assert res["websocket_url"] == "wss://example.com/ws/twilio/call-1"
    assert "CA-SIMULATED" in res["call_sid"]


@pytest.mark.asyncio
async def test_twilio_adapter_real_outbound_call_success():
    adapter = TwilioAdapter(
        account_sid="AC_test_account_sid",
        auth_token="test_auth_token",
        default_from_number="+18005550100",
    )

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "status": "queued",
        "sid": "CA1234567890abcdef",
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        res = await adapter.make_outbound_call(
            to_phone_number="+15550199",
            from_phone_number="+18005550100",
            websocket_url="wss://example.com/ws/twilio/call-1",
        )
        assert res["status"] == "queued"
        assert res["call_sid"] == "CA1234567890abcdef"
        assert res["to"] == "+15550199"


@pytest.mark.asyncio
async def test_twilio_adapter_real_outbound_call_error():
    adapter = TwilioAdapter(
        account_sid="AC_test_account_sid",
        auth_token="test_auth_token",
    )

    with patch("httpx.AsyncClient.post", side_effect=Exception("Connection refused")):
        res = await adapter.make_outbound_call(
            to_phone_number="+15550199",
            from_phone_number="+18005550100",
            websocket_url="wss://example.com/ws/twilio/call-1",
        )
        assert res["status"] == "error"
        assert "Connection refused" in res["message"]


def test_twilio_parse_media_event_start():
    adapter = TwilioAdapter()
    start_payload = json.dumps({
        "event": "start",
        "streamSid": "MZ12345",
        "start": {
            "callSid": "CA999",
            "mediaFormat": {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1},
        },
    })
    event = adapter.parse_media_event(start_payload)
    assert event["event"] == "start"
    assert event["stream_sid"] == "MZ12345"
    assert event["call_sid"] == "CA999"


def test_twilio_parse_media_event_media():
    adapter = TwilioAdapter()
    # 20ms of silence in mu-law (0xFF or 0x7F)
    pcm_bytes = AudioUtils.create_silence(duration_ms=20)
    mulaw_bytes = AudioUtils.pcm_to_mulaw(pcm_bytes)
    b64_str = base64.b64encode(mulaw_bytes).decode("utf-8")

    media_payload = json.dumps({
        "event": "media",
        "streamSid": "MZ12345",
        "media": {
            "payload": b64_str,
            "track": "inbound",
        },
    })
    event = adapter.parse_media_event(media_payload)
    assert event["event"] == "media"
    assert event["stream_sid"] == "MZ12345"
    assert len(event["pcm_bytes"]) > 0


def test_twilio_parse_media_event_stop_and_invalid():
    adapter = TwilioAdapter()
    stop_payload = json.dumps({"event": "stop", "streamSid": "MZ12345"})
    event = adapter.parse_media_event(stop_payload)
    assert event["event"] == "stop"
    assert event["stream_sid"] == "MZ12345"

    # Invalid JSON
    err_event = adapter.parse_media_event("invalid-non-json-string")
    assert err_event["event"] == "error"


def test_twilio_format_outbound_media_payload():
    pcm_silence = AudioUtils.create_silence(duration_ms=20)
    payload_str = TwilioAdapter.format_outbound_media_payload("MZ999", pcm_silence)
    data = json.loads(payload_str)
    assert data["event"] == "media"
    assert data["streamSid"] == "MZ999"
    assert "payload" in data["media"]


@pytest.mark.asyncio
async def test_sip_adapter_outbound_and_events():
    sip = SIPAdapter()
    call_res = await sip.make_outbound_call(
        to_phone_number="+15550199",
        from_phone_number="+18005550100",
        websocket_url="wss://example.com/ws/sip/1",
    )
    assert call_res["status"] == "initiated"
    assert "sip:+15550199@" in call_res["sip_uri"]

    # Parse binary PCM bytes
    pcm_data = b"\x00\x00" * 160
    ev1 = sip.parse_media_event(pcm_data)
    assert ev1["event"] == "media"
    assert ev1["pcm_bytes"] == pcm_data

    # Parse JSON string
    ev2 = sip.parse_media_event(json.dumps({"type": "ping", "data": "123"}))
    assert ev2["event"] == "ping"

    # Parse invalid string
    ev3 = sip.parse_media_event("not-json")
    assert ev3["event"] == "error"

    # Parse other types
    ev4 = sip.parse_media_event(12345)
    assert ev4["event"] == "unknown"
