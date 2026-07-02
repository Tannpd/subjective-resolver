# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

import json
import typing
from dataclasses import dataclass


@allow_storage
@dataclass
class DisputeRecord:
    rules: str
    argument_a: str
    argument_b: str
    verdict: str  # PARTY_A | PARTY_B | TIE
    confidence: bigint
    rationale: str


def _normalize_verdict(verdict: str) -> str:
    v = str(verdict or "").strip().upper()
    if "PARTY_A" in v or "PARTY A" in v or "A" == v:
        return "PARTY_A"
    if "PARTY_B" in v or "PARTY B" in v or "B" == v:
        return "PARTY_B"
    if "TIE" in v or "DRAW" in v or "EQUAL" in v:
        return "TIE"
    return "TIE"


def _normalize_confidence(conf_val: typing.Any) -> int:
    try:
        c = int(conf_val)
    except Exception:
        c = 0
    return max(0, min(100, c))


class Contract(gl.Contract):
    records: TreeMap[str, DisputeRecord]
    next_id: bigint

    def __init__(self):
        self.next_id = bigint(0)

    @gl.public.write
    def resolve_dispute(self, argument_a: str, argument_b: str, rules: str) -> None:
        if not argument_a or not argument_a.strip():
            raise gl.vm.UserError("argument_a must not be empty")
        if not argument_b or not argument_b.strip():
            raise gl.vm.UserError("argument_b must not be empty")
        if not rules or not rules.strip():
            raise gl.vm.UserError("rules must not be empty")

        a_clean = argument_a.strip()
        b_clean = argument_b.strip()
        rules_clean = rules.strip()

        def leader_fn() -> str:
            prompt = f"""You are an impartial adjudicator in a professional and educational setting.
Evaluate both arguments strictly based on the provided rules, and decide which argument prevails or if there is a tie.

ADJUDICATION RULES:
---
{rules_clean}
---

ARGUMENT A:
---
{a_clean}
---

ARGUMENT B:
---
{b_clean}
---

Rules for adjudication:
- Assign "PARTY_A" if Argument A clearly adheres to the rules and is logically superior, more persuasive, or factually sound compared to Argument B.
- Assign "PARTY_B" if Argument B clearly adheres to the rules and is logically superior, more persuasive, or factually sound compared to Argument A.
- Assign "TIE" if both arguments equally meet the rules, are of identical logical strength, or if neither adheres to the criteria.
- Assign a confidence score from 0 to 100 representing how confident you are in this qualitative decision.
- Provide a brief, objective rationale (maximum 200 characters) explaining the decision.

Respond ONLY with a valid JSON object matching the following structure:
{{
  "verdict": "PARTY_A" | "PARTY_B" | "TIE",
  "confidence": <integer 0-100>,
  "rationale": "explanation string"
}}"""
            res = gl.nondet.exec_prompt(prompt, response_format="json")
            if not isinstance(res, dict):
                res = {}

            verdict = _normalize_verdict(res.get("verdict", "TIE"))
            confidence = _normalize_confidence(res.get("confidence", 0))
            rationale = str(res.get("rationale", "")).strip()[:200]
            if not rationale:
                rationale = "No rationale provided."

            return json.dumps({
                "verdict": verdict,
                "confidence": confidence,
                "rationale": rationale
            }, sort_keys=True)

        def validator_fn(leader_res: typing.Any) -> bool:
            if not isinstance(leader_res, gl.vm.Return):
                return False
            try:
                leader_data = json.loads(leader_res.calldata)
            except Exception:
                return False

            leader_verdict = _normalize_verdict(leader_data.get("verdict"))
            leader_confidence = _normalize_confidence(leader_data.get("confidence"))

            try:
                mine_json = leader_fn()
                mine_data = json.loads(mine_json)
            except Exception:
                return False

            mine_verdict = _normalize_verdict(mine_data.get("verdict"))
            mine_confidence = _normalize_confidence(mine_data.get("confidence"))

            if leader_verdict != mine_verdict:
                return False

            if abs(leader_confidence - mine_confidence) > 20:
                return False

            return True

        raw_result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        payload = json.loads(raw_result)

        rid = str(self.next_id)
        self.records[rid] = DisputeRecord(
            rules=rules_clean,
            argument_a=a_clean,
            argument_b=b_clean,
            verdict=_normalize_verdict(payload.get("verdict")),
            confidence=bigint(_normalize_confidence(payload.get("confidence"))),
            rationale=str(payload.get("rationale")).strip()[:200]
        )
        self.next_id = self.next_id + bigint(1)

    @gl.public.view
    def get_record(self, record_id: str) -> str:
        if record_id not in self.records:
            raise gl.vm.UserError("Dispute record not found")
        
        record = self.records[record_id]
        return json.dumps({
            "id": record_id,
            "rules": record.rules,
            "argument_a": record.argument_a,
            "argument_b": record.argument_b,
            "verdict": record.verdict,
            "confidence": int(record.confidence),
            "rationale": record.rationale
        })

    @gl.public.view
    def get_total_records(self) -> int:
        return int(self.next_id)
