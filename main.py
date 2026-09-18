from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import re
import sys
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"


def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()


class TextInput(BaseModel):
    text:         str
    systemPrompt: str | None = None
    detailed:     bool = False

@app.get("/")
def root():
    return {"status": "Exam Notes backend running"}

@app.post("/api/generate-notes-from-text")
async def generate_notes(data: TextInput):
    text = data.text.strip()
    detailed = data.detailed
    log(f"[NOTES] received text_len={len(text)} detailed={detailed}")

    if not text or len(text) < 15:
        return {
            "title":   "Cannot Extract",
            "content": "• Could not extract meaningful text.\n• Try a clearer image with visible text."
        }

    if not GROQ_API_KEY:
        log("[NOTES] GROQ_API_KEY missing")
        return fallback_notes(text)

    # Detailed mode gets a higher input ceiling (larger scans need more room)
    MAX_INPUT_CHARS = 16000 if detailed else 9000
    if len(text) > MAX_INPUT_CHARS:
        log(f"[NOTES] truncating input from {len(text)} to {MAX_INPUT_CHARS} chars")
        text = text[:MAX_INPUT_CHARS]

    try:
        word_count = len(text.split())

        if detailed:
            max_sections   = 6 if word_count < 300 else 8 if word_count < 600 else 10
            bullets_per    = "5-6" if word_count < 300 else "6-7"
            bullet_min     = 14
            bullet_max     = 22
            detailed_note  = (
                "- DETAILED MODE: cover more secondary details, examples, and sub-points "
                "in addition to core facts — write fuller explanations while still keeping "
                "each bullet a single complete thought.\n"
            )
        else:
            max_sections   = 4 if word_count < 300 else 5 if word_count < 600 else 7
            bullets_per    = "3-4" if word_count < 300 else "4-5"
            bullet_min     = 9
            bullet_max     = 13
            detailed_note  = ""

        prompt = f"""You are an expert note-taking assistant that converts any scanned or pasted text into clean, organized, easy-to-study notes.

Your job has TWO parts:

PART 1 — Generate a smart title:
- Read the ENTIRE text and create a short meaningful title (4-7 words max)
- Title should describe the MAIN CONTENT, not just copy the first words
- Example: "Photosynthesis: Light and Dark Reactions" or "Weekly Class Timetable" or "Team Meeting Action Items"

PART 2 — Generate CONCISE, well-organized notes:
- Read the ENTIRE text carefully from start to finish
- This tool works for ANY real content, not just textbooks — school/class timetables, schedules, meeting notes, recipes, instructions, forms, general topics, articles, personal notes, checklists, plans, and academic material are ALL valid and should all produce clean organized notes
- Do NOT just copy headings or phrases from the source as bullet points
- Each bullet must be a COMPLETE, USEFUL PIECE OF INFORMATION — not a bare topic name
- BAD bullet: "Calculating Variance and Standard Deviation"
- GOOD bullet: "Variance measures spread from the mean; average of squared differences"
- For a timetable/schedule: each bullet should state the actual time/day/subject/event clearly, e.g. "Monday 9-10am: Mathematics with Mr. Khan"
- For academic content: combine what the source says WITH your own expert knowledge for complete, useful notes
- Be concise: only the MOST important, useful information — skip filler
- For math topics: write formulas using plain text only — e.g. "a^2 + b^2 = c^2" NOT "$a^2 + b^2 = c^2$"
- NEVER use LaTeX syntax — no $ signs, no \\frac, no \\sqrt, no \\cdot, no backslashes
- Write math naturally: use ^ for powers, / for fractions, sqrt() for roots
- Group related points under short section headings (e.g. days of the week for a timetable, topics for study material, agenda items for meeting notes)
- Section heading format: ALL CAPS, no bullet, e.g. "FORMULA" or "MONDAY" or "ACTION ITEMS"
- Each bullet point starts with "• "
- {bullets_per} bullets per section MAXIMUM (no repetition, be selective)
- Aim for AT LEAST 3-4 sections when the content has enough distinct groups to support it, up to {max_sections} MAXIMUM
- Do not force multiple sections on very short or single-topic text — only split into more sections if there is genuinely enough distinct content
- STRICT LENGTH RULE: each bullet must be {bullet_min}-{bullet_max} words, NEVER more than {bullet_max}
- CRITICAL: every bullet must be a COMPLETE sentence/thought — NEVER cut off mid-word or mid-phrase
- If a fact needs more than {bullet_max} words to complete, shorten the wording instead of cutting it off — an unfinished bullet is worse than a slightly denser one
- Do not start a bullet or section you cannot finish within the remaining space — finish EVERY bullet and EVERY section you begin, never leave a trailing incomplete line
- Write each bullet so it reads as a short, complete, punchy sentence — avoid trailing filler words or clauses that spill onto an extra line
- Do not pad bullets to sound formal — shorter and clearer is always better
- Always write full information — never truncate mid-sentence, but keep it tight
{detailed_note}
IMPORTANT — When to actually refuse (be EXTREMELY reluctant to refuse):
- This text came from a photo or paste of REAL content a real person is trying to organize — a textbook page, a timetable, handwritten notes, a schedule, a to-do list, an article, meeting notes, or any other genuine written material. OCR is never perfect — expect occasional garbled words, missing punctuation, odd line breaks, or a few unclear phrases. This is NORMAL and NOT a reason to refuse.
- This tool is NOT limited to academic subjects. Timetables, schedules, plans, lists, instructions, general topics, conversations about a real subject, and any other genuine informational content are ALL valid and must produce real notes.
- Even if parts of the text look imperfect, incomplete, fragmented, or slightly broken from scanning — you MUST still generate real, organized notes from whatever real content is present. Use your own knowledge to fill small gaps and interpret unclear words sensibly.
- ONLY respond with exactly "CANNOT_EXTRACT" if the text is truly meaningless — e.g. it is random keyboard mashing, pure gibberish with zero real words, a completely blank/empty extraction, or contains no identifiable real-world information whatsoever.
- Do NOT respond with CANNOT_EXTRACT just because the content isn't "educational" in a narrow sense, has typos, looks like a rough OCR scan, or is a non-academic document like a timetable, list, or casual note. Any real, organizable content is a valid input.

Respond in this exact format:
TITLE: <your title here>
NOTES:
<SECTION HEADING>
• bullet
• bullet
<SECTION HEADING>
• bullet
• bullet

Text to convert:
{text}"""

        max_tokens = 3500 if detailed else 2200

        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model": "openai/gpt-oss-120b",
                    "messages":    [{"role": "user", "content": prompt}],
                    "max_tokens":  max_tokens,
                    "temperature": 0.2,
                    "reasoning_effort": "low",
                },
            )

        log(f"[NOTES] Groq status={response.status_code}")

        try:
            result = response.json()
        except Exception:
            log(f"[NOTES] Non-JSON response: {response.text[:500]}")
            return fallback_notes(text)

        if "error" in result:
            error_msg = result["error"].get("message", "Unknown Groq error")
            log(f"[NOTES] Groq API error: {error_msg}")
            if "reasoning_effort" in error_msg:
                log("[NOTES] retrying without reasoning_effort param")
                async with httpx.AsyncClient(timeout=45) as client:
                    response = await client.post(
                        GROQ_URL,
                        headers={
                            "Authorization": f"Bearer {GROQ_API_KEY}",
                            "Content-Type":  "application/json",
                        },
                        json={
                            "model": "openai/gpt-oss-120b",
                            "messages":    [{"role": "user", "content": prompt}],
                            "max_tokens":  max_tokens,
                            "temperature": 0.2,
                        },
                    )
                result = response.json()
                if "error" in result:
                    log(f"[NOTES] Retry also failed: {result['error']}")
                    return fallback_notes(text)
            else:
                return fallback_notes(text)

        if not result.get("choices"):
            log(f"[NOTES] Groq empty choices. Full response: {result}")
            return fallback_notes(text)

        choice = result["choices"][0]
        finish_reason = choice.get("finish_reason")
        usage = result.get("usage", {})
        message = choice.get("message", {})
        raw_response = (message.get("content") or "").strip()
        reasoning_field = message.get("reasoning", "") or ""

        log(f"[NOTES] finish_reason={finish_reason} usage={usage} "
            f"content_len={len(raw_response)} reasoning_len={len(reasoning_field)}")

        if finish_reason == "length":
            log("[NOTES] WARNING: response was truncated by max_tokens limit")

        if not raw_response and reasoning_field:
            # Only trust the reasoning field as a fallback if it actually
            # contains the expected TITLE:/NOTES: structure. If reasoning
            # ran away and consumed the whole token budget, the reasoning
            # field is raw unstructured thinking -- never show that to
            # the user as if it were finished notes.
            if "TITLE:" in reasoning_field and "NOTES:" in reasoning_field:
                raw_response = reasoning_field.strip()
            else:
                log(f"[NOTES] Reasoning field lacks TITLE:/NOTES: structure "
                    f"(finish_reason={finish_reason}, reasoning_len={len(reasoning_field)}). "
                    f"Treating as failed generation, using fallback_notes().")
                return fallback_notes(text)

        if not raw_response:
            log(f"[NOTES] Truly empty response. finish_reason={finish_reason}")
            return fallback_notes(text)

        if finish_reason == "length" and len(raw_response) < 50:
            log(f"[NOTES] Response too short after truncation "
                f"(len={len(raw_response)}). Using fallback_notes().")
            return fallback_notes(text)

        if "CANNOT_EXTRACT" in raw_response:
            return {
                "title":   "Cannot Extract",
                "content": "• Could not find meaningful content in this image.\n• Try a clearer photo, or make sure there's readable text visible."
            }

        title = "Untitled Note"
        if "TITLE:" in raw_response:
            title_line = raw_response.split("TITLE:")[1].split("\n")[0].strip()
            if title_line:
                title = title_line

        content = raw_response
        if "NOTES:" in raw_response:
            content = raw_response.split("NOTES:")[1].strip()

        content = drop_trailing_incomplete_bullet(content, finish_reason)

        if title == "Untitled Note" or not content.strip():
            log(f"[NOTES] Malformed output despite passing earlier checks "
                f"(title={title!r}, content_len={len(content)}). Using fallback_notes().")
            return fallback_notes(text)

        log(f"[NOTES] Success. title={title!r} content_len={len(content)}")
        return {"title": title, "content": content}

    except Exception as e:
        log(f"[NOTES EXCEPTION] {type(e).__name__}: {e}")
        return fallback_notes(text)


def drop_trailing_incomplete_bullet(content: str, finish_reason: str) -> str:
    """
    If the Groq response was cut off by the max_tokens limit, the last
    line (and possibly a dangling section heading with zero bullets
    under it) is often incomplete. Drop both so the user never sees a
    half-written bullet or an empty trailing heading.
    """
    if finish_reason != "length":
        return content
    lines_ = content.rstrip("\n").split("\n")
    if not lines_:
        return content
    last = lines_[-1].strip()
    ends_clean = last.endswith((".", ";", ":", "!", "?"))
    if not ends_clean:
        log(f"[NOTES] Dropping likely-truncated trailing line: {last!r}")
        lines_ = lines_[:-1]
    while lines_:
        candidate = lines_[-1].strip()
        if candidate and not candidate.startswith("•"):
            log(f"[NOTES] Dropping dangling empty heading: {candidate!r}")
            lines_ = lines_[:-1]
        else:
            break
    return "\n".join(lines_).rstrip()


def fallback_notes(text: str) -> dict:
    log("[NOTES] Using fallback_notes()")
    words     = text.split()
    title     = " ".join(words[:6]) + ("..." if len(words) > 6 else "")
    sentences = re.split(r'(?<=[.!?])\s+', text)
    bullets   = []
    for sentence in sentences:
        sentence = sentence.strip().strip(".")
        if len(sentence) > 20:
            bullets.append(f"• {sentence}")
        if len(bullets) >= 8:
            break
    if not bullets:
        bullets = ["• Could not extract meaningful content. Try a clearer image."]
    return {"title": title, "content": "\n".join(bullets)}
