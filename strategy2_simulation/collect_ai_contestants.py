"""Harvest the 30 real AI contestants' answers from Claude Code subagent transcripts.

Each AI contestant was a fresh Claude subagent (haiku / sonnet / opus) given only
the verbatim Trial.txt text wrapped in one of five "how a person asks an AI"
framings. Its reply ends in a ```json block with game1, game2, strategy_text
and reasoning_summary. This script finds that block, validates it, and writes
contestants/ai_contestants.json.

Usage: python collect_ai_contestants.py <path-to-session>/subagents
(Only needed once; the harvested JSON is committed, so the rest of the
pipeline never needs the transcripts.)
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "contestants" / "ai_contestants.json"
DESC = re.compile(r"AI contestant #(\d+) (\w+)/(\w+)")
FRAMING_TEXT = {
    "verbatim": "Pasted the Trial text and nothing else (r1 adds 'Hi!').",
    "optimal": "Pasted the Trial text and asked for the optimal / best-scoring allocation.",
    "quick": "Said they only had 3 minutes and wanted numbers fast.",
    "field_aware": "Asked the AI to predict other (mostly AI-using) applicants and beat them.",
    "game_theory": "Asked the AI to use game theory (Blotto / Nash equilibrium).",
}


def texts_from(transcript):
    """Yield every candidate reply text, oldest first (handback messages and assistant text)."""
    for line in transcript.open(encoding="utf-8"):
        d = json.loads(line)
        if d.get("type") != "assistant":
            continue
        for part in d.get("message", {}).get("content") or []:
            if part.get("type") == "text":
                yield part["text"]
            elif part.get("type") == "tool_use" and part.get("name") == "SubagentHandback":
                yield part["input"].get("message", "")


def prompt_sent(transcript):
    """The first user message: exactly what the contestant was sent (header + framed Trial text)."""
    for line in transcript.open(encoding="utf-8"):
        d = json.loads(line)
        if d.get("type") == "user":
            c = d.get("message", {}).get("content")
            return c if isinstance(c, str) else "".join(p.get("text", "") for p in c if isinstance(p, dict))
    return ""


def tools_used(transcript):
    used = []
    for line in transcript.open(encoding="utf-8"):
        content = json.loads(line).get("message", {}).get("content")
        for part in content if isinstance(content, list) else []:
            if part.get("type") == "tool_use" and part.get("name") != "SubagentHandback":
                used.append(part["name"])
    return used


def extract(text):
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, flags=re.S)
    if not blocks:
        blocks = re.findall(r"(\{[^{}]*\"game1\"[^{}]*\})", text, flags=re.S)
    for b in reversed(blocks):
        try:
            obj = json.loads(b)
        except json.JSONDecodeError:
            continue
        if "game1" in obj and "game2" in obj:
            return obj
    return None


def main(subagents_dir):
    rows = []
    for meta_path in sorted(Path(subagents_dir).glob("agent-*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        m = DESC.match(meta.get("description", ""))
        if not m:
            continue
        cid, framing, model = int(m.group(1)), m.group(2), m.group(3)
        transcript = meta_path.with_name(meta_path.name.replace(".meta.json", ".jsonl"))
        texts = list(texts_from(transcript))
        answer, reply = None, ""
        for t in reversed(texts):
            answer = extract(t)
            if answer:
                reply = t
                break
        if answer is None:
            print(f"#{cid:02d}: no JSON answer found", file=sys.stderr)
            continue
        g1, g2 = [int(x) for x in answer["game1"]], [int(x) for x in answer["game2"]]
        rows.append({
            "id": f"AI{cid:02d}",
            "framing": framing,
            "framing_description": FRAMING_TEXT.get(framing, ""),
            "model": model,
            "replicate": (cid - 1) % 2,
            "game1": g1, "game2": g2,
            "game1_valid": len(g1) == 5 and sum(g1) == 100 and min(g1) >= 0,
            "game2_valid": len(g2) == 5 and sum(g2) == 100 and min(g2) >= 0,
            "strategy_text": answer.get("strategy_text", ""),
            "reasoning_summary": answer.get("reasoning_summary", ""),
            "prompt_sent": prompt_sent(transcript),
            "full_reply": reply,
            "non_handback_tools_used": tools_used(transcript),
        })
    rows.sort(key=lambda r: r["id"])
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(rows)} AI contestants to {OUT}")
    for r in rows:
        flag = "" if r["game1_valid"] and r["game2_valid"] else "  <-- INVALID TOTAL"
        tools = f"  tools={r['non_handback_tools_used']}" if r["non_handback_tools_used"] else ""
        print(f"{r['id']} {r['framing']:<12}{r['model']:<7} G1 {'/'.join(map(str, r['game1'])):<16} "
              f"G2 {'/'.join(map(str, r['game2'])):<16}{flag}{tools}")


if __name__ == "__main__":
    main(sys.argv[1])
