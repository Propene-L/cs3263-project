"""Session-scoped offline or hybrid Phase 2 museum-guide CLI."""

from __future__ import annotations

import argparse
import json

from .dialogue import MuseumDialogue


DEMO_TURNS = [
    "like ag_8416",
    "dislike ag_13231",
    "dislike ag_8296",
    "yes",
    "topic c_expressionist_portrait",
    "no",
    "topic c_expressionist_portrait",
    "no",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Logic-guided museum curator")
    parser.add_argument("--mode", choices=["manual", "hybrid"], default="manual")
    parser.add_argument("--demo", action="store_true", help="Run an explicit offline transcript")
    parser.add_argument("--json-audit", action="store_true", help="Print validated state and proof JSON")
    args = parser.parse_args()
    if args.demo and args.mode != "manual":
        parser.error("--demo uses the explicit manual command language")

    guide = MuseumDialogue.from_repository(use_llm=args.mode == "hybrid")
    session = guide.new_session("visitor_demo")
    print(f"Museum guide mode={args.mode}. Session is not persisted. Type 'quit' to exit.")
    if args.mode == "manual":
        print(
            "Commands: like/dislike ag_ID; interested/reject h_ID; "
            "conjunction h_ID h_ID; know/dont-know/unknown c_ID; "
            "topic/explain c_ID; yes/no/unsure; skip; "
            "correct obs_ID like/dislike ag_ID"
        )
    turns = list(DEMO_TURNS) if args.demo else None
    while True:
        if turns is not None:
            if not turns:
                break
            user_text = turns.pop(0)
            print(f"Visitor > {user_text}")
        else:
            try:
                user_text = input("Visitor > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if user_text.lower() in {"quit", "exit"}:
                break
            if user_text.lower() == "reset":
                session = guide.new_session("visitor_demo")
                print("New session created.")
                continue
        try:
            session, response = guide.run_turn(session, user_text, mode=args.mode)
        except Exception as exc:
            print(f"Validation/engine error: {type(exc).__name__}: {exc}")
            continue
        print(f"Guide > {response['text']}")
        if response["sources"]:
            print("Sources:", json.dumps(response["sources"], ensure_ascii=False))
        if args.json_audit:
            print("Audit:", json.dumps(response["audit"], ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()
