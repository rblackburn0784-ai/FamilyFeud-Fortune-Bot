import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

QUESTION_FILES = [
    Path("questions.json"),
    Path("extra_questions.json"),
    Path("mega_questions.json"),
]


def load_questions():
    questions = []

    for path in QUESTION_FILES:
        if not path.exists():
            continue

        for index, item in enumerate(json.loads(path.read_text(encoding="utf-8")), start=1):
            questions.append((path.name, index, item))

    return questions


def validate_questions(questions):
    issues = []
    seen = set()

    for source, index, item in questions:
        question = item.get("question", "").strip()
        category = item.get("category", "general")
        answers = item.get("answers", [])
        signature = (category.lower(), question.lower(), tuple(answer.get("text", "").lower() for answer in answers))

        if signature in seen:
            issues.append(f"{source}:{index} duplicate full question")

        seen.add(signature)

        if not question:
            issues.append(f"{source}:{index} missing question")

        if len(answers) < 2:
            issues.append(f"{source}:{index} fewer than two answers")

        answer_seen = set()

        for answer in answers:
            text = answer.get("text", "").strip().lower()

            if not text:
                issues.append(f"{source}:{index} blank answer")

            if text in answer_seen:
                issues.append(f"{source}:{index} duplicate answer {text}")

            answer_seen.add(text)

            if int(answer.get("points", 0)) <= 0:
                issues.append(f"{source}:{index} non-positive points")

    return issues


class QuestionManagerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        search = query.get("q", [""])[0].lower().strip()
        category = query.get("category", [""])[0].lower().strip()
        questions = load_questions()

        if search:
            questions = [
                item
                for item in questions
                if search in item[2].get("question", "").lower()
            ]

        if category:
            questions = [
                item
                for item in questions
                if item[2].get("category", "").lower() == category
            ]

        issues = validate_questions(load_questions())
        categories = sorted({item[2].get("category", "general") for item in load_questions()})
        rows = []

        for source, index, item in questions[:300]:
            answers = ", ".join(
                f"{answer.get('text')} ({answer.get('points')})"
                for answer in item.get("answers", [])
            )
            rows.append(
                "<tr>"
                f"<td>{html.escape(source)}:{index}</td>"
                f"<td>{html.escape(item.get('category', 'general'))}</td>"
                f"<td>{html.escape(item.get('difficulty', 'normal'))}</td>"
                f"<td>{html.escape(item.get('question', ''))}</td>"
                f"<td>{html.escape(answers)}</td>"
                "</tr>"
            )

        category_options = "".join(
            f"<option value='{html.escape(cat)}'>{html.escape(cat)}</option>"
            for cat in categories
        )
        body = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Family Fortunes Question Manager</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 24px; background: #f8fafc; color: #172033; }}
    form {{ display: flex; gap: 8px; margin-bottom: 16px; }}
    input, select, button {{ padding: 8px; }}
    table {{ border-collapse: collapse; width: 100%; background: white; }}
    th, td {{ border: 1px solid #d8dee9; padding: 8px; vertical-align: top; }}
    th {{ background: #eef2f7; text-align: left; }}
    .status {{ margin-bottom: 12px; }}
  </style>
</head>
<body>
  <h1>Family Fortunes Question Manager</h1>
  <p class="status">Showing {len(questions[:300])} of {len(questions)} matching questions. Validation issues: {len(issues)}.</p>
  <form>
    <input name="q" placeholder="Search questions" value="{html.escape(search)}">
    <select name="category"><option value="">All categories</option>{category_options}</select>
    <button>Search</button>
  </form>
  <table>
    <tr><th>Source</th><th>Category</th><th>Difficulty</th><th>Question</th><th>Answers</th></tr>
    {''.join(rows)}
  </table>
</body>
</html>
"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8765), QuestionManagerHandler)
    print("Question manager running at http://127.0.0.1:8765")
    server.serve_forever()
