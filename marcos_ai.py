"""Marcos AI — Smart Business Advisor for Academy Owners
Powered by Claude API (Anthropic)

Marcos analyzes your academy's real data and gives actionable advice on:
- Finance & profitability
- Marketing & lead acquisition
- Member retention & growth
- Expense optimization
- Pricing strategy
"""

import os
import json

def _sanitized_key() -> str:
    """Strip whitespace + accidental quote chars from the env value.
    Common Railway/console copy-paste bugs include trailing newlines and
    surrounding quotes that the Anthropic API rejects with 401."""
    raw = os.environ.get('ANTHROPIC_API_KEY', '') or ''
    return raw.strip().strip('"').strip("'").strip()


try:
    import anthropic
    ANTHROPIC_KEY = _sanitized_key()
    AI_ENABLED = bool(ANTHROPIC_KEY)
except ImportError:
    AI_ENABLED = False
    anthropic = None
    ANTHROPIC_KEY = ''

MARCOS_SYSTEM_PROMPT = """You are Marcos, an AI business advisor specialized in martial arts academies, fitness studios, and gyms. You work inside Fit4Academy, a CRM platform for academy owners.

Your personality:
- Friendly but direct — you're a business mentor, not a chatbot
- Data-driven — always reference the numbers when giving advice
- Action-oriented — every tip should be something they can do THIS WEEK
- Encouraging but honest — celebrate wins, but flag problems clearly
- Speak concisely — academy owners are busy, keep it practical

Your expertise:
- Revenue optimization (pricing, upselling, membership tiers)
- Marketing (Google Ads, Meta/Facebook Ads, Instagram, referral programs)
- Member retention (attendance tracking, engagement, belt promotions)
- Lead conversion (pipeline optimization, follow-up cadence, trial-to-member)
- Expense management (rent negotiation, payroll optimization, vendor deals)
- Growth strategies (new programs, events, competitions, kids programs)
- Industry benchmarks (average revenue per member, churn rate, conversion rate)

Industry benchmarks you know:
- Healthy academy: $150-200/member/month average revenue
- Good retention: >85% monthly retention rate
- Good conversion: >30% trial-to-member conversion
- Healthy margin: >20% net profit margin
- Marketing spend: 5-10% of revenue
- Payroll: 30-40% of revenue
- Rent: 15-25% of revenue

When analyzing data, always:
1. Start with the most impactful insight
2. Compare to industry benchmarks
3. Give 2-3 specific actionable tips
4. End with encouragement

Format your response with emojis for readability. Use bullet points.
Keep responses under 300 words — be concise and impactful."""


def get_marcos_advice(data_context, question=""):
    """Get AI-powered business advice from Marcos.

    data_context: dict with academy metrics
    question: optional specific question from the owner
    """
    if not AI_ENABLED:
        return _fallback_advice(data_context)

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

        user_msg = f"""Here's my academy's current data:

FINANCE ({data_context.get('month_name', 'This Month')} {data_context.get('year', '')}):
- Revenue: ${data_context.get('revenue', 0):,.2f}
- Expenses: ${data_context.get('expenses', 0):,.2f}
- Payroll: ${data_context.get('payroll', 0):,.2f}
- Net Profit: ${data_context.get('net_profit', 0):,.2f}
- Margin: {data_context.get('margin', 0)}%
- Pending payments: ${data_context.get('pending', 0):,.2f}
- vs Last Month Revenue: {data_context.get('revenue_change', 0):+.1f}%

MEMBERS:
- Active members: {data_context.get('active_members', 0)}
- Revenue per member: ${data_context.get('revenue_per_member', 0):,.2f}

LEADS:
- New leads this month: {data_context.get('leads_in', 0)}
- Converted: {data_context.get('leads_converted', 0)}
- Conversion rate: {data_context.get('conversion_rate', 0)}%
- Leads waiting 24h+: {data_context.get('urgent_leads', 0)}

ATTENDANCE:
- Members who trained: {data_context.get('members_trained', 0)}
- Attendance rate: {data_context.get('attendance_rate', 0)}%
- Absent 15+ days: {data_context.get('absent_members', 0)}

TOP EXPENSES:
{data_context.get('top_expenses_text', 'No expenses recorded')}

TOP REVENUE SOURCES:
{data_context.get('revenue_sources_text', 'No revenue recorded')}
"""
        if question:
            user_msg += f"\n\nMy specific question: {question}"
        else:
            user_msg += "\n\nGive me your top insights and actionable tips for this month."

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=MARCOS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}]
        )

        return response.content[0].text
    except Exception as e:
        print(f"[Marcos AI] Error: {e}")
        return _fallback_advice(data_context)


INBOX_REPLY_SYSTEM_PROMPT = """You are Marcos, helping a martial arts academy
owner reply to messages from prospects, members, and parents. Draft a single
reply — no greetings, no sign-offs unless they fit the existing thread tone.

Rules:
- Match the language of the most recent inbound message (Portuguese, English,
  Spanish — whatever they wrote).
- Match the thread's tone: warm but professional, never salesy.
- Keep replies under 3 sentences unless the question genuinely needs more.
- If the question is about pricing, schedule, or trial — answer directly using
  the academy data provided. If you don't know, say so and suggest a phone
  call or visit.
- Never invent specifics like prices, instructor names, or class times that
  aren't in the data.
- Never use exclamation marks unless the inbound message used them.
- Do not include "Sincerely, Marcos" or any AI-disclosure footer.

Your output is the reply text only. The owner will review it before sending.
"""


def draft_inbox_reply(thread_messages, thread_meta=None, academy_context=None):
    """Draft a reply to a conversation in the unified inbox.

    thread_messages: list of dicts with {direction: 'in'|'out', body, sender_label}
                     ordered chronologically (oldest first).
    thread_meta:     {channel_kind, contact_name, member_belt, member_status, ...}
    academy_context: {name, programs, schedule_summary, pricing_summary, ...}

    Returns a draft reply string. Falls back to a polite generic ask when AI is
    not configured.
    """
    if not AI_ENABLED:
        return _fallback_inbox_reply(thread_messages)

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

        # Build a conversation summary for the prompt.
        history_lines = []
        for m in thread_messages[-15:]:  # last 15 turns is plenty
            role = 'PROSPECT' if m.get('direction') == 'in' else 'COACH (us)'
            label = m.get('sender_label', '')
            body = (m.get('body') or '').strip()
            if body:
                history_lines.append(f"[{role}{' / ' + label if label else ''}] {body}")

        meta = thread_meta or {}
        ac = academy_context or {}

        prompt = f"""You're drafting the next reply for the academy "{ac.get('name', 'our academy')}".

CHANNEL: {meta.get('channel_kind', 'unknown')}
CONTACT NAME: {meta.get('contact_name', 'unknown')}
LINKED MEMBER: {('yes — ' + str(meta.get('member_belt', '?')) + ' belt, status ' + str(meta.get('member_status', '?'))) if meta.get('member_id') else 'no (this is a prospect or unmatched contact)'}

ACADEMY CONTEXT:
- Programs offered: {ac.get('programs_text', 'BJJ, Muay Thai, Kids')}
- Schedule highlights: {ac.get('schedule_text', 'see /schedule')}
- Pricing notes: {ac.get('pricing_text', 'see /memberships')}

CONVERSATION SO FAR (oldest to newest):
{chr(10).join(history_lines) if history_lines else '(no prior messages)'}

Write the next reply for the COACH. Output the reply text only — no quotes,
no labels, no preamble."""

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=INBOX_REPLY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"[Marcos AI] Inbox reply error: {e}")
        return _fallback_inbox_reply(thread_messages)


def _fallback_inbox_reply(thread_messages):
    """Plain rule-based suggestion when AI isn't configured."""
    last_in = next(
        (m for m in reversed(thread_messages) if m.get('direction') == 'in'),
        None
    )
    if not last_in:
        return "Hi! Thanks for reaching out — how can I help?"
    body = (last_in.get('body') or '').lower()
    if any(k in body for k in ('price', 'preço', 'cost', 'how much', 'quanto', 'mensalidade')):
        return ("Thanks for asking! Pricing depends on the program you choose. "
                "Want to come by for a free trial class? I can show you everything in person.")
    if any(k in body for k in ('trial', 'aula experimental', 'first class', 'visit')):
        return ("Of course — you're welcome anytime. We have classes most evenings; "
                "what time works best for you?")
    if any(k in body for k in ('schedule', 'horário', 'time', 'when', 'quando')):
        return ("Our full schedule is on the website. What program are you most "
                "interested in? I can recommend a starting class.")
    if any(k in body for k in ('cancel', 'cancelar', 'unsubscribe', 'pause')):
        return ("Sorry to hear you're thinking about pausing. Can you tell me what's "
                "going on? We might be able to find an option that works.")
    return "Thanks for the message — I'll get back to you shortly."


def _fallback_advice(data):
    """Rule-based advice when AI is not available."""
    tips = []
    margin = data.get('margin', 0)
    conv_rate = data.get('conversion_rate', 0)
    attendance = data.get('attendance_rate', 0)
    urgent = data.get('urgent_leads', 0)
    absent = data.get('absent_members', 0)
    rev_change = data.get('revenue_change', 0)
    revenue = data.get('revenue', 0)
    payroll = data.get('payroll', 0)
    expenses = data.get('expenses', 0)
    rpm = data.get('revenue_per_member', 0)

    # Revenue insight
    if rev_change > 10:
        tips.append(f"📈 **Revenue is up {rev_change:+.1f}%** vs last month — great momentum! Keep pushing marketing.")
    elif rev_change < -10:
        tips.append(f"📉 **Revenue dropped {rev_change:+.1f}%** vs last month — check if members are canceling or if lead flow decreased.")

    # Margin insight
    if margin >= 30:
        tips.append(f"🏆 **{margin}% margin is excellent!** You're above the industry average (20%). Consider reinvesting 5-10% in marketing to grow further.")
    elif margin >= 20:
        tips.append(f"✅ **{margin}% margin is healthy.** Look for small expense optimizations to push above 30%.")
    elif margin >= 0:
        tips.append(f"⚠️ **{margin}% margin is thin.** Review your top expenses — can you negotiate rent or reduce utility costs?")
    else:
        tips.append(f"🚨 **Operating at a loss ({margin}%).** Urgent: either increase revenue (raise prices, enroll more members) or cut costs.")

    # Lead conversion
    if conv_rate < 20 and data.get('leads_in', 0) > 0:
        tips.append(f"📊 **{conv_rate}% conversion rate is below average** (industry: 30%+). Improve your trial experience — personal attention during the first class makes a huge difference.")
    elif conv_rate >= 30:
        tips.append(f"🎯 **{conv_rate}% conversion rate is strong!** Your trial process is working. Consider increasing marketing spend to feed more leads into the pipeline.")

    # Urgent leads
    if urgent > 0:
        tips.append(f"🔴 **{urgent} leads waiting 24h+** without contact! Speed-to-lead is critical — contact them within 5 minutes for 10x higher conversion.")

    # Attendance
    if absent > 3:
        tips.append(f"👋 **{absent} members absent 15+ days.** Reach out personally — a quick WhatsApp or call can prevent cancellations. Members who stop training are 80% likely to cancel within 30 days.")

    # Revenue per member
    if rpm > 0 and rpm < 100:
        tips.append(f"💡 **${rpm:.0f}/member is below industry average** ($150-200). Consider: premium tiers, private lessons, merchandise, or small price increases.")

    # Payroll ratio
    if revenue > 0 and payroll / revenue > 0.4:
        tips.append(f"👥 **Payroll is {payroll/revenue*100:.0f}% of revenue** (ideal: 30-40%). Consider revenue-share or commission-based pay for instructors.")

    if not tips:
        tips.append("📊 Add more data (expenses, payroll, leads) to get personalized insights from Marcos.")

    return "\n\n".join(tips)
