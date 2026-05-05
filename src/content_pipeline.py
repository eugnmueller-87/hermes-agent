"""
Content pipeline: Hermes signals -> KB context -> LLM -> draft post.

Workflow:
  1. Document  — load KB (brand voice, background, signal data)
  2. Monitor   — pull significant signals from Hermes Redis
  3. Brief     — summarise signals into procurement intelligence
  4. Draft     — generate LinkedIn post draft using brand voice
  5. Publish   — stage for approval (Icarus LinkedIn skill handles actual publish)
  6. Iterate   — user edits → regenerate → approve
"""

import logging
from dataclasses import dataclass

from .knowledge_base import KnowledgeBase
from .llm_integration import LLMClient
from .prompt_templates import LINKEDIN_POST, MARKET_BRIEF, SIGNAL_ANALYSIS


@dataclass
class Signal:
    company: str
    signal_type: str
    title: str
    summary: str
    urgency: str
    url: str = ""


@dataclass
class ContentDraft:
    post_text: str
    signal: Signal
    brief: str
    status: str = "draft"  # draft | approved | published


class ContentPipeline:
    def __init__(self, kb_root: str = None, api_key: str = None):
        self.kb = KnowledgeBase(kb_root)
        self.llm = LLMClient(api_key)

    # --- Step 2: Monitor ---

    def fetch_signals(self, min_urgency: str = "MEDIUM") -> list[Signal]:
        """Pull significant signals from Hermes Redis."""
        try:
            from integrations.hermes_client import HermesClient
            client = HermesClient()
            raw = client.get_procurement_briefing(limit=20)
            urgency_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
            threshold = urgency_rank.get(min_urgency, 2)
            signals = []
            for item in raw:
                if urgency_rank.get(item.get("urgency", "LOW"), 1) >= threshold:
                    signals.append(Signal(
                        company=item.get("supplier", ""),
                        signal_type=item.get("signal_type", "OTHER"),
                        title=item.get("title", ""),
                        summary=item.get("summary", ""),
                        urgency=item.get("urgency", "MEDIUM"),
                        url=item.get("url", ""),
                    ))
            return signals
        except Exception as e:
            logging.warning(f"[ContentPipeline] Redis fetch failed: {e}")
            return []

    # --- Step 3: Brief ---

    def generate_brief(self, signals: list[Signal]) -> str:
        if not signals:
            return "No significant signals this period."
        signals_text = "\n\n".join(
            f"- {s.company} [{s.signal_type}] {s.urgency}: {s.title}\n  {s.summary}"
            for s in signals
        )
        prompt = MARKET_BRIEF.format(signals=signals_text)
        return self.llm.generate_brief(prompt)

    # --- Step 4: Draft ---

    def draft_post(self, signal: Signal) -> ContentDraft:
        kb_context = self.kb.brand_voice_context()
        signal_text = (
            f"Company: {signal.company}\n"
            f"Signal type: {signal.signal_type}\n"
            f"Title: {signal.title}\n"
            f"Summary: {signal.summary}\n"
            f"Urgency: {signal.urgency}"
        )
        prompt = LINKEDIN_POST.format(kb_context=kb_context, signal=signal_text)
        post_text = self.llm.generate_linkedin_post(prompt)
        brief = self.generate_brief([signal])
        return ContentDraft(post_text=post_text, signal=signal, brief=brief)

    def analyze_signal(self, signal: Signal) -> str:
        prompt = SIGNAL_ANALYSIS.format(
            company=signal.company,
            signal_type=signal.signal_type,
            title=signal.title,
            summary=signal.summary,
            urgency=signal.urgency,
        )
        return self.llm.generate(prompt)

    # --- Step 6: Iterate ---

    def refine_post(self, draft: ContentDraft, feedback: str) -> ContentDraft:
        kb_context = self.kb.brand_voice_context()
        prompt = (
            f"Revise this LinkedIn post based on the feedback below.\n\n"
            f"CURRENT POST:\n{draft.post_text}\n\n"
            f"FEEDBACK:\n{feedback}\n\n"
            f"BRAND VOICE RULES:\n{kb_context}\n\n"
            "Output only the revised post text."
        )
        new_text = self.llm.generate_linkedin_post(prompt)
        return ContentDraft(
            post_text=new_text,
            signal=draft.signal,
            brief=draft.brief,
            status="draft",
        )

    # --- Full run ---

    def run(self, min_urgency: str = "HIGH") -> list[ContentDraft]:
        """Full pipeline: fetch signals -> brief -> draft posts for top signals."""
        signals = self.fetch_signals(min_urgency=min_urgency)
        if not signals:
            logging.info("[ContentPipeline] No signals meeting threshold.")
            return []
        drafts = []
        for signal in signals[:3]:  # cap at 3 drafts per run
            draft = self.draft_post(signal)
            drafts.append(draft)
            logging.info(f"[ContentPipeline] Drafted post for {signal.company} [{signal.signal_type}]")
        return drafts
