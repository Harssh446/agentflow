import csv
import io
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from flask import (Flask, Response, abort, flash, jsonify, redirect,
                   render_template, request, url_for)

import runner
import seed
import store

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")
seed.init()
app.jinja_env.filters["hue"] = lambda s: sum(ord(c) for c in (s or "")) % 360


def wf_names():
    return {w["id"]: w["name"] for w in store.load("workflows")}


# ---------- Dashboard ----------
@app.route("/")
def dashboard():
    runs = store.load("runs")
    failed = sum(1 for r in runs if r["status"] != "completed")
    days = [datetime.now().date() - timedelta(days=i) for i in range(6, -1, -1)]
    chart = {"labels": [d.strftime("%d %b") for d in days],
             "values": [sum(1 for r in runs if r["start"][:10] == d.isoformat()) for d in days]}
    stats = {"agents": len(store.load("agents")), "workflows": len(store.load("workflows")),
             "runs": len(runs), "cost": round(sum(r["cost"] for r in runs), 4),
             "error_rate": round(100 * failed / len(runs), 1) if runs else 0}
    recent = sorted(runs, key=lambda r: r["start"], reverse=True)[:6]
    return render_template("dashboard.html", stats=stats, chart=chart, recent=recent, wf=wf_names())


# ---------- Agents ----------
@app.route("/agents")
def agents():
    items = store.load("agents")
    tools_all = store.load("tools")
    edit = store.get("agents", request.args.get("edit", ""))
    return render_template("agents.html", agents=items, tools=tools_all, edit=edit,
                           models=seed.MODELS, tool_names={t["id"]: t["name"] for t in tools_all})


@app.post("/agents/save")
def agent_save():
    f = request.form
    name = f.get("name", "").strip()
    if not name:
        flash("Agent name is required.", "error")
        return redirect(url_for("agents"))
    data = {"name": name, "role": f.get("role", "").strip() or "Agent",
            "goal": f.get("goal", "").strip(), "instructions": f.get("instructions", "").strip(),
            "tools": f.getlist("tools"), "model": f.get("model", "default")}
    items = store.load("agents")
    existing = next((a for a in items if a["id"] == f.get("id")), None)
    if existing:
        existing.update(data)
        flash("Agent updated.", "ok")
    else:
        data.update(id=store.uid("a_"), created=store.now())
        items.append(data)
        flash("Agent created.", "ok")
    store.save("agents", items)
    return redirect(url_for("agents"))


@app.post("/agents/<aid>/delete")
def agent_delete(aid):
    store.save("agents", [a for a in store.load("agents") if a["id"] != aid])
    wfs = store.load("workflows")
    for w in wfs:
        gone = {n["id"] for n in w["nodes"] if n["agent_id"] == aid}
        w["nodes"] = [n for n in w["nodes"] if n["id"] not in gone]
        w["edges"] = [e for e in w["edges"] if e["from"] not in gone and e["to"] not in gone]
    store.save("workflows", wfs)
    flash("Agent deleted (and removed from workflows).", "ok")
    return redirect(url_for("agents"))


# ---------- Tools ----------
@app.route("/tools")
def tools_page():
    return render_template("tools.html", tools=store.load("tools"), types=seed.TOOL_TYPES)


@app.post("/tools/save")
def tool_save():
    f = request.form
    name, ttype = f.get("name", "").strip(), f.get("type", "")
    if not name or ttype not in seed.TOOL_TYPES:
        flash("Tool needs a name and a valid type.", "error")
        return redirect(url_for("tools_page"))
    items = store.load("tools")
    items.append({"id": store.uid("t_"), "name": name, "type": ttype,
                  "description": f.get("description", "").strip()})
    store.save("tools", items)
    flash("Tool created.", "ok")
    return redirect(url_for("tools_page"))


@app.post("/tools/<tid>/delete")
def tool_delete(tid):
    store.save("tools", [t for t in store.load("tools") if t["id"] != tid])
    items = store.load("agents")
    for a in items:
        a["tools"] = [t for t in a.get("tools", []) if t != tid]
    store.save("agents", items)
    flash("Tool deleted.", "ok")
    return redirect(url_for("tools_page"))


# ---------- Workflows ----------
@app.route("/workflows")
def workflows():
    return render_template("workflows.html", workflows=store.load("workflows"))


@app.post("/workflows/new")
def workflow_new():
    name = request.form.get("name", "").strip() or "Untitled workflow"
    wf = {"id": store.uid("w_"), "name": name, "nodes": [], "edges": [], "created": store.now()}
    items = store.load("workflows")
    items.append(wf)
    store.save("workflows", items)
    return redirect(url_for("editor", wid=wf["id"]))


@app.post("/workflows/<wid>/delete")
def workflow_delete(wid):
    store.save("workflows", [w for w in store.load("workflows") if w["id"] != wid])
    flash("Workflow deleted.", "ok")
    return redirect(url_for("workflows"))


@app.route("/workflows/<wid>/editor")
def editor(wid):
    wf = store.get("workflows", wid) or abort(404)
    return render_template("editor.html", wf=wf, agents=store.load("agents"))


@app.post("/api/workflows/<wid>")
def api_wf_save(wid):
    d = request.get_json(force=True, silent=True) or {}
    items = store.load("workflows")
    wf = next((w for w in items if w["id"] == wid), None)
    if not wf:
        return jsonify(error="Workflow not found"), 404
    nodes = []
    for n in d.get("nodes", []):
        try:
            nodes.append({"id": str(n["id"]), "agent_id": str(n["agent_id"]),
                          "x": round(float(n["x"])), "y": round(float(n["y"]))})
        except (KeyError, ValueError, TypeError):
            continue
    ids = {n["id"] for n in nodes}
    edges = [{"from": str(e["from"]), "to": str(e["to"])} for e in d.get("edges", [])
             if isinstance(e, dict) and str(e.get("from")) in ids and str(e.get("to")) in ids
             and e.get("from") != e.get("to")]
    wf["nodes"], wf["edges"] = nodes, edges
    if str(d.get("name", "")).strip():
        wf["name"] = str(d["name"]).strip()
    store.save("workflows", items)
    return jsonify(ok=True, nodes=len(nodes), edges=len(edges))


@app.post("/workflows/<wid>/run")
def wf_run(wid):
    wf = store.get("workflows", wid) or abort(404)
    if not wf["nodes"]:
        flash("This workflow has no agents yet. Add some in the editor first.", "error")
        return redirect(url_for("editor", wid=wid))
    run = runner.execute(wf, request.form.get("input", "").strip() or "Give an overview of the topic.")
    flash(f"Run {run['status']}.", "ok" if run["status"] == "completed" else "error")
    return redirect(url_for("logs", open=run["id"]))


# ---------- Logs ----------
def filtered_runs():
    runs = sorted(store.load("runs"), key=lambda r: r["start"], reverse=True)
    status = request.args.get("status", "")
    wid = request.args.get("workflow_id", "")
    q = request.args.get("q", "").strip().lower()
    if status:
        runs = [r for r in runs if r["status"] == status]
    if wid:
        runs = [r for r in runs if r["workflow_id"] == wid]
    if q:
        runs = [r for r in runs if q in r["label"].lower() or q in r["input"].lower()]
    return runs


@app.route("/logs")
def logs():
    return render_template("logs.html", runs=filtered_runs(), wf=wf_names(),
                           workflows=store.load("workflows"), open_id=request.args.get("open", ""),
                           csv_url=url_for("logs_csv", **request.args.to_dict()))


@app.route("/logs/export.csv")
def logs_csv():
    wf = wf_names()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["run_id", "workflow", "label", "status", "start", "end", "duration_s", "total_tokens",
                "cost_usd", "step", "agent", "step_input", "step_output", "step_duration_s",
                "step_tokens", "step_cost_usd", "step_error"])
    for r in filtered_runs():
        for i, s in enumerate(r["steps"] or [None], 1):
            base = [r["id"], wf.get(r["workflow_id"], "(deleted)"), r["label"], r["status"],
                    r["start"], r["end"], r["duration"], r["tokens"], r["cost"]]
            if s:
                w.writerow(base + [i, s["agent"], s["input"], s["output"], s["duration"],
                                   s["tokens"], s["cost"], s["error"] or ""])
            else:
                w.writerow(base + [""] * 8)
    return Response("\ufeff" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=agentflow_runs.csv"})


# ---------- Compare ----------
@app.route("/compare", methods=["GET", "POST"])
def compare():
    wfs = store.load("workflows")
    results, chart, form = None, None, request.form
    if request.method == "POST":
        wf = store.get("workflows", form.get("workflow_id", ""))
        if not wf or not wf["nodes"]:
            flash("Pick a workflow that contains at least one agent.", "error")
        else:
            text = form.get("input", "").strip() or "Give an overview of the topic."
            results = []
            for s in "ab":
                strat = {"model": form.get(f"model_{s}") or None, "extra": form.get(f"extra_{s}", "").strip()}
                label = form.get(f"label_{s}", "").strip() or f"Strategy {s.upper()}"
                results.append(runner.execute(wf, text, strat, label))
            labels = [r["label"] for r in results]
            chart = {"time": {"labels": labels, "values": [r["duration"] for r in results]},
                     "cost": {"labels": labels, "values": [r["cost"] for r in results]},
                     "tokens": {"labels": labels, "values": [r["tokens"] for r in results]}}
    return render_template("compare.html", workflows=wfs, models=seed.MODELS[1:],
                           results=results, chart=chart, form=form)


# ---------- Templates ----------
@app.route("/templates")
def template_library():
    cat = request.args.get("category", "")
    names = {a["id"]: a["name"] for a in store.load("agents")}
    items = []
    for t in store.load("templates"):
        if cat and t["category"] != cat:
            continue
        items.append(dict(t, steps=[names.get(n["agent_id"], "?") for n in t["workflow"]["nodes"]]))
    return render_template("templates.html", templates=items, categories=seed.CATEGORIES, cat=cat)


@app.post("/templates/<tid>/use")
def template_use(tid):
    t = store.get("templates", tid) or abort(404)
    agent_ids = {a["id"] for a in store.load("agents")}
    nodes = [dict(n) for n in t["workflow"]["nodes"] if n["agent_id"] in agent_ids]
    keep = {n["id"] for n in nodes}
    edges = [dict(e) for e in t["workflow"]["edges"] if e["from"] in keep and e["to"] in keep]
    wf = {"id": store.uid("w_"), "name": t["name"] + " (copy)", "nodes": nodes,
          "edges": edges, "created": store.now()}
    items = store.load("workflows")
    items.append(wf)
    store.save("workflows", items)
    flash("Template copied to your workflows.", "ok")
    return redirect(url_for("editor", wid=wf["id"]))


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "5000")))
