import ast
import json
import operator
import os
import re
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        v = _eval(node.operand)
        return v if isinstance(node.op, ast.UAdd) else -v
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        a, b = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and (abs(b) > 100 or abs(a) > 1e6):
            raise ValueError("power too large")
        return OPS[type(node.op)](a, b)
    raise ValueError("unsupported expression")


def calculator(text):
    results = []
    for cand in re.findall(r"[\d(][\d\s.+\-*/^%()]*[\d)]", text):
        cand = cand.strip()
        if not re.search(r"\d\s*[-+*/^%]\s*[\d(]", cand) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", cand):
            continue
        try:
            value = _eval(ast.parse(cand.replace("^", "**"), mode="eval"))
            results.append(f"{cand} = {round(value, 6)}")
        except Exception:
            continue
        if len(results) >= 5:
            break
    return "Calculator results: " + "; ".join(results) if results else "Calculator: no arithmetic expression found."


def summarizer(text):
    sentences = [s for s in re.split(r"(?<=[.!?])\s+|\n+", text.strip()) if s.strip()]
    if len(sentences) <= 3:
        return "Summary: " + " ".join(sentences)
    freq = Counter(w for w in re.findall(r"[a-z]{4,}", text.lower()))
    scored = sorted(range(len(sentences)),
                    key=lambda i: -sum(freq[w] for w in re.findall(r"[a-z]{4,}", sentences[i].lower())))[:3]
    return "Summary: " + " ".join(sentences[i] for i in sorted(scored))


def web_lookup(text):
    q = " ".join(text.split()[:8]) or "the topic"
    return (f"[web-lookup stub - no live internet] Query: '{q}'. Simulated results: "
            f"1) Overview of {q} (encyclopedia). 2) Recent articles about {q}. "
            f"3) Frequently asked questions about {q}.")


def data_lookup(text):
    with open(os.path.join(BASE, "data", "lookup.json"), encoding="utf-8") as f:
        rows = json.load(f)
    words = set(re.findall(r"[a-z]{4,}", text.lower()))
    scored = []
    for r in rows:
        hay = set(re.findall(r"[a-z]{4,}", (r["topic"] + " " + r["fact"] + " " + r["keywords"]).lower()))
        score = len(words & hay)
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return "Data lookup: no matching records."
    return "Data lookup: " + " | ".join(f"{r['topic']}: {r['fact']}" for _, r in scored[:3])


RUNNERS = {"calculator": calculator, "text-summarizer": summarizer,
           "web-lookup": web_lookup, "data-lookup": data_lookup}


def run_tool(tool, text):
    fn = RUNNERS.get(tool["type"])
    if not fn:
        raise ValueError(f"Unknown tool type: {tool['type']}")
    return fn(text)
