"""UI presentation model. Counts are opportunity proxies, NOT trained workers.

Pure helpers tested without Relate; the web app always supplies graph data via
Cypher queries (read_model, downstream_paths, occupation_provider_paths_relate).
"""
from __future__ import annotations

from .core import classify_impacts, coverage_proxies, plan, set_capacity, validate


def graph_payload(graph_model: dict, affected_programs: set[str], changed_skills: set[str], changed_roles: set[str]) -> dict:
    validate(graph_model)
    nodes, edges = [], set()
    for kind, collection in (
        ("Resource", "resources"), ("Program", "programs"),
        ("Skill", "skills"), ("Occupation", "occupations"),
    ):
        for obj in graph_model[collection]:
            oid = obj["id"]
            affected = (
                oid in affected_programs if kind == "Program" else
                oid in changed_skills if kind == "Skill" else
                oid in changed_roles if kind == "Occupation" else False
            )
            nodes.append({"id": oid, "label": obj["name"], "kind": kind, "affected": affected})
    for p in graph_model["programs"]:
        for rid in p["resources"]:
            edges.add((rid, p["id"], "USES_RESOURCE"))
        for sid in p["skills"]:
            edges.add((p["id"], sid, "DEVELOPS"))
    for o in graph_model["occupations"]:
        for sid in o["skills"]:
            edges.add((sid, o["id"], "REQUIRES"))
    return {"nodes": sorted(nodes,key=lambda n:(n["kind"],n["id"])),
            "edges": [{"from": a, "to": b, "type": t} for a,b,t in sorted(edges)]}


def explain(visible_graph: dict, worlds: list[dict], structural_paths: list[dict], provider_paths: list[dict], *, capacity_a: int, capacity_b: int) -> dict:
    """Calculate explanations after caller queried real graph and evaluated A/B/A."""
    if len(worlds) != 3 or worlds[0] != worlds[2]:
        raise AssertionError("A→B→A restoration not proven")
    impact = classify_impacts(worlds, structural_paths)
    coverage = coverage_proxies(visible_graph, worlds)
    changed_programs = {d["program"] for d in impact["program_deltas"]}
    changed_skills = {d["skill"] for d in coverage["skill_seat_opportunities"] if d["delta_b_minus_a"]}
    changed_roles = set(coverage["occupations_with_proxy_delta"])
    graph = graph_payload(visible_graph, changed_programs, changed_skills, changed_roles)
    return {
        "data_kind": "SYNTHETIC_ONLY",
        "status": "DERIVED_FROM_RELATE_GRAPH",
        "capacity_a": capacity_a,
        "capacity_b": capacity_b,
        "planned": worlds[0]["planned_total"],
        "feasible_a": worlds[0]["feasible_total"],
        "feasible_b": worlds[1]["feasible_total"],
        "feasible_restored": worlds[2]["feasible_total"],
        "restored": worlds[0] == worlds[2],
        "programs": [
            {"id": pid, "name": next(x["name"] for x in visible_graph["programs"] if x["id"] == pid),
             "planned": value["planned"], "a": value["feasible"],
             "b": worlds[1]["programs"][pid]["feasible"],
             "delta": worlds[1]["programs"][pid]["feasible"]-value["feasible"]}
            for pid,value in sorted(worlds[0]["programs"].items())
        ],
        "changed_programs": sorted(changed_programs),
        "structural_paths": structural_paths,
        "affected_paths": impact["affected_paths"],
        "occupation_provider_paths": provider_paths,
        "occupation_proxies": coverage["occupation_bottleneck_proxies"],
        "skill_opportunities": coverage["skill_seat_opportunities"],
        "changed_roles": sorted(changed_roles),
        "graph": graph,
        "claim": coverage["coverage_claim"],
        "method": "fixed_priority_greedy_not_optimal",
    }


def compare_baseline(original:dict, capacity_b:int, relate_ui:dict) -> bool:
    """Independent JSON-join baseline; fail closed on any mismatch."""
    from .core import evaluate_baseline
    from copy import deepcopy
    candidate=deepcopy(original)
    candidate["scenario"]["capacity_b"]=capacity_b
    baseline=evaluate_baseline(candidate)
    if baseline["states"][0]["feasible_total"]!=relate_ui["feasible_a"]:
        return False
    if baseline["states"][1]["feasible_total"]!=relate_ui["feasible_b"]:
        return False
    if baseline["states"][2]["feasible_total"]!=relate_ui["feasible_restored"]:
        return False
    expected_programs={x["program"]:x["delta_b_minus_a"] for x in baseline["program_deltas"]}
    actual_programs={x["id"]:x["delta"] for x in relate_ui["programs"] if x["delta"]}
    if expected_programs != actual_programs:
        return False
    if baseline["impact_paths"] != relate_ui["structural_paths"]:
        return False
    if baseline["affected_paths"] != relate_ui["affected_paths"]:
        return False
    if baseline["occupation_provider_paths"] != relate_ui["occupation_provider_paths"]:
        return False
    if baseline["occupation_bottleneck_proxies"] != relate_ui["occupation_proxies"]:
        return False
    if baseline["skill_seat_opportunities"] != relate_ui["skill_opportunities"]:
        return False
    if baseline["occupations_with_proxy_delta"] != relate_ui["changed_roles"]:
        return False
    return True
