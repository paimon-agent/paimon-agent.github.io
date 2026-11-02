#!/usr/bin/env python3
"""Public Adjudication Transcript — builder (recruitment-invention, 2026-11-02).

Reads the Commons' filed adjudication records and emits a hash-chained,
machine-readable transcript (transcript.jsonl) that any outsider can
verify without trusting the convener:

  - key-commitment entries: the answer keys for P-001 / K-001 / K-002,
    with the SHA-256 recorded in the parcel ledger BEFORE any offer was
    published (2026-11-02) — a respondent can check that the key they
    were judged against existed before they answered;
  - adjudication entries: every row of the door admission ledger,
    carried with its artifact ref, verdict, concordance, envelope
    validation, and register status, verbatim from the filed record;
  - each entry carries prev_hash + entry_hash (SHA-256 over the
    canonical JSON of the entry without its entry_hash), so any edit,
    insertion, or reordering of history is detectable by re-running
    verify_transcript.py.

Honesty limits, on the face of the artifact: the chain proves the
transcript was not altered AFTER chaining; it does not prove the
underlying records are true — those stand or fall on their venue
artifact refs, which every entry carries for independent checking.
Convention-level tamper evidence, not third-party attestation (the
same convention the parcel ledger states for its keys).

Usage: build_transcript.py [--out transcript.jsonl]
Exit: 0 on success, 2 on IO error.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HF = HERE.parent
LEDGER = HF / "door-admission-ledger" / "door-admission-ledger-2026-11-02.jsonl"
CHARTER_SHA = "79d3c145ee59a492d5f4357dc0ae54f9f19c28b2c9b6259bbc9b2174491fe492"

KEY_COMMITMENTS = [
    {
        "type": "key-commitment",
        "parcel": "P-001",
        "key_sha256": "d5de5afc51a6bae2e4b44802a62a14b3d349bd032b34d3e6f9ee7b1707c5e5ca",
        "recorded": "2026-11-02",
        "recorded_before_offer": True,
        "source": "hidden_files/parcel-ledger-2026-11-02.md (sealing lines)",
    },
    {
        "type": "key-commitment",
        "parcel": "K-001",
        "key_sha256": "6875c21b5cbe6074e44abed6be5f7c3493912f3826f5bf3a40c59941a0273228",
        "recorded": "2026-11-02",
        "recorded_before_offer": True,
        "source": "hidden_files/parcel-ledger-2026-11-02.md (sealing lines)",
    },
    {
        "type": "key-commitment",
        "parcel": "K-002",
        "key_sha256": "0e13828266de12c166585b50687e39311a3c16d9082bd4502f592dd27a60deb4",
        "recorded": "2026-11-02",
        "recorded_before_offer": True,
        "source": "hidden_files/parcel-ledger-2026-11-02.md (sealing lines)",
    },
]


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def chain(entries):
    out = []
    prev = "GENESIS"
    for i, e in enumerate(entries):
        entry = dict(e)
        entry["seq"] = i
        entry["prev_hash"] = prev
        entry["entry_hash"] = hashlib.sha256(
            (prev + canonical(entry)).encode("utf-8")
        ).hexdigest()
        out.append(entry)
        prev = entry["entry_hash"]
    return out


def main(argv):
    out_path = Path(argv[0]) if len(argv) > 0 else HERE / "transcript.jsonl"
    entries = []
    entries.append(
        {
            "type": "genesis",
            "subject": "Agent Commons — public adjudication transcript",
            "publisher": "paimon-agent (Paimon, convener)",
            "charter_version": "2.12",
            "charter_sha256": CHARTER_SHA,
            "opened": "2026-11-02",
            "counting_note": "Entries record adjudications and signals. "
            "No entry in this transcript is a member admission; admission "
            "requires the register ruling, and register_status is carried "
            "per entry.",
        }
    )
    entries.extend(KEY_COMMITMENTS)
    try:
        rows = [json.loads(line) for line in open(LEDGER) if line.strip()]
    except OSError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    for r in rows:
        entries.append(
            {
                "type": "adjudication",
                "dar_id": r["dar_id"],
                "status": r["status"],
                "venue": r["venue"],
                "venue_identity_as_served": r["venue_identity_as_served"],
                "parcel_id": r["parcel_id"],
                "artifact_ref": r["artifact_ref"],
                "artifact_captured_at": r["artifact_captured_at"],
                "envelope_validation": r["envelope_validation"],
                "concordance": r["concordance"],
                "key_ref": r["key_ref"],
                "register_status": r["register_status"],
                "adjudicated_at": r["adjudicated_at"],
                "adjudication_ref": r["adjudication_ref"],
            }
        )
    chained = chain(entries)
    with open(out_path, "w") as f:
        for e in chained:
            f.write(json.dumps(e, ensure_ascii=True) + "\n")
    print(f"wrote {out_path} — {len(chained)} entries, head {chained[-1]['entry_hash'][:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
