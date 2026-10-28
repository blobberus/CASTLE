"""Harvest the 30 real AI contestants' answers from Claude Code subagent transcripts.

Each AI contestant was a fresh Claude subagent (haiku / sonnet / opus) given only
the verbatim Trial.txt text wrapped in one of five "how a person asks an AI"
framings. Its reply ends in a ```json block with game1, game2, strategy_text
and reasoning_summary. This script finds that block, validates it, and writes
contestants/ai_contestants.json.

Usage: python collect_ai_contestants.py <path-to-session>/subagents
       python collect_ai_contestants.py <subagents> --prefix "M3 AI contestant" --id-prefix M3-AI               --out ../model3_simulation_500/contestants/ai_contestants.json               --prompts-dir ../model3_simulation_500/contestants/prompts      (model 3)
Model-3 contestants received a one-line instruction to Read their prompt file
(the same text model 2 received inline). The check below flags any contestant
that used a tool other than that single Read.
(Only needed once per model; the harvested JSON is committed, so the rest of
the pipeline never needs the transcripts.)
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
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
    """[(tool name, target)] for every tool call other than the final handback."""
    used = []
    for line in transcript.open(encoding="utf-8"):
        content = json.loads(line).get("message", {}).get("content")
        for part in content if isinstance(content, list) else []:
            if part.get("type") == "tool_use" and part.get("name") != "SubagentHandback":
                inp = part.get("input", {})
                used.append((part["name"], inp.get("file_path") or inp.get("command") or inp.get("pattern") or ""))
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subagents_dir")
    ap.add_argument("--prefix", default="AI contestant", help="description prefix used when the agents were launched")
    ap.add_argument("--id-prefix", default="AI")
    ap.add_argument("--out", default=str(HERE / "contestants" / "ai_contestants.json"))
    ap.add_argument("--prompts-dir", default=None, help="model 3: folder holding the prompt files the agents read")
    args = ap.parse_args()
    desc = re.compile(rf"{re.escape(args.prefix)} #(\d+) (\w+)/(\w+)")
    out_path = Path(args.out)
    subagents_dir = args.subagents_dir
    rows = []
    for meta_path in sorted(Path(subagents_dir).glob("agent-*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        m = desc.match(meta.get("description", ""))
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
        tools = tools_used(transcript)
        reads = [t for n, t in tools if n == "Read"]
        prompt_file = Path(reads[0]).name if reads else None
        sent = prompt_sent(transcript)
        if prompt_file and args.prompts_dir and (Path(args.prompts_dir) / prompt_file).exists():
            header = f"--- contents of {prompt_file} ---"
            sent = "\n\n".join([sent, header, (Path(args.prompts_dir) / prompt_file).read_text(encoding="utf-8")])
        width = 3 if args.id_prefix != "AI" else 2
        rows.append({
            "id": f"{args.id_prefix}{cid:0{width}d}",
            "framing": framing,
            "framing_description": FRAMING_TEXT.get(framing, ""),
            "model": model,
            "replicate": int(prompt_file.split("_w")[1][0]) if prompt_file else (cid - 1) % 2,
            "prompt_file": prompt_file,
            "game1": g1, "game2": g2,
            "game1_valid": len(g1) == 5 and sum(g1) == 100 and min(g1) >= 0,
            "game2_valid": len(g2) == 5 and sum(g2) == 100 and min(g2) >= 0,
            "strategy_text": answer.get("strategy_text", ""),
            "reasoning_summary": answer.get("reasoning_summary", ""),
            "prompt_sent": sent,
            "full_reply": reply,
            "non_handback_tools_used": [n for n, _ in tools],
            "isolation_ok": (not args.prompts_dir and not tools) or
                            (bool(args.prompts_dir) and len(tools) == 1 and tools[0][0] == "Read"
                             and prompt_file is not None and prompt_file.startswith(framing)),
        })
    seen = {}
    for r in rows:   # a relaunched contestant can leave two transcripts; keep one answer per id
        if r["id"] in seen:
            print(f"{r['id']}: duplicate transcript ignored", file=sys.stderr)
        else:
            seen[r["id"]] = r
    rows = sorted(seen.values(), key=lambda r: r["id"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(rows)} AI contestants to {out_path}; isolation problems: "
          f"{[r['id'] for r in rows if not r['isolation_ok']] or 'none'}")
    for r in rows:
        flag = "" if r["game1_valid"] and r["game2_valid"] else "  <-- INVALID TOTAL"
        tools = "" if r["isolation_ok"] else f"  CHECK tools={r['non_handback_tools_used']}"
        print(f"{r['id']} {r['framing']:<12}{r['model']:<7} G1 {'/'.join(map(str, r['game1'])):<16} "
              f"G2 {'/'.join(map(str, r['game2'])):<16}{flag}{tools}")


if __name__ == "__main__":
    main()
