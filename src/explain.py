
import os
from dotenv import load_dotenv
from .anomaly import Anomaly

load_dotenv() 

_SYSTEM_PROMPT = (
    "You are a precise spreadsheet auditor. You are given one cell whose "
    "formula breaks the pattern used by the rest of a block of similar "
    "cells, plus one neighboring cell that DOES follow the pattern. "
    "In 2-3 sentences: (1) state plainly what is different about the "
    "flagged formula, (2) give your best guess at whether this looks like "
    "a genuine error (e.g. a forgotten range update, wrong relative/absolute "
    "reference) or a deliberate exception, and (3) suggest the likely "
    "correct formula. Be concise and concrete -- no filler, no restating "
    "the question."
)


def _template_fallback(anomaly: Anomaly) -> str:
    conforming = anomaly.example_conforming_cell
    conforming_txt = (
        f"{conforming.address} ({conforming.formula})" if conforming else "a neighboring cell"
    )
    return (
        f"{anomaly.address} does not match the pattern used by the other "
        f"{anomaly.block_size - 1} cells in this {anomaly.orientation} block "
        f"(e.g. {conforming_txt}). This often indicates a forgotten update "
        f"when the formula was filled down/across, or a manual edit. "
        f"[Set OPENAI_API_KEY for a detailed AI explanation.]"
    )


def explain_anomaly(anomaly: Anomaly, model: str = "gpt-4o-mini") -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _template_fallback(anomaly)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        conforming = anomaly.example_conforming_cell
        conforming_desc = (
            f"{conforming.address}: {conforming.formula}"
            if conforming
            else "(no example available)"
        )

        user_prompt = (
            f"Flagged cell: {anomaly.address}\n"
            f"Flagged formula: {anomaly.formula}\n"
            f"Block context: {anomaly.orientation}-wise block of {anomaly.block_size} cells, "
            f"{int(anomaly.majority_share * anomaly.block_size)} of which follow the same pattern.\n"
            f"A conforming neighbor: {conforming_desc}\n"
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=200,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e: 
        return _template_fallback(anomaly) + f" (AI explanation unavailable: {e})"
