import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import CallRepository, PromptRepository


@pytest.mark.asyncio
async def test_call_repository_create_and_get_session(db_session: AsyncSession):
    repo = CallRepository(db_session)
    call_id = "test-call-100"

    created = await repo.create_session(
        call_id=call_id,
        direction="outbound",
        phone_number="+15550199",
        prompt_id="sales_outbound",
        metadata={"campaign": "q3_leads", "retry_count": 1},
    )

    assert created.call_id == call_id
    assert created.direction == "outbound"
    assert created.phone_number == "+15550199"
    assert created.status == "connected"
    assert created.metadata_json is not None
    assert created.metadata_json["campaign"] == "q3_leads"

    fetched = await repo.get_session(call_id)
    assert fetched is not None
    assert fetched.call_id == call_id
    assert fetched.prompt_id == "sales_outbound"


@pytest.mark.asyncio
async def test_call_repository_get_nonexistent_session(db_session: AsyncSession):
    repo = CallRepository(db_session)
    fetched = await repo.get_session("nonexistent-call-id")
    assert fetched is None


@pytest.mark.asyncio
async def test_call_repository_update_status(db_session: AsyncSession):
    repo = CallRepository(db_session)
    call_id = "test-call-200"

    await repo.create_session(
        call_id=call_id,
        direction="inbound",
        phone_number="+18005550000",
        prompt_id="customer_support_inbound",
    )

    updated = await repo.update_status(
        call_id=call_id, status="active", current_stage="business_logic"
    )
    assert updated is not None
    assert updated.status == "active"
    assert updated.current_stage == "business_logic"
    assert updated.end_time is None

    # End call session
    ended = await repo.update_status(call_id=call_id, status="ended")
    assert ended is not None
    assert ended.status == "ended"
    assert ended.end_time is not None

    # Updating non-existent returns None
    none_result = await repo.update_status("invalid-id", status="failed")
    assert none_result is None


@pytest.mark.asyncio
async def test_call_repository_add_transcript(db_session: AsyncSession):
    repo = CallRepository(db_session)
    call_id = "test-call-300"

    await repo.create_session(
        call_id=call_id,
        direction="inbound",
        phone_number="+15550123",
        prompt_id="healthcare_appointment",
    )

    t1 = await repo.add_transcript(
        call_id=call_id,
        speaker="user",
        text="I need to book an appointment for tomorrow.",
        latency_ms=120.5,
        stage="greeting",
    )
    assert t1.id is not None
    assert t1.speaker == "user"
    assert t1.text == "I need to book an appointment for tomorrow."
    assert t1.latency_ms == 120.5

    t2 = await repo.add_transcript(
        call_id=call_id,
        speaker="assistant",
        text="Certainly, what time works best?",
        latency_ms=250.0,
        stage="business_logic",
    )
    assert t2.speaker == "assistant"
    assert t2.stage == "business_logic"


@pytest.mark.asyncio
async def test_call_repository_log_tool_execution(db_session: AsyncSession):
    repo = CallRepository(db_session)
    call_id = "test-call-400"

    await repo.create_session(
        call_id=call_id,
        direction="outbound",
        phone_number="+15559876",
        prompt_id="banking_verification",
    )

    log = await repo.log_tool_execution(
        call_id=call_id,
        tool_name="database_lookup",
        arguments={"account_id": "ACC-998"},
        result={"balance": "$5,000.00"},
        execution_time_ms=45.2,
    )
    assert log.id is not None
    assert log.tool_name == "database_lookup"
    assert log.arguments_json["account_id"] == "ACC-998"
    assert log.result_json is not None
    assert log.result_json["balance"] == "$5,000.00"
    assert log.error is None
    assert log.execution_time_ms == 45.2

    # Error logging
    err_log = await repo.log_tool_execution(
        call_id=call_id,
        tool_name="crm_lookup",
        arguments={"customer_id": "INVALID"},
        error="Customer ID not found in CRM",
        execution_time_ms=15.0,
    )
    assert err_log.error == "Customer ID not found in CRM"


@pytest.mark.asyncio
async def test_call_repository_save_analytics(db_session: AsyncSession):
    repo = CallRepository(db_session)
    call_id = "test-call-500"

    await repo.create_session(
        call_id=call_id,
        direction="outbound",
        phone_number="+15559999",
        prompt_id="sales_outbound",
    )

    analytics = await repo.save_analytics(
        call_id=call_id,
        total_duration_sec=145.5,
        avg_latency_ms=320.0,
        turn_count=8,
        interruption_count=2,
        summary="Customer confirmed interest in Enterprise plan.",
    )
    assert analytics.call_id == call_id
    assert analytics.total_duration_sec == 145.5
    assert analytics.turn_count == 8
    assert analytics.interruption_count == 2
    assert analytics.summary is not None
    assert "Enterprise plan" in analytics.summary


@pytest.mark.asyncio
async def test_prompt_repository_save_and_update(db_session: AsyncSession):
    repo = PromptRepository(db_session)
    prompt_id = "custom_sales_v1"

    # 1. Create prompt
    p1 = await repo.save_prompt(
        prompt_id=prompt_id,
        name="Custom Sales Script",
        content_yaml="stages:\n  greeting:\n    prompt: Hello!",
        description="Initial sales script",
    )
    assert p1.id == prompt_id
    assert p1.version == 1
    assert p1.name == "Custom Sales Script"

    # 2. Retrieve prompt
    fetched = await repo.get_prompt(prompt_id)
    assert fetched is not None
    assert fetched.name == "Custom Sales Script"

    # 3. Update existing prompt (should increment version)
    p2 = await repo.save_prompt(
        prompt_id=prompt_id,
        name="Custom Sales Script v2",
        content_yaml="stages:\n  greeting:\n    prompt: Hi there!",
        description="Updated sales script",
    )
    assert p2.version == 2
    assert p2.name == "Custom Sales Script v2"

    # 4. Get non-existent prompt
    assert await repo.get_prompt("nonexistent_prompt") is None
