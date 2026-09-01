from prompt_engine.prompt_builder import PromptBuilder
from prompt_engine.prompt_loader import PromptLoader


def test_prompt_loader():
    loader = PromptLoader(prompts_dir="prompts")
    prompt_data = loader.load_prompt("sales_outbound")
    assert prompt_data["name"] == "sales_outbound"
    assert "workflow" in prompt_data


def test_prompt_builder():
    builder = PromptBuilder()
    sys_prompt = builder.build_system_prompt(
        prompt_id="healthcare_appointment",
        current_stage="VERIFICATION",
        context_vars={"patient_name": "John Doe"},
        rag_facts=["Clinic Hours: Mon-Fri 8am-6pm"],
    )
    assert "ROLE & PERSONALITY" in sys_prompt
    assert "CURRENT CONVERSATION STAGE: VERIFICATION" in sys_prompt
    assert "patient_name: John Doe" in sys_prompt
    assert "Clinic Hours: Mon-Fri 8am-6pm" in sys_prompt
