"""Test thủ công cho src/graph.py — chạy toàn bộ pipeline LangGraph
(Fetch -> Orchestrator -> 4 agent -> Aggregator -> Write-back) trên
instance Drupal local thật.

Cách chạy:
    .venv\\Scripts\\python.exe scripts\\smoke_test_graph.py <node_id>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from graph import build_graph

if __name__ == "__main__":
    node_id = sys.argv[1] if len(sys.argv) > 1 else "67859e3c-ccf8-45d5-b4e3-9ee68e0895fa"

    app = build_graph()
    result = app.invoke({"node_id": node_id})

    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
