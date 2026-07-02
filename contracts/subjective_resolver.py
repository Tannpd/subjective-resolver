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


class Contract(gl.Contract):
    records: TreeMap[str, DisputeRecord]
    next_id: bigint

    def __init__(self):
        self.next_id = bigint(0)

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
