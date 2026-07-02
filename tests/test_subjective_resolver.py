import pytest
import json

def test_initial_state(direct_deploy):
    # Deploy contract and check initial count is 0
    contract = direct_deploy("contracts/subjective_resolver.py", sdk_version="v0.2.16")
    assert contract.get_total_records() == 0

def test_input_validation(direct_deploy, direct_vm):
    contract = direct_deploy("contracts/subjective_resolver.py", sdk_version="v0.2.16")
    
    # Test empty argument_a
    with pytest.raises(Exception) as excinfo:
        contract.resolve_dispute("", "Argument B", "Rules")
    assert "argument_a must not be empty" in str(excinfo.value)
    
    # Test empty argument_b
    with pytest.raises(Exception) as excinfo:
        contract.resolve_dispute("Argument A", "", "Rules")
    assert "argument_b must not be empty" in str(excinfo.value)
    
    # Test empty rules
    with pytest.raises(Exception) as excinfo:
        contract.resolve_dispute("Argument A", "Argument B", "")
    assert "rules must not be empty" in str(excinfo.value)

def test_resolve_dispute_happy_path(direct_deploy, direct_vm):
    contract = direct_deploy("contracts/subjective_resolver.py", sdk_version="v0.2.16")
    
    # Mock LLM verdict
    direct_vm.mock_llm(
        r".*",
        '{"verdict": "PARTY_B", "confidence": 95, "rationale": "Argument B uses gamification which directly meets the primary classroom requirements."}'
    )
    
    # Execute dispute resolution
    contract.resolve_dispute(
        argument_a="We should write tables 100 times.",
        argument_b="We will run a Math Forest gaming app where children cross hurdles by solving arithmetic.",
        rules="Syllabus must use interactive gamification for elementary kids."
    )
    
    assert contract.get_total_records() == 1
    
    # Retrieve and parse record
    record_json = contract.get_record("0")
    record = json.loads(record_json)
    
    assert record["id"] == "0"
    assert record["rules"] == "Syllabus must use interactive gamification for elementary kids."
    assert record["argument_a"] == "We should write tables 100 times."
    assert record["argument_b"] == "We will run a Math Forest gaming app where children cross hurdles by solving arithmetic."
    assert record["verdict"] == "PARTY_B"
    assert record["confidence"] == 95
    assert record["rationale"] == "Argument B uses gamification which directly meets the primary classroom requirements."
