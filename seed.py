import json
import os

import store

MODELS = ["default", "grok-3-mini", "grok-3", "grok-4"]
TOOL_TYPES = ["calculator", "text-summarizer", "web-lookup", "data-lookup"]
CATEGORIES = ["Research", "Coding", "Data analysis", "Business automation"]

TOOLS = [
    {"id": "t_calc", "name": "Calculator",
     "description": "Evaluates arithmetic expressions found in the input text.",
     "type": "calculator"},
    {"id": "t_summary", "name": "Text Summarizer",
     "description": "Extracts the three most important sentences from the input.",
     "type": "text-summarizer"},
    {"id": "t_data", "name": "Knowledge Lookup",
     "description": "Searches the local data/lookup.json knowledge file.",
     "type": "data-lookup"},
]

AGENTS = [
    {"id": "a_researcher", "name": "Research Analyst", "role": "Researcher",
     "goal": "Collect accurate key facts about the topic",
     "instructions": "Gather 5 concise key facts. Use tool results when helpful. Output a bullet list.",
     "tools": ["t_data"], "model": "grok-3-mini"},
    {"id": "a_writer", "name": "Report Writer", "role": "Writer",
     "goal": "Turn findings into a clear, short report",
     "instructions": "Write a structured report of under 200 words from the input. Use a title and short sections.",
     "tools": ["t_summary"], "model": "grok-3-mini"},
    {"id": "a_coder", "name": "Code Assistant", "role": "Coder",
     "goal": "Produce clean, working Python code",
     "instructions": "Write Python code for the task with brief comments and one usage example. Add a 2-line explanation.",
     "tools": [], "model": "grok-3-mini"},
    {"id": "a_analyst", "name": "Data Analyst", "role": "Analyst",
     "goal": "Extract numbers and insights from the input",
     "instructions": "Identify numbers, trends and calculations. List 3 insights and one recommendation.",
     "tools": ["t_calc", "t_data"], "model": "grok-3-mini"},
]


def _chain(name, agent_ids):
    nodes = [{"id": f"n{i + 1}", "agent_id": a, "x": 40 + i * 250, "y": 90 + (i % 2) * 80}
             for i, a in enumerate(agent_ids)]
    edges = [{"from": f"n{i + 1}", "to": f"n{i + 2}"} for i in range(len(agent_ids) - 1)]
    return {"name": name, "nodes": nodes, "edges": edges}


TEMPLATES = [
    {"id": "tpl_research", "name": "Research Brief", "category": "Research",
     "description": "Research a topic, then write a short report.",
     "workflow": _chain("Research Brief", ["a_researcher", "a_writer"])},
    {"id": "tpl_coding", "name": "Code and Document", "category": "Coding",
     "description": "Generate code for a task, then document it.",
     "workflow": _chain("Code and Document", ["a_coder", "a_writer"])},
    {"id": "tpl_data", "name": "Data Insight Pipeline", "category": "Data analysis",
     "description": "Gather facts, analyse the numbers, and report insights.",
     "workflow": _chain("Data Insight Pipeline", ["a_researcher", "a_analyst", "a_writer"])},
    {"id": "tpl_business", "name": "Business Report Automation", "category": "Business automation",
     "description": "Analyse business data and produce a ready-to-send report.",
     "workflow": _chain("Business Report Automation", ["a_analyst", "a_writer"])},
]

LOOKUP = [
    {"topic": "Solar energy", "fact": "Solar panels typically convert 15-22% of sunlight into electricity, and costs fell about 90% in the last decade.", "keywords": "solar energy panels renewable electricity"},
    {"topic": "Electric vehicles", "fact": "Battery packs account for roughly 30-40% of an electric vehicle's cost; typical range is 250-400 miles.", "keywords": "electric vehicles ev battery car range"},
    {"topic": "Machine learning", "fact": "Machine learning models learn patterns from data; common types are supervised, unsupervised and reinforcement learning.", "keywords": "machine learning model training data ai"},
    {"topic": "Inflation", "fact": "Inflation measures how fast prices rise; central banks often target about 2% per year.", "keywords": "inflation prices economy interest rates"},
    {"topic": "Customer churn", "fact": "Churn rate is customers lost divided by customers at the start of the period; 5% monthly churn loses about 46% of customers per year.", "keywords": "customer churn retention subscription business"},
    {"topic": "Cloud computing", "fact": "Cloud computing rents servers and services on demand; main models are IaaS, PaaS and SaaS.", "keywords": "cloud computing servers saas infrastructure"},
    {"topic": "Remote work", "fact": "Surveys show hybrid work is the most common arrangement for knowledge workers; commute savings average about 1 hour per day.", "keywords": "remote work hybrid productivity office"},
    {"topic": "Python", "fact": "Python is a high-level language known for readable syntax; popular for web, data science and automation.", "keywords": "python programming code language script"},
    {"topic": "Climate change", "fact": "Global average temperature has risen about 1.1 C since the late 1800s, mainly due to greenhouse gas emissions.", "keywords": "climate change warming emissions carbon"},
]


def _ensure(name, data):
    p = store.path(name)
    if not os.path.exists(p) or os.path.getsize(p) == 0:
        store.save(name, data)


def init():
    os.makedirs(store.DATA, exist_ok=True)
    stamp = store.now()
    _ensure("agents", [dict(a, created=stamp) for a in AGENTS])
    _ensure("tools", TOOLS)
    _ensure("templates", TEMPLATES)
    _ensure("workflows", [])
    _ensure("runs", [])
    _ensure("lookup", LOOKUP)
