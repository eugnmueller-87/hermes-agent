"""
Content pipeline entry point.

Usage:
  python -m src.main                     # run full pipeline, print drafts
  python -m src.main --signal NVIDIA     # draft post for a specific company
  python -m src.main --brief             # print market brief only
  python -m src.main --kb                # list loaded KB documents
"""

import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def cmd_run(args):
    from src.content_pipeline import ContentPipeline
    pipeline = ContentPipeline()
    drafts = pipeline.run(min_urgency=args.urgency)
    if not drafts:
        print("No drafts generated — no signals at this urgency level.")
        return
    for i, draft in enumerate(drafts, 1):
        print(f"\n--- Draft {i}: {draft.signal.company} [{draft.signal.signal_type}] ---")
        print(draft.post_text)
        print(f"\nBrief: {draft.brief}")


def cmd_brief(args):
    from src.content_pipeline import ContentPipeline
    pipeline = ContentPipeline()
    signals = pipeline.fetch_signals(min_urgency="LOW")
    brief = pipeline.generate_brief(signals)
    print("\nMarket Brief\n" + "=" * 40)
    print(brief)


def cmd_kb(args):
    from src.knowledge_base import KnowledgeBase
    kb = KnowledgeBase()
    docs = kb.all()
    print(f"\nKnowledge Base — {len(docs)} documents loaded")
    for doc in docs:
        print(f"  [{doc.category}] {doc.name}  ({len(doc.content)} chars)")


def cmd_signal(args):
    from src.content_pipeline import ContentPipeline, Signal
    pipeline = ContentPipeline()
    signal = Signal(
        company=args.signal,
        signal_type="OTHER",
        title=f"Manual signal for {args.signal}",
        summary=args.summary or f"User-requested post about {args.signal}.",
        urgency="MEDIUM",
    )
    draft = pipeline.draft_post(signal)
    print(f"\n--- Draft: {args.signal} ---")
    print(draft.post_text)


def main():
    parser = argparse.ArgumentParser(description="Hermes Content Pipeline")
    parser.add_argument("--urgency", default="HIGH", choices=["HIGH", "MEDIUM", "LOW"])
    parser.add_argument("--brief", action="store_true", help="Print market brief only")
    parser.add_argument("--kb", action="store_true", help="List KB documents")
    parser.add_argument("--signal", metavar="COMPANY", help="Draft post for a specific company")
    parser.add_argument("--summary", metavar="TEXT", help="Signal summary (used with --signal)")
    args = parser.parse_args()

    if args.kb:
        cmd_kb(args)
    elif args.brief:
        cmd_brief(args)
    elif args.signal:
        cmd_signal(args)
    else:
        cmd_run(args)


if __name__ == "__main__":
    main()
