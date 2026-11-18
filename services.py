import os, re, json, urllib.request, urllib.error
from datetime import datetime, date, time
from dateutil import parser as date_parser

CATEGORIES = ["Assignments", "Examinations", "Events", "Workshops", "Registrations",
              "Academic Announcements", "Fee Payments", "Other"]

def extract_document(path, extension):
    ext = extension.lower()
    if ext == ".pdf":
        import fitz
        doc = fitz.open(path)
        return "\n".join(page.get_text("text") for page in doc).strip()
    if ext in (".jpg", ".jpeg", ".png"):
        from PIL import Image, ImageOps
        import pytesseract
        img = Image.open(path)
        img = ImageOps.exif_transpose(img).convert("RGB")
        return pytesseract.image_to_string(img).strip()
    if ext == ".txt":
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            return f.read().strip()
    raise ValueError("Unsupported file type.")

def analyze_notice(text):
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        raise ValueError("No readable text was found. Try a clearer scan or paste the notice text.")
    low = clean.lower()
    rules = [
        ("Assignments", ["assignment", "submission", "submit", "coursework", "practical file"]),
        ("Examinations", ["exam", "examination", "timetable", "hall ticket", "assessment", "viva"]),
        ("Workshops", ["workshop", "bootcamp", "hands-on"]),
        ("Registrations", ["registration", "register", "enrolment", "enrollment", "application form"]),
        ("Fee Payments", ["fee", "payment", "tuition", "pay online"]),
        ("Events", ["event", "fest", "seminar", "competition", "hackathon", "webinar"]),
    ]
    category = next((cat for cat, words in rules if any(w in low for w in words)), "Academic Announcements")
    title = next((line.strip(" -:\t") for line in text.splitlines() if len(line.strip()) > 8), "College notice")
    title = title[:220]
    date_matches = []
    patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[, ]+\d{2,4}\b",
        r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?[,]?\s+\d{2,4}\b"
    ]
    for pat in patterns:
        date_matches.extend(re.findall(pat, text, flags=re.I))
    parsed = []
    for value in dict.fromkeys(date_matches):
        try:
            dt = date_parser.parse(value, dayfirst=True, fuzzy=False)
            if 2000 <= dt.year <= 2100:
                parsed.append((value, dt.date()))
        except (ValueError, OverflowError):
            pass
    due = None
    if parsed:
        deadline_words = ["deadline", "last date", "submit", "submission", "due", "by "]
        prioritized = [p for p in parsed if any(w in low[max(0, low.find(p[0].lower())-90):low.find(p[0].lower())+len(p[0])+30] for w in deadline_words)]
        due = (prioritized or parsed)[0][1]
    venue_match = re.search(r"(?:venue|location|at)\s*[:\-]?\s*([A-Z][A-Za-z0-9 ,./()\-]{2,70})", text, re.I)
    venue = venue_match.group(1).strip() if venue_match else ""
    instruction_lines = []
    for line in text.splitlines():
        s = line.strip()
        if re.search(r"\b( submit| bring| carry| register| upload| attend| report| pay| complete| contact)\b", " "+s.lower()):
            instruction_lines.append(s)
    instructions = "\n".join(instruction_lines[:8]) or ""
    priority = "High" if any(w in low for w in ["urgent", "mandatory", "compulsory", "final deadline", "immediately"]) else "Medium"
    return {
        "title": title, "category": category, "dates": [{"text": x, "date": d.isoformat()} for x,d in parsed],
        "due_date": due.isoformat() if due else "", "venue": venue,
        "instructions": instructions, "priority": priority,
        "action_suggested": category in ("Assignments", "Registrations", "Fee Payments") or bool(due),
    }

def answer_from_notices(question, notices):
    if not notices:
        return "I couldn't find any uploaded notices yet. Upload a notice first, then ask me about it."
    context = "\n\n".join(f"NOTICE {n.id}: {n.title} | {n.category}\n{n.extracted_text[:5000]}" for n in notices)
    api_key = os.getenv("AI_API_KEY")
    if api_key:
        prompt = ("Answer only from the notice context below. If the answer is not present, say "
                  "'I couldn't find that information in your uploaded notices.' Cite notice IDs. "
                  "Do not infer missing dates or requirements.\n\nCONTEXT:\n"+context+"\n\nQUESTION:"+question)
        payload = json.dumps({"model": os.getenv("AI_MODEL","gpt-4o-mini"),
            "messages":[{"role":"system","content":"You are Ask NoticeIQ, a careful college notice assistant."},
                        {"role":"user","content":prompt}],
            "temperature":0.1}).encode()
        req = urllib.request.Request(os.getenv("AI_BASE_URL","https://api.openai.com/v1").rstrip("/")+"/chat/completions",
             data=payload, headers={"Authorization":"Bearer "+api_key,"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                data=json.loads(response.read().decode())
                return data["choices"][0]["message"]["content"].strip()
        except Exception:
            pass
    terms = [w for w in re.findall(r"[a-zA-Z]{3,}", question.lower()) if w not in
             {"when","what","which","where","about","does","have","from","with","your","this","that","next","latest","notice","tell","please","there","happening"}]
    scored=[]
    for n in notices:
        hay=(n.title+" "+n.category+" "+n.extracted_text+" "+(n.instructions or "")).lower()
        score=sum(1 for t in terms if t in hay)
        if score: scored.append((score,n))
    scored.sort(key=lambda x:x[0], reverse=True)
    if not scored:
        return "I couldn't find that information in your uploaded notices. Try asking with a course name, event name, or a more specific phrase."
    results=[]
    for _,n in scored[:3]:
        excerpt=n.extracted_text[:900].strip()
        results.append(f"From **{n.title}** (Notice #{n.id}):\n{excerpt}")
    return "\n\n".join(results)+"\n\n*Fallback answer: based on matching text in your saved notices. Verify the original notice for full details.*"
