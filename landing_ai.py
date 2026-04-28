"""AI landing-page generator for Fit4Academy.

Owners describe their gym in plain language; Claude returns a structured
content blob the renderer turns into a public lead-capture page at
/lead/<academy_id>.

Calls are guarded by ANTHROPIC_API_KEY presence — without it, the module
raises at runtime so the admin UI can surface a clear "AI not configured"
message rather than failing the whole request.
"""

from __future__ import annotations

import json
import os

try:
    import anthropic
    AI_ENABLED = bool(os.environ.get('ANTHROPIC_API_KEY', ''))
except ImportError:
    anthropic = None
    AI_ENABLED = False


MODEL = "claude-opus-4-7"


# ───────────────────────── system prompt (cached) ─────────────────────────
# Frozen — do not interpolate dynamic values here. Anything that varies per
# academy (name, brief, vibe) goes in the user message, not the system prompt.
# Otherwise the prompt-cache hit rate drops to zero.

SYSTEM_PROMPT = """You write high-converting landing-page copy for martial-arts academies in the United States — Brazilian Jiu-Jitsu, MMA, Muay Thai, Boxing, Judo, Karate, Kids programs, etc.

Your job: turn a 1-3 sentence brief from the gym owner into a punchy, trust-building landing page that gets visitors to fill out the lead form.

WRITING RULES
1. ENGLISH FIRST. The product is US-market; keep copy in English even if the brief is in Portuguese or Spanish.
2. PLAIN, CONCRETE LANGUAGE. No marketing fluff like "embark on a journey" or "unleash your potential". Write the way a coach actually talks to a new student.
3. SPECIFIC > GENERIC. If the brief mentions a real detail (e.g. "we have kids classes 4 days a week", "black-belt instructors", "20-year-old gym"), use it verbatim or near-verbatim.
4. TIGHT WORD COUNTS. The form below already enforces character limits — respect them. A short, specific headline beats a long generic one.
5. NO FAKE NUMBERS. Don't invent stats ("trusted by 5,000 students") unless the brief states them. If you must reference scale, use phrases like "growing community" or "all levels welcome".
6. INCLUSIVE BUT CONFIDENT TONE. Welcoming to beginners, respectful of experienced grapplers. Not bro-y, not corporate.
7. ASSUME the academy offers a free first class unless the brief says otherwise.

STRUCTURE GUIDE
- Headline: a single concrete promise. Avoid generic "Train. Grow. Conquer." three-word stacks.
- Subheadline: extends the headline with a reason-to-believe in one sentence.
- Perks (4): mix of practical (free first class, all levels welcome, flexible schedule) and academy-specific perks pulled from the brief.
- About paragraph: 2-3 sentences. Who runs the gym, what makes it different, why a stranger should walk in.
- FAQs (4): the actual questions a beginner asks before showing up — schedule, what to wear, no experience, kids, pricing model. Pick the 4 most relevant.
- CTA: 2-4 words, action verb. "Get Started", "Claim Free Class", "Book My Trial".
- Urgency line: one short line under the CTA — scarcity if real ("Limited spots this month"), or reassurance ("No commitment, no credit card").
- Social proof line: one line. Pull from the brief if it mentions reviews/years/students; otherwise lean on "growing community" or omit.

If the user asks to regenerate ONLY a specific section, return content for the WHOLE schema but only the requested section needs to be different — keep the other fields short and generic so the merge layer can ignore them.

Output: strict JSON matching the schema. No markdown, no preamble, no trailing commentary."""


# ───────────────────────── output schema ─────────────────────────

LANDING_SCHEMA = {
    "type": "object",
    "properties": {
        "hero_headline": {
            "type": "string",
            "description": "6-10 words. Concrete promise, not a slogan."
        },
        "hero_subheadline": {
            "type": "string",
            "description": "One sentence (12-20 words) supporting the headline."
        },
        "perks": {
            "type": "array",
            "minItems": 4,
            "maxItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "icon": {
                        "type": "string",
                        "enum": ["check", "shield", "users", "calendar", "trophy", "star",
                                 "heart", "fire", "clock", "geo", "sparkle"],
                        "description": "Bootstrap icon name (without 'bi-' prefix)."
                    },
                    "title": {"type": "string", "description": "2-4 words."},
                    "body": {"type": "string", "description": "1 sentence, 8-15 words."}
                },
                "required": ["icon", "title", "body"],
                "additionalProperties": False
            }
        },
        "about_paragraph": {
            "type": "string",
            "description": "2-3 sentences (40-70 words) about the gym."
        },
        "faqs": {
            "type": "array",
            "minItems": 4,
            "maxItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Question, 5-12 words."},
                    "a": {"type": "string", "description": "Answer, 1-2 sentences (15-30 words)."}
                },
                "required": ["q", "a"],
                "additionalProperties": False
            }
        },
        "cta_label": {
            "type": "string",
            "description": "2-4 words. Action verb. e.g. 'Claim Free Class'."
        },
        "urgency_line": {
            "type": "string",
            "description": "Short line under the CTA. e.g. 'No commitment · No credit card'."
        },
        "social_proof_line": {
            "type": "string",
            "description": "1 line of social proof. May be empty string if nothing concrete in brief."
        }
    },
    "required": ["hero_headline", "hero_subheadline", "perks", "about_paragraph",
                 "faqs", "cta_label", "urgency_line", "social_proof_line"],
    "additionalProperties": False,
}


# Sections that can be regenerated individually
SECTIONS = {'hero', 'perks', 'about', 'faqs', 'cta', 'social_proof'}


# ───────────────────────── prompts ─────────────────────────

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
            "that section. The other sections in your output will be discarded — keep them "
            "minimal."
        )
    bits.append("\nWrite the landing page content as JSON.")
    return "\n".join(bits)


# ───────────────────────── public API ─────────────────────────

class AINotConfigured(RuntimeError):
    pass


def _client():
    if not AI_ENABLED or not anthropic:
        raise AINotConfigured("ANTHROPIC_API_KEY is not set; landing AI is disabled")
    return anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])


def generate_full(academy_name: str, brief: str, vibe: str = '') -> dict:
    """Generate a complete landing-content blob for a new academy. Returns a
    dict matching LANDING_SCHEMA."""
    return _generate(academy_name, brief, vibe, regenerate_section=None)


def regenerate_section(section: str, academy_name: str, brief: str, vibe: str = '') -> dict:
    """Regenerate a single section. Returns the same full schema dict — caller
    merges only the relevant key(s) back into the saved content."""
    if section not in SECTIONS:
        raise ValueError(f"unknown section: {section}; expected one of {sorted(SECTIONS)}")
    return _generate(academy_name, brief, vibe, regenerate_section=section)


def _generate(academy_name: str, brief: str, vibe: str, regenerate_section: str | None) -> dict:
    client = _client()
    user_msg = _user_prompt(academy_name, brief, vibe, regenerate_section)

    # System prompt is cached: it's the same for every call across all academies,
    # so the cache is shared workspace-wide → ~0.1× cost on read.
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": LANDING_SCHEMA,
            }
        },
        messages=[{"role": "user", "content": user_msg}],
    )

    text = next((b.text for b in response.content if b.type == 'text'), None)
    if not text:
        raise RuntimeError("Claude returned no text block")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Claude returned non-JSON: {e}; text={text[:300]}") from e
    return data
