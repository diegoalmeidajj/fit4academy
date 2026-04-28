"""AI landing-page generator for Fit4Academy.

Owners describe their gym in plain language; Claude returns a structured
content blob the renderer turns into a public lead-capture page at
/lead/<academy_id>.

Implementation note: we deliberately avoid `output_config={"format": ...}`
and rely on prompt engineering to coerce JSON output. This keeps us
compatible with every supported version of the anthropic SDK — the
canonical structured-outputs parameter shape has shifted over time and
breaks builds when the SDK on the Railway image is older than expected.
"""

from __future__ import annotations

import json
import os
import re

try:
    import anthropic
    AI_ENABLED = bool(os.environ.get('ANTHROPIC_API_KEY', ''))
except ImportError:
    anthropic = None
    AI_ENABLED = False


MODEL = "claude-opus-4-7"
FALLBACK_MODELS = ["claude-sonnet-4-6", "claude-haiku-4-5"]
MAX_TOKENS = 2048


# ───────────────────────── system prompt (cached) ─────────────────────────

SYSTEM_PROMPT = """You write high-converting landing-page copy for martial-arts academies in the United States — Brazilian Jiu-Jitsu, MMA, Muay Thai, Boxing, Judo, Karate, Kids programs, etc.

Your job: turn a 1-3 sentence brief from the gym owner into a punchy, trust-building landing page that gets visitors to fill out the lead form.

WRITING RULES
1. ENGLISH FIRST. The product is US-market; keep copy in English even if the brief is in Portuguese or Spanish.
2. PLAIN, CONCRETE LANGUAGE. No marketing fluff like "embark on a journey" or "unleash your potential". Write the way a coach actually talks to a new student.
3. SPECIFIC > GENERIC. If the brief mentions a real detail (e.g. "we have kids classes 4 days a week", "black-belt instructors", "20-year-old gym"), use it verbatim or near-verbatim.
4. TIGHT WORD COUNTS. Respect the limits in the schema below.
5. NO FAKE NUMBERS. Don't invent stats unless the brief states them.
6. INCLUSIVE BUT CONFIDENT TONE. Welcoming to beginners, respectful of experienced grapplers.
7. ASSUME the academy offers a free first class unless the brief says otherwise.

OUTPUT — strict JSON matching this exact shape (no markdown, no preamble, no trailing commentary):

{
  "hero_headline": "<6-10 words, concrete promise>",
  "hero_subheadline": "<1 sentence, 12-20 words>",
  "perks": [
    { "icon": "<one of: check|shield|users|calendar|trophy|star|heart|fire|clock|geo|sparkle>",
      "title": "<2-4 words>",
      "body": "<1 sentence, 8-15 words>" },
    ... exactly 4 perks
  ],
  "about_paragraph": "<2-3 sentences, 40-70 words>",
  "faqs": [
    { "q": "<question, 5-12 words>", "a": "<answer, 1-2 sentences, 15-30 words>" },
    ... exactly 4 FAQs
  ],
  "cta_label": "<2-4 words, action verb>",
  "urgency_line": "<short line under CTA, e.g. 'No commitment · No credit card'>",
  "social_proof_line": "<1 line of social proof, may be empty string if nothing concrete in brief>"
}

If asked to regenerate ONLY one section, still emit the WHOLE JSON shape — keep the other fields short/generic since they will be discarded.

Output JSON ONLY. Start your response with { and end with }."""


# Sections that can be regenerated individually
SECTIONS = {'hero', 'perks', 'about', 'faqs', 'cta', 'social_proof'}


# ───────────────────────── helpers ─────────────────────────

class AINotConfigured(RuntimeError):
    pass


def _client():
    if not AI_ENABLED or not anthropic:
        raise AINotConfigured("ANTHROPIC_API_KEY is not set; landing AI is disabled")
    return anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])


def _user_prompt(academy_name: str, brief: str, vibe: str = '', regenerate_section: str | None = None) -> str:
    bits = [
        f"ACADEMY NAME: {academy_name}",
        f"BRIEF FROM OWNER: {brief.strip()}",
    ]
    if vibe:
        bits.append(f"DESIRED VIBE: {vibe}")
    if regenerate_section:
        bits.append(
            f"\nREGENERATE_ONLY: {regenerate_section}\n"
            f"The owner is unhappy with the '{regenerate_section}' section and wants a "
            "different take. Generate something distinctly different in tone or angle for "
            "that section. The other fields will be discarded — keep them minimal."
        )
    bits.append("\nReturn the landing page JSON now. No markdown, no commentary — JSON only.")
    return "\n".join(bits)


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of `text`. Tolerates ``` fences and stray prose."""
    if not text:
        raise ValueError("empty response from Claude")

    # Strip markdown code fences if present
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if fenced:
        candidate = fenced.group(1)
    else:
        # Find first '{' and last '}' — robust to any leading/trailing text
        first = text.find('{')
        last = text.rfind('}')
        if first == -1 or last == -1 or last <= first:
            raise ValueError(f"no JSON object found in response: {text[:200]!r}")
        candidate = text[first:last + 1]

    return json.loads(candidate)


def _call_claude(user_msg: str) -> dict:
    """Try MODEL, fall back to alternates if the chosen one is unavailable on this account."""
    client = _client()
    last_err = None
    for model in [MODEL] + FALLBACK_MODELS:
        try:
            response = client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_msg}],
            )
            text = next((b.text for b in response.content if getattr(b, 'type', None) == 'text'), None)
            if not text:
                raise RuntimeError(f"{model}: no text block in response")
            return _extract_json(text)
        except Exception as e:
            last_err = e
            cls = type(e).__name__
            msg = str(e)
            # Only fall back on model-not-found / not-supported errors. Other
            # errors (network, auth, quota, schema) should bubble up immediately.
            if 'NotFoundError' in cls or 'not found' in msg.lower() or 'invalid_model' in msg or 'does not exist' in msg.lower():
                print(f"[landing-ai] {model} unavailable, trying fallback: {e}")
                continue
            raise
    raise RuntimeError(f"all models failed; last error: {last_err}")


# ───────────────────────── public API ─────────────────────────

def generate_full(academy_name: str, brief: str, vibe: str = '') -> dict:
    """Generate a complete landing-content blob."""
    return _call_claude(_user_prompt(academy_name, brief, vibe, regenerate_section=None))


def regenerate_section(section: str, academy_name: str, brief: str, vibe: str = '') -> dict:
    """Regenerate a single section. Caller merges only the relevant key(s)."""
    if section not in SECTIONS:
        raise ValueError(f"unknown section: {section}; expected one of {sorted(SECTIONS)}")
    return _call_claude(_user_prompt(academy_name, brief, vibe, regenerate_section=section))
