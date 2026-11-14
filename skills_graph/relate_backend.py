"""Actual Relate adapter, based on official relate-db 1.0.1 Python documentation.

No database fallback or fabricated graph: absence of relate raises an error.
This adapter must be executed on a machine with relate-db installed.
"""
from __future__ import annotations
from pathlib import Path
from .core import plan, validate, classify_impacts, coverage_proxies


def _relate():
    try:
        import relate
    except ImportError as exc:
        raise RuntimeError("Relate is not installed. Run: python -m pip install relate-db==1.0.1") from exc
    return relate


def seed(conn, data: dict) -> None:
    validate(data)
    # Use parameter binding for data values. Labels and relation types are fixed literals.
    for r in data["resources"]:
        conn.execute("CREATE (:Resource {id: $id, name: $name, capacity: $capacity})", r)
    for s in data["skills"]:
        conn.execute("CREATE (:Skill {id: $id, name: $name})", s)
    for p in data["programs"]:
        conn.execute("CREATE (:Program {id: $id, name: $name, seats: $seats, priority: $priority})",
                     {k: p[k] for k in ("id", "name", "seats", "priority")})
        for rid in p["resources"]:
            conn.execute("""MATCH (p:Program {id: $pid}), (r:Resource {id: $rid})
                         CREATE (p)-[:USES_RESOURCE]->(r)""", {"pid": p["id"], "rid": rid})
        for sid in p["skills"]:
            conn.execute("""MATCH (p:Program {id: $pid}), (s:Skill {id: $sid})
                         CREATE (p)-[:DEVELOPS]->(s)""", {"pid": p["id"], "sid": sid})
    for o in data["occupations"]:
        conn.execute("CREATE (:Occupation {id: $id, name: $name})", {k: o[k] for k in ("id", "name")})
        for sid in o["skills"]:
            conn.execute("""MATCH (o:Occupation {id: $oid}), (s:Skill {id: $sid})
                         CREATE (o)-[:REQUIRES]->(s)""", {"oid": o["id"], "sid": sid})


def read_model(conn, original: dict) -> dict:
    """Constructs all allocation inputs from Cypher queries, NOT the JSON fixture."""
    resources = [{"id": row["id"], "name": row["name"], "capacity": row["capacity"]}
                 for row in conn.execute("MATCH (r:Resource) RETURN r.id AS id, r.name AS name, r.capacity AS capacity ORDER BY id")]
    programs = [{"id": row["id"], "name": row["name"], "seats": row["seats"],
                 "priority": row["priority"], "resources": [], "skills": []}
                for row in conn.execute("MATCH (p:Program) RETURN p.id AS id, p.name AS name, p.seats AS seats, p.priority AS priority ORDER BY id")]
    index = {p["id"]: p for p in programs}
    for row in conn.execute("MATCH (p:Program)-[:USES_RESOURCE]->(r:Resource) RETURN p.id AS pid, r.id AS rid"):
        index[row["pid"]]["resources"].append(row["rid"])
    for row in conn.execute("MATCH (p:Program)-[:DEVELOPS]->(s:Skill) RETURN p.id AS pid, s.id AS sid"):
        index[row["pid"]]["skills"].append(row["sid"])
    skills = [dict(row) for row in conn.execute("MATCH (s:Skill) RETURN s.id AS id, s.name AS name")]
    occupations = [{"id": row["id"], "name": row["name"], "skills": []}
                   for row in conn.execute("MATCH (o:Occupation) RETURN o.id AS id, o.name AS name")]
    jobs = {o["id"]: o for o in occupations}
    for row in conn.execute("MATCH (o:Occupation)-[:REQUIRES]->(s:Skill) RETURN o.id AS oid, s.id AS sid"):
        jobs[row["oid"]]["skills"].append(row["sid"])
    for p in programs:
        p["resources"].sort()
        p["skills"].sort()
    for o in occupations:
        o["skills"].sort()
    resources.sort(key=lambda x: x["id"])
    skills.sort(key=lambda x: x["id"])
    occupations.sort(key=lambda x: x["id"])
    return {"resources": resources, "programs": programs, "skills": skills,
            "occupations": occupations, "scenario": original["scenario"], "metadata": original["metadata"]}


def downstream_paths(conn, resource_id: str) -> list[dict]:
    cypher = """
    MATCH (r:Resource {id: $rid})<-[:USES_RESOURCE]-(p:Program)-[:DEVELOPS]->(s:Skill)<-[:REQUIRES]-(o:Occupation)
    RETURN p.id AS program, s.id AS skill, o.id AS occupation
    ORDER BY program, skill, occupation
    """
    return [dict(row) for row in conn.execute(cypher, {"rid": resource_id})]


def occupation_provider_paths_relate(conn) -> list[dict]:
    """Return occupation requirement -> provider chains from the embedded graph."""
    cypher = """
    MATCH (o:Occupation)-[:REQUIRES]->(s:Skill)<-[:DEVELOPS]-(p:Program)
    RETURN o.id AS occupation, s.id AS skill, p.id AS program
    ORDER BY occupation, skill, program
    """
    return [dict(row) for row in conn.execute(cypher)]

def run_relate(data: dict, store_path: str) -> dict:
    relate = _relate()
    store = Path(store_path)
    if store.exists():
        raise FileExistsError(f"Store already exists, will not overwrite: {store}")
    store.parent.mkdir(parents=True, exist_ok=True)
    scenario = data["scenario"]
    results = []
    with relate.connect(str(store)) as conn:
        seed(conn, data)
        paths = downstream_paths(conn, scenario["resource"])
        role_paths = occupation_provider_paths_relate(conn)
        for cap in (scenario["capacity_a"], scenario["capacity_b"], scenario["capacity_a"]):
            conn.execute("MATCH (r:Resource {id: $rid}) SET r.capacity = $cap",
                         {"rid": scenario["resource"], "cap": cap})
            results.append(plan(read_model(conn, data)))
        # Read requirements and skill providers from the graph itself, while
        # the writer is still open (after restoration to state A).
        graph_model = read_model(conn, data)
    if results[0] != results[2]:
        raise AssertionError("Relate A→B→A restoration failed")
    impacts = classify_impacts(results, paths)
    coverage = coverage_proxies(graph_model, results)
    return {"states": results, "impact_paths": paths, **impacts,
            "occupation_provider_paths": role_paths, **coverage, "restored": True,
            "store_path": str(store), "relate_version": getattr(relate, "__version__", "unknown")}
