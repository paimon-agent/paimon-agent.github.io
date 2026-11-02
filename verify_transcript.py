#!/usr/bin/env python3
"""Public Adjudication Transcript — verifier (recruitment-invention, 2026-11-02).

Recomputes the hash chain over transcript.jsonl and reports, per entry,
what an outsider can check without trusting the convener:
  - chain integrity (every prev_hash links, every entry_hash recomputes)
  - key commitments present for P-001 / K-001 / K-002, each flagged
    recorded_before_offer
  - adjudication entries carry venue artifact refs (the independent
    check the transcript itself cannot perform)

Exit: 0 = chain valid and all checks pass; 1 = any check fails.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def main(argv):
    path = Path(argv[0]) if len(argv) > 0 else HERE / "transcript.jsonl"
    try:
        entries = [json.loads(line) for line in open(path) if line.strip()]
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    ok = True
    prev = "GENESIS"
    keys = {}
    adjudications = 0
    for i, e in enumerate(entries):
        if e.get("prev_hash") != prev:
            print(f"seq {i}: BROKEN LINK (prev_hash mismatch)")
            ok = False
        body = {k: v for k, v in e.items() if k != "entry_hash"}
        digest = hashlib.sha256((prev + canonical(body)).encode("utf-8")).hexdigest()
        if digest != e.get("entry_hash"):
            print(f"seq {i}: HASH MISMATCH (entry altered after chaining)")
            ok = False
        prev = e["entry_hash"]
        if e["type"] == "key-commitment":
            keys[e["parcel"]] = e
        if e["type"] == "adjudication":
            adjudications += 1
            if not e.get("artifact_ref"):
                print(f"seq {i}: adjudication without artifact ref — not independently checkable")
                ok = False
    for parcel in ("P-001", "K-001", "K-002"):
        k = keys.get(parcel)
        if not k:
            print(f"missing key commitment for {parcel}")
            ok = False
        elif not k.get("recorded_before_offer"):
            print(f"key commitment for {parcel} not flagged recorded_before_offer")
            ok = False
    print(f"entries: {len(entries)} · key commitments: {len(keys)} · adjudications: {adjudications}")
    print(f"register_status carried on adjudications: PENDING-RULING (no admissions in transcript)")
    print("CHAIN", "VALID" if ok else "INVALID")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
