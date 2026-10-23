"""
Prompt templates for Gemini API calls.

Each prompt function constructs a structured prompt that:
1. Receives retrieved evidence as context.
2. Instructs Gemini to distinguish sourced facts from missing information.
3. Never asks Gemini to invent sources, dates, or amounts.
4. Requests structured JSON output matching our Pydantic schemas.
"""

from typing import List


def build_scheme_research_prompt(query: str, retrieved_passages: List[dict]) -> str:
    """
    Build a prompt for comprehensive scheme research.

    Args:
        query: The user's search query.
        retrieved_passages: List of dicts with keys: url, title, publisher,
                            published_date, text.

    Returns:
        A structured prompt string.
    """
    passages_text = _format_passages(retrieved_passages)

    return f"""You are a fact-checking assistant specialising in Indian government schemes and public policy.

Your task is to analyse the USER QUERY and the RETRIEVED EVIDENCE below, and produce a structured JSON research result.

CRITICAL RULES — YOU MUST FOLLOW THESE EXACTLY:
1. Only use facts that are explicitly stated in the RETRIEVED EVIDENCE below.
2. If a field cannot be determined from the evidence, set it to null and add the field name to "data_gaps".
3. Do NOT invent dates, amounts, names, URLs, quotations, or document titles.
4. Do NOT treat your training knowledge as a source. Only use the RETRIEVED EVIDENCE.
5. Clearly distinguish between officially stated reasons (from government records) and independent analysis.
6. Do not label a claim false merely because no supporting source was found — use "insufficient_evidence" instead.
7. When sources disagree, include both versions and note the disagreement.

TIMELINE REQUIREMENT — VERY IMPORTANT:
- Extract EVERY timeline event from the scheme's launch date all the way to the most recent event in the evidence.
- Do NOT limit to recent years. Include the launch event, every amendment, every budget update, every leadership change, and every eligibility change found in the evidence.
- List events in chronological order, oldest first.
- If the evidence mentions any date-linked event, it must appear as a timeline entry.

BUDGET REQUIREMENT:
- Extract budget records for EVERY financial year mentioned in the evidence — from the first year to the most recent.
- Do not skip any year. Include years with partial data (mark data_gaps accordingly).

USER QUERY:
{query}

RETRIEVED EVIDENCE:
{passages_text}

Produce a JSON object matching this exact structure (omit fields that are null):
{{
  "query": "<original query>",
  "scheme_name": "<official scheme name or null>",
  "overview": {{
    "name": "<official name>",
    "abbreviation": "<abbreviation or null>",
    "category": "<agriculture|education|health|housing|infrastructure|livelihood|nutrition|social_protection|women_child|other>",
    "jurisdiction": "<central|state|joint>",
    "country": "India",
    "state": "<state name or null>",
    "launch_date": "<YYYY-MM-DD or null>",
    "original_objectives": "<from sources or null>",
    "intended_beneficiaries": "<from sources or null>",
    "application_portal": "<URL or null>",
    "operational_status": "<active|discontinued|merged|suspended|unknown>",
    "confidence": "<high|medium|low>",
    "data_gaps": ["<list of unavailable fields>"],
    "source_urls": ["<URLs used>"]
  }},
  "timeline_events": [
    {{
      "event_type": "<launch|amendment|budget_update|eligibility_change|leadership_change|suspension|revival|merger|evaluation_report|other>",
      "title": "<short title>",
      "description": "<detailed description from sources>",
      "event_date": "<YYYY-MM-DD or null>",
      "announced_date": "<YYYY-MM-DD or null>",
      "responsible_ministry": "<ministry name or null>",
      "responsible_leader": "<documented official or null — do not assume based on who was PM>",
      "verification_status": "<verified|partially_verified|unverified|disputed>",
      "source_urls": ["<URLs>"],
      "data_gaps": []
    }}
  ],
  "amendments": [...],
  "budget_records": [
    {{
      "financial_year": "<YYYY-YY>",
      "budget_estimate": <number or null>,
      "revised_estimate": <number or null>,
      "actual_expenditure": <number or null>,
      "amount_unit": "<crore|lakh|million|actual>",
      "currency": "INR",
      "source_url": "<URL or null>",
      "source_title": "<document title or null>",
      "verification_status": "<verified|partially_verified|unverified|disputed>",
      "data_gaps": []
    }}
  ],
  "leadership_records": [
    {{
      "leader_name": "<name or null>",
      "role": "<prime_minister|chief_minister|cabinet_minister|minister_of_state|secretary|other>",
      "party": "<party name or null>",
      "government_name": "<government name or null>",
      "coalition": "<coalition name or null>",
      "ministry": "<ministry name or null>",
      "portfolio": "<portfolio or null>",
      "tenure_start": "<YYYY-MM-DD or null>",
      "tenure_end": "<YYYY-MM-DD or null>",
      "responsibility_type": "<launch|administration|amendment>",
      "source_urls": [],
      "data_gaps": []
    }}
  ],
  "source_urls_searched": ["<all URLs in evidence>"],
  "confidence": "<high|medium|low>",
  "data_gaps": ["<top-level missing information>"],
  "ai_model_used": null
}}

Respond with ONLY the JSON object. No markdown code fences, no commentary outside the JSON.
"""



def build_fact_check_prompt(claim: str, retrieved_passages: List[dict]) -> str:
    """
    Build a prompt for verifying a single factual claim.

    Args:
        claim: The claim to verify.
        retrieved_passages: Evidence passages retrieved for this claim.

    Returns:
        A structured prompt string.
    """
    passages_text = _format_passages(retrieved_passages)

    return f"""You are a fact-checking assistant specialising in Indian government schemes and public policy.

Verify the CLAIM below using ONLY the RETRIEVED EVIDENCE. Do not use your training knowledge as a source.

CRITICAL RULES:
1. A claim is NOT false merely because no supporting source was found. Use "insufficient_evidence" in that case.
2. When evidence conflicts, include both supporting and contradicting evidence. Do not remove contradicting evidence.
3. Every evidence item must include the exact text from the source and its URL.
4. Assign confidence based on the quantity and quality of retrieved evidence, not assumptions.
5. Do NOT fabricate source URLs, publication dates, or quotations.

CLAIM TO VERIFY:
{claim}

RETRIEVED EVIDENCE:
{passages_text}

Produce a JSON object with this structure:
{{
  "original_claim": "<exact claim text>",
  "verdict": "<supported|contradicted|partially_supported|insufficient_evidence|outdated>",
  "explanation": "<clear, transparent explanation of the verdict>",
  "supporting_evidence": [
    {{
      "text": "<exact passage from source>",
      "source_url": "<URL>",
      "source_title": "<document title or null>",
      "publisher": "<publisher name or null>",
      "publication_date": "<YYYY-MM-DD or null>",
      "event_date": "<YYYY-MM-DD or null>",
      "stance": "supports"
    }}
  ],
  "contradicting_evidence": [...],
  "confidence": "<high|medium|low>",
  "confidence_explanation": "<why this confidence level>",
  "verified_at": null,
  "data_gaps": ["<what information was missing>"]
}}

Respond with ONLY the JSON object. No markdown, no commentary.
"""


def _format_passages(passages: List[dict]) -> str:
    """Format retrieved passages into a readable evidence block."""
    if not passages:
        return 'No evidence was retrieved. All fields should be null and data_gaps should reflect this.'

    lines = []
    for i, p in enumerate(passages, 1):
        lines.append(f'--- SOURCE {i} ---')
        lines.append(f'URL: {p.get("url", "unknown")}')
        lines.append(f'Title: {p.get("title", "unknown")}')
        lines.append(f'Publisher: {p.get("publisher", "unknown")}')
        lines.append(f'Published: {p.get("published_date", "unknown")}')
        lines.append(f'Content:\n{p.get("text", "")}')
        lines.append('')
    return '\n'.join(lines)
