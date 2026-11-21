"""Local node-profile application with bounded graph retrieval and cited Qwen answers."""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Literal

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from vckg.final_project.build import OUT
from vckg.final_project.graph_view import options as graph_options
from vckg.final_project.graph_view import overview as graph_overview
from vckg.final_project.graph_view import subgraph as graph_subgraph

STATIC = Path(__file__).parent / "static"
LOGGER = logging.getLogger(__name__)
SOURCE_REF = re.compile(r"\[(\d+)\]")
Mode = Literal["passed", "quarantine"]


def _cites_retrieved_sources(answer: str, source_count: int) -> bool:
    refs = [int(number) for number in SOURCE_REF.findall(answer)]
    return bool(refs) and all(1 <= number <= source_count for number in refs)


def snapshot_dir() -> Path:
    configured = os.environ.get("VCKG_FINAL_SNAPSHOT")
    if configured:
        return Path(configured)
    active = OUT / "ACTIVE.txt"
    if active.exists():
        return Path(active.read_text(encoding="utf-8-sig").strip())
    root = OUT / "complete"
    return root / (root / "LATEST.txt").read_text(encoding="utf-8").strip()


def mode_metrics(mode: Mode) -> dict:
    filename = "metrics.json" if mode == "passed" else "quarantine_metrics.json"
    path = snapshot_dir() / filename
    if not path.exists():
        raise HTTPException(503, f"Chưa có dữ liệu cho chế độ {mode}.")
    return json.loads(path.read_text(encoding="utf-8"))


@contextmanager
def db(mode: Mode = "passed") -> Iterator[sqlite3.Connection]:
    path = snapshot_dir() / ("profile.sqlite" if mode == "passed" else "quarantine.sqlite")
    if not path.exists():
        raise HTTPException(503, "Chưa có snapshot ứng dụng; chạy vckg.final_project.build.")
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def _node(connection: sqlite3.Connection, node_id: str) -> dict:
    row = connection.execute("SELECT * FROM nodes WHERE node_id=?", (node_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Không tìm thấy node trong snapshot đã kiểm định")
    return dict(row)


def _evidence(connection: sqlite3.Connection, edge_uid: str, limit: int = 3,
              mode: Mode = "passed", path_only: bool = False) -> list[dict]:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(evidence)")}
    has_source_status = mode == "quarantine" and "source_factual_statuses" in columns
    extra = (",factual_status,source_factual_statuses,quarantine_classes,"
             "source_edge_uids,status_adjustment") if has_source_status else ""
    allowed = " AND factual_status!='DENIED'" if has_source_status and path_only else ""
    rows = [dict(row) for row in connection.execute(
        "SELECT article_id,source_url,publisher,published_at,evidence_text,extraction_method" + extra
        + " FROM evidence WHERE edge_uid=?" + allowed + " ORDER BY published_at DESC LIMIT 500", (edge_uid,))]
    if has_source_status and path_only:
        rows = [row for row in rows if "DENIED" not in json.loads(row["source_factual_statuses"] or "[]")]
    if not has_source_status:
        return rows[:limit]
    diverse, seen = [], set()
    for row in rows:
        key = (row["factual_status"], row["quarantine_classes"])
        if key not in seen:
            diverse.append(row)
            seen.add(key)
            if len(diverse) == limit:
                return diverse
    return (diverse + [row for row in rows if row not in diverse])[:limit]


def _path_neo4j(snapshot_id: str, start: str, target: str, mode: Mode = "passed") -> tuple[list[str], list[str]] | None:
    try:
        from vckg.graph.neo4j_sync import connect

        node_label, edge_label = ("FEntity", "F_RELATION") if mode == "passed" else ("QEntity", "Q_RELATION")
        quality_clause = "AND r.endpoint_quality='ELIGIBLE'" if mode == "quarantine" else ""
        query = f"""
            MATCH (a:{node_label} {{uid:$start}}), (b:{node_label} {{uid:$target}})
            MATCH p=shortestPath((a)-[:{edge_label}*..3]-(b))
            WHERE all(r IN relationships(p) WHERE r.snapshot_id=$snapshot {quality_clause})
            RETURN [n IN nodes(p) | n.node_id] AS nodes,
                   [r IN relationships(p) | r.edge_uid] AS edges
        """
        with connect() as driver, driver.session() as session:
            record = session.run(query, start=f"{snapshot_id}|{start}", target=f"{snapshot_id}|{target}",
                                 snapshot=snapshot_id).single()
            return (record["nodes"], record["edges"]) if record else None
    except Exception:  # optional Neo4j layer; SQLite keeps the local demo usable
        LOGGER.exception("Neo4j path retrieval failed; using the same immutable SQLite snapshot")
        return None


def _path_sqlite(connection: sqlite3.Connection, start: str, target: str,
                 mode: Mode = "passed") -> tuple[list[str], list[str]] | None:
    if start == target:
        return [start], []
    graph: dict[str, list[tuple[str, str]]] = {}
    query = "SELECT subject_id, object_id, edge_uid FROM edges"
    if mode == "quarantine":
        query += " WHERE endpoint_quality='ELIGIBLE'"
    for row in connection.execute(query):
        graph.setdefault(row["subject_id"], []).append((row["object_id"], row["edge_uid"]))
        graph.setdefault(row["object_id"], []).append((row["subject_id"], row["edge_uid"]))
    queue = deque([(start, [start], [])])
    seen = {start}
    while queue:
        current, nodes, edges = queue.popleft()
        if len(edges) == 3:
            continue
        for neighbor, edge_uid in graph.get(current, []):
            if neighbor in seen:
                continue
            next_nodes, next_edges = [*nodes, neighbor], [*edges, edge_uid]
            if neighbor == target:
                return next_nodes, next_edges
            seen.add(neighbor)
            queue.append((neighbor, next_nodes, next_edges))
    return None


def _path(connection: sqlite3.Connection, start: str, target: str, mode: Mode = "passed") -> dict:
    snapshot_id = mode_metrics(mode)["snapshot_id"]
    linked = None if os.environ.get("VCKG_DISABLE_NEO4J") == "1" else _path_neo4j(snapshot_id, start, target, mode)
    backend = "Neo4j" if linked else "SQLite snapshot"
    linked = linked or _path_sqlite(connection, start, target, mode)
    if linked is None:
        return {"found": False, "hops": None, "nodes": [], "edges": [], "retrieval_backend": backend}
    node_ids, edge_ids = linked
    nodes = [_node(connection, node_id) for node_id in node_ids]
    edges = []
    for uid in edge_ids:
        row = connection.execute("SELECT * FROM edges WHERE edge_uid=?", (uid,)).fetchone()
        if row:
            edges.append({**dict(row), "evidence": _evidence(connection, uid, mode=mode, path_only=True)})
    return {"found": True, "hops": len(edges), "nodes": nodes, "edges": edges, "retrieval_backend": backend}


class AskRequest(BaseModel):
    start_id: str
    target_id: str
    mode: Mode = "passed"
    question: str = Field(min_length=5, max_length=600)


app = FastAPI(title="VCKG · Chân dung node", docs_url="/api/docs")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/style.css")
def style():
    return FileResponse(STATIC / "style.css", media_type="text/css")


@app.get("/app.js")
def javascript():
    return FileResponse(STATIC / "app.js", media_type="text/javascript")


@app.get("/api/health")
def health():
    directory = snapshot_dir()
    return {"ok": (directory / "profile.sqlite").exists(), "snapshot": directory.name,
            "modes": {"passed": (directory / "profile.sqlite").exists(),
                      "quarantine": (directory / "quarantine.sqlite").exists()}}


@app.get("/api/stats")
def stats(mode: Mode = "passed"):
    return mode_metrics(mode)


@app.get("/api/graph/overview")
def graph_overview_api(mode: Mode = "passed", predicates: Annotated[list[str] | None, Query()] = None,
                       types: Annotated[list[str] | None, Query()] = None,
                       min_incident_edges: int = Query(1, ge=0, le=1000)):
    return graph_overview(str(snapshot_dir()), mode, tuple(predicates or ()), tuple(types or ()),
                          min_incident_edges)


@app.get("/api/graph/options")
def graph_options_api(mode: Mode = "passed"):
    return graph_options(str(snapshot_dir()), mode)


@app.get("/api/graph/subgraph")
def graph_subgraph_api(mode: Mode = "passed", scope: Literal["global", "community", "neighborhood"] = "global",
                       node_id: str | None = None, community_id: int | None = None,
                       hops: int = Query(1, ge=1, le=3), max_nodes: int = Query(300, ge=1, le=100000),
                       max_edges: int = Query(700, ge=0, le=200000),
                       min_incident_edges: int = Query(1, ge=0, le=1000),
                       predicates: Annotated[list[str] | None, Query()] = None,
                       types: Annotated[list[str] | None, Query()] = None):
    try:
        return graph_subgraph(str(snapshot_dir()), mode, scope, max_nodes, max_edges, min_incident_edges,
                              tuple(predicates or ()), tuple(types or ()), node_id, community_id, hops)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except KeyError as error:
        raise HTTPException(404, f"Không tìm thấy node {error.args[0]}") from error


@app.get("/api/graph/edge/{edge_uid:path}")
def graph_edge_api(edge_uid: str, mode: Mode = "passed", offset: int = Query(0, ge=0),
                   limit: int = Query(20, ge=1, le=100)):
    with db(mode) as connection:
        edge = connection.execute("""SELECT e.*, s.name AS subject_name, o.name AS object_name
            FROM edges e JOIN nodes s ON s.node_id=e.subject_id JOIN nodes o ON o.node_id=e.object_id
            WHERE e.edge_uid=?""", (edge_uid,)).fetchone()
        if edge is None:
            raise HTTPException(404, "Không tìm thấy cạnh trong snapshot")
        evidence = [dict(row) for row in connection.execute(
            "SELECT * FROM evidence WHERE edge_uid=? ORDER BY published_at DESC,article_id LIMIT ? OFFSET ?",
            (edge_uid, limit, offset))]
        return {"mode": mode, "edge": dict(edge), "evidence": evidence,
                "offset": offset, "limit": limit, "total": edge["evidence_count"]}


@app.get("/api/graph/review/{node_id:path}")
def graph_review_api(node_id: str, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    """Keep excluded candidate relations reviewable without drawing them as graph edges."""
    with db("quarantine") as connection:
        _node(connection, node_id)
        where = "(e.subject_id=? OR e.object_id=?) AND e.endpoint_quality!='ELIGIBLE'"
        total = connection.execute(f"SELECT count(*) FROM edges e WHERE {where}", (node_id, node_id)).fetchone()[0]
        rows = connection.execute(f"""SELECT e.edge_uid,e.predicate,e.factual_status,e.endpoint_quality,
            e.article_count,e.evidence_count,s.name AS subject_name,o.name AS object_name
            FROM edges e JOIN nodes s ON s.node_id=e.subject_id JOIN nodes o ON o.node_id=e.object_id
            WHERE {where} ORDER BY e.article_count DESC,e.evidence_count DESC,e.edge_uid LIMIT ? OFFSET ?""",
                                  (node_id, node_id, limit, offset)).fetchall()
        return {"node_id": node_id, "total": total, "offset": offset,
                "relations": [dict(row) for row in rows]}


@app.get("/api/search")
def search(q: str = Query(min_length=2, max_length=100), limit: int = Query(20, ge=1, le=50),
           mode: Mode = "passed"):
    with db(mode) as connection:
        quality = ",endpoint_quality" if mode == "quarantine" else ""
        rows = connection.execute(f"""
            SELECT node_id,name,entity_type,degree,pagerank,community,core_number{quality} FROM nodes
            WHERE name LIKE ? OR aliases LIKE ? ORDER BY degree DESC, pagerank DESC LIMIT ?
        """, (f"%{q}%", f"%{q}%", limit)).fetchall()
        return [dict(row) for row in rows]


@app.get("/api/top")
def top(limit: int = Query(15, ge=1, le=50), mode: Mode = "passed"):
    with db(mode) as connection:
        where = "WHERE endpoint_quality='ELIGIBLE' AND degree>0" if mode == "quarantine" else ""
        return [dict(row) for row in connection.execute(
            f"SELECT node_id,name,entity_type,degree,pagerank,community,core_number FROM nodes {where} "
            "ORDER BY pagerank DESC LIMIT ?", (limit,))]


@app.get("/api/profile/{node_id:path}")
def profile(node_id: str, limit: int = Query(80, ge=1, le=200), mode: Mode = "passed"):
    with db(mode) as connection:
        node = _node(connection, node_id)
        rows = connection.execute("""
            SELECT e.*,s.name AS subject_name,o.name AS object_name,
                   s.entity_type AS subject_type,o.entity_type AS object_type
            FROM edges e JOIN nodes s ON e.subject_id=s.node_id JOIN nodes o ON e.object_id=o.node_id
            WHERE e.subject_id=? OR e.object_id=?
            ORDER BY e.article_count DESC,e.evidence_count DESC LIMIT ?
        """, (node_id, node_id, limit)).fetchall()
        relations = [{**dict(row), "evidence": _evidence(connection, row["edge_uid"], 6, mode)} for row in rows]
        total = connection.execute("SELECT count(*) FROM edges WHERE subject_id=? OR object_id=?",
                                   (node_id, node_id)).fetchone()[0]
        return {"mode": mode, "node": node, "relations": relations,
                "shown": len(relations), "total": total}


@app.get("/api/path")
def path(start_id: str, target_id: str, mode: Mode = "passed"):
    with db(mode) as connection:
        _node(connection, start_id)
        _node(connection, target_id)
        return _path(connection, start_id, target_id, mode)


@app.post("/api/ask")
def ask(request: AskRequest):
    with db(request.mode) as connection:
        _node(connection, request.start_id)
        _node(connection, request.target_id)
        graph_path = _path(connection, request.start_id, request.target_id, request.mode)
        if not graph_path["found"] or not graph_path["edges"]:
            return {"answer": "Chưa tìm thấy đường liên hệ có bằng chứng trong tối đa 3 bước.", "path": graph_path,
                    "sources": [], "model_used": False}
        sources, facts = [], []
        for index, edge in enumerate(graph_path["edges"], 1):
            subject = next(n["name"] for n in graph_path["nodes"] if n["node_id"] == edge["subject_id"])
            object_ = next(n["name"] for n in graph_path["nodes"] if n["node_id"] == edge["object_id"])
            evidence = edge["evidence"][:2]
            if not evidence:
                continue
            facts.append(f"[{index}] {subject} --{edge['predicate']}--> {object_}; trạng thái {edge['factual_status']}; "
                         + " | ".join(item["evidence_text"][:650] for item in evidence))
            sources.append({"number": index, "edge_uid": edge["edge_uid"], "subject": subject,
                            "predicate": edge["predicate"], "object": object_, "evidence": evidence})
        if not facts:
            return {"answer": "Đường đi chưa có đoạn chứng cứ để trả lời.", "path": graph_path,
                    "sources": [], "model_used": False}
        if request.mode == "quarantine":
            route = " → ".join(node["name"] for node in graph_path["nodes"])
            statuses = ", ".join(dict.fromkeys(edge["factual_status"] for edge in graph_path["edges"]))
            return {"answer": f"Đường ứng viên QUARANTINE ({graph_path['hops']} bước): {route}. "
                              f"Trạng thái được ghi: {statuses}. Các quan hệ và danh tính trên đường này "
                              "chưa qua kiểm định để dùng như sự kiện đã xác nhận; hãy mở bài báo và lý do giữ lại ở từng cạnh.",
                    "path": graph_path, "sources": sources, "model_used": False,
                    "warning": "QUARANTINE: ứng viên chưa được xác nhận"}
        start_name, target_name = graph_path["nodes"][0]["name"], graph_path["nodes"][-1]["name"]
        prompt = (f"Cặp được hỏi là A = {start_name}; B = {target_name}. "
                  f"Đường truy xuất giữa A và B có đúng {graph_path['hops']} cạnh. "
                  "Trả lời bằng tiếng Việt, chỉ dựa vào các cạnh và trích dẫn báo dưới đây. "
                  "Nói rõ đây là liên hệ trên đồ thị, không khẳng định quan hệ trực tiếp nếu nhiều bước. "
                  "Nếu chỉ một bước, mô tả đúng chủ thể, loại quan hệ và đối tượng của cạnh đó; "
                  "không tự thêm nút trung gian, đổi vai A/B hoặc sửa tên node được cung cấp. "
                  "Gắn số nguồn [1], [2], [3] cho từng mệnh đề. Nếu chứng cứ không đủ, nói không đủ.\n"
                  f"Câu hỏi: {request.question}\nDữ kiện:\n" + "\n".join(facts))
        if os.environ.get("VCKG_DISABLE_OLLAMA") == "1":
            route = " → ".join(n["name"] for n in graph_path["nodes"])
            return {"answer": f"Đường liên hệ {graph_path['hops']} bước: {route}. "
                              f"Xem chứng cứ [1]–[{len(sources)}].",
                    "path": graph_path, "sources": sources, "model_used": False}
        try:
            response = httpx.post(os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434") + "/api/chat",
                                  json={"model": "qwen3.5:9b", "stream": False, "think": False,
                                        "messages": [{"role": "user", "content": prompt}],
                                        "options": {"temperature": 0, "num_predict": 350}}, timeout=90)
            response.raise_for_status()
            answer = response.json()["message"]["content"].strip()
            if not _cites_retrieved_sources(answer, len(sources)):
                raise ValueError("Qwen answer omitted or invented a source number")
            return {"answer": answer, "path": graph_path, "sources": sources, "model_used": True}
        except (httpx.HTTPError, KeyError, ValueError):
            answer = " → ".join(n["name"] for n in graph_path["nodes"])
            return {"answer": f"Đường liên hệ {graph_path['hops']} bước: {answer}. Xem chứng cứ [1]–[{len(sources)}].",
                    "path": graph_path, "sources": sources, "model_used": False}
