import time
from collections import defaultdict, deque

import ai
import store
import tools as toolbox

# Rough USD per 1,000 tokens. These are estimates for comparison, not real billing.
RATES = {"grok-3-mini": 0.0004, "grok-3": 0.006, "grok-4": 0.009, "default": 0.004}


def est_tokens(text):
    return max(1, len(text or "") // 4)


def order(wf):
    ids = [n["id"] for n in wf["nodes"]]
    indeg = {i: 0 for i in ids}
    out = defaultdict(list)
    for e in wf["edges"]:
        if e["from"] in indeg and e["to"] in indeg:
            out[e["from"]].append(e["to"])
            indeg[e["to"]] += 1
    queue = deque(i for i in ids if indeg[i] == 0)
    seq = []
    while queue:
        i = queue.popleft()
        seq.append(i)
        for j in out[i]:
            indeg[j] -= 1
            if indeg[j] == 0:
                queue.append(j)
    return seq, [i for i in ids if i not in seq]


def execute(wf, user_input, strategy=None, label="Standard"):
    strategy = strategy or {}
    agents = {a["id"]: a for a in store.load("agents")}
    tool_map = {t["id"]: t for t in store.load("tools")}
    nodes = {n["id"]: n for n in wf["nodes"]}
    preds = defaultdict(list)
    for e in wf["edges"]:
        if e["from"] in nodes and e["to"] in nodes:
            preds[e["to"]].append(e["from"])

    start = store.now()
    t_run = time.perf_counter()
    seq, cyclic = order(wf)
    outputs, steps = {}, []

    for nid in seq:
        agent = agents.get(nodes[nid]["agent_id"])
        inp = "\n\n".join(outputs.get(p, "") for p in preds[nid] if outputs.get(p)) if preds[nid] else user_input
        t0 = time.perf_counter()
        out, errors = "", []
        model = (strategy.get("model") or (agent or {}).get("model") or "default")
        prompt = ""
        try:
            if not agent:
                raise ValueError("Agent no longer exists")
            tool_results = []
            for tid in agent.get("tools", []):
                tool = tool_map.get(tid)
                if not tool:
                    errors.append(f"Tool {tid} not found")
                    continue
                try:
                    tool_results.append(f"[{tool['name']}] {toolbox.run_tool(tool, inp)}")
                except Exception as e:
                    errors.append(f"Tool {tool['name']} failed: {e}")
            instr = agent["instructions"]
            if strategy.get("extra"):
                instr += "\nAdditional strategy instructions: " + strategy["extra"]
            prompt = f"Role: {agent['role']}\nGoal: {agent['goal']}\nInstructions: {instr}\n"
            if tool_results:
                prompt += "Tool results:\n" + "\n".join(tool_results) + "\n"
            prompt += "INPUT:\n" + inp
            out = ai.ask_ai(prompt, model)
        except Exception as e:
            errors.append(f"{type(e).__name__}: {e}")
        outputs[nid] = out
        tokens = est_tokens(prompt) + est_tokens(out) if out else est_tokens(inp)
        cost = tokens / 1000 * RATES.get(model, RATES["default"])
        steps.append({"node_id": nid, "agent": agent["name"] if agent else "(deleted agent)",
                      "role": agent["role"] if agent else "Missing", "model": model,
                      "input": inp, "output": out,
                      "duration": round(time.perf_counter() - t0, 3),
                      "tokens": tokens, "cost": round(cost, 6),
                      "error": "; ".join(errors) or None})

    for nid in cyclic:
        agent = agents.get(nodes[nid]["agent_id"])
        steps.append({"node_id": nid, "agent": agent["name"] if agent else "(deleted agent)",
                      "role": agent["role"] if agent else "Missing", "model": "-",
                      "input": "", "output": "", "duration": 0, "tokens": 0, "cost": 0,
                      "error": "Skipped: node is part of a connection loop"})

    run = {"id": store.uid("r_"), "workflow_id": wf["id"], "label": label, "input": user_input,
           "start": start, "end": store.now(),
           "status": "failed" if any(s["error"] for s in steps) else "completed",
           "duration": round(time.perf_counter() - t_run, 3),
           "tokens": sum(s["tokens"] for s in steps),
           "cost": round(sum(s["cost"] for s in steps), 6),
           "steps": steps, "output": next((s["output"] for s in reversed(steps) if s["output"]), "")}
    runs = store.load("runs")
    runs.append(run)
    store.save("runs", runs)
    return run
