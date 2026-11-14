"""Deterministic fixed-priority seat planner; deliberately NOT an AI or optimizer."""
from __future__ import annotations
import json
from pathlib import Path
from copy import deepcopy


def load_data(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate(data)
    return data


def validate(data: dict) -> None:
    def unique(kind: str) -> set[str]:
        ids = [x["id"] for x in data[kind]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate identifiers in {kind}")
        return set(ids)
    resources = unique("resources")
    programs = unique("programs")
    skills = unique("skills")
    unique("occupations")
    if not programs:
        raise ValueError("no programs")
    for r in data["resources"]:
        if not isinstance(r["capacity"], int) or r["capacity"] < 0:
            raise ValueError(f"unknown/invalid capacity for {r['id']}; do not guess")
    for p in data["programs"]:
        if not isinstance(p["seats"], int) or p["seats"] < 0 or not isinstance(p["priority"], int):
            raise ValueError(f"invalid seat or priority in {p['id']}")
        if not p["resources"] or any(x not in resources for x in p["resources"]):
            raise ValueError(f"unknown/missing resource in {p['id']}")
        if any(x not in skills for x in p["skills"]):
            raise ValueError(f"unknown skill in {p['id']}")
    for o in data["occupations"]:
        if any(x not in skills for x in o["skills"]):
            raise ValueError(f"unknown skill in occupation {o['id']}")
    sc = data["scenario"]
    if sc["resource"] not in resources:
        raise ValueError("scenario resource unknown")
    for k in ("capacity_a", "capacity_b"):
        if not isinstance(sc[k], int) or sc[k] < 0:
            raise ValueError("invalid scenario capacity")


def set_capacity(data: dict, resource_id: str, capacity: int) -> dict:
    if not isinstance(capacity, int) or capacity < 0:
        raise ValueError("capacity must be nonnegative integer")
    result = deepcopy(data)
    match = [r for r in result["resources"] if r["id"] == resource_id]
    if len(match) != 1:
        raise ValueError(f"resource not found: {resource_id}")
    match[0]["capacity"] = capacity
    return result


def plan(data: dict) -> dict:
    """Deterministic schedule in *declared priority* order. Not globally optimal."""
    validate(data)
    remaining = {r["id"]: r["capacity"] for r in data["resources"]}
    per_program: dict[str, dict] = {}
    for p in sorted(data["programs"], key=lambda p: (p["priority"], p["id"])):
        seats = min([p["seats"]] + [remaining[r] for r in p["resources"]])
        for r in p["resources"]:
            remaining[r] -= seats
        per_program[p["id"]] = {"planned": p["seats"], "feasible": seats, "gap": p["seats"] - seats}
    return {
        "programs": per_program,
        "planned_total": sum(x["planned"] for x in per_program.values()),
        "feasible_total": sum(x["feasible"] for x in per_program.values()),
        "remaining_resources": remaining,
        "method": "fixed_priority_greedy_not_optimal",
    }


def impact_paths(data: dict, resource_id: str) -> list[dict]:
    """Independent non-graph baseline: 4-way joins over JSON arrays."""
    paths = set()
    skill_to_jobs = {s["id"]: [] for s in data["skills"]}
    for o in data["occupations"]:
        for sid in o["skills"]:
            skill_to_jobs[sid].append(o["id"])
    for p in data["programs"]:
        if resource_id in p["resources"]:
            for sid in p["skills"]:
                for oid in skill_to_jobs.get(sid, []):
                    paths.add((p["id"], sid, oid))
    return [{"program": p, "skill": s, "occupation": o} for p, s, o in sorted(paths)]


def worlds(data: dict) -> list[dict]:
    sc = data["scenario"]
    return [set_capacity(data, sc["resource"], cap) for cap in
            (sc["capacity_a"], sc["capacity_b"], sc["capacity_a"])]


def classify_impacts(states: list[dict], paths: list[dict]) -> dict:
    """Separate graph reachability from observed seat changes between A and B.

    Important: paths through a changed program are *not* proof of jobs created,
    lost skills, or causal economic effects. Only training-seat capacities differ.
    """
    if len(states) != 3 or states[0] != states[2]:
        raise AssertionError("Expected restored A→B→A states")
    a, b = states[0]["programs"], states[1]["programs"]
    if set(a) != set(b):
        raise AssertionError("Program identities differ between A and B")
    deltas = []
    for pid in sorted(a):
        if a[pid]["planned"] != b[pid]["planned"]:
            raise AssertionError(f"Changed planned seats: {pid}")
        before, after = a[pid]["feasible"], b[pid]["feasible"]
        if before != after:
            deltas.append({
                "program": pid, "feasible_a": before, "feasible_b": after,
                "delta_b_minus_a": after - before,
            })
    affected_ids = {d["program"] for d in deltas}
    affected_paths = sorted(
        (p for p in paths if p["program"] in affected_ids),
        key=lambda p: (p["program"], p["skill"], p["occupation"]),
    )
    # `paths` describe structural reachability, not who actually lost seats.
    return {"program_deltas": deltas, "affected_paths": affected_paths}


def evaluate_baseline(data: dict) -> dict:
    states = [plan(w) for w in worlds(data)]
    if states[0] != states[2]:
        raise AssertionError("A→B→A restoration mismatch")
    paths = impact_paths(data, data["scenario"]["resource"])
    impacts = classify_impacts(states, paths)
    role_paths = occupation_provider_paths(data)
    coverage = coverage_proxies(data, states)
    return {"states": states, "impact_paths": paths, **impacts,
            "occupation_provider_paths": role_paths, **coverage, "restored": True}


def occupation_provider_paths(data: dict) -> list[dict]:
    """Independent JSON-join baseline for all occupation/skill/program evidence.

    This is NOT a proof that any learner acquired a skill or is employable.
    """
    validate(data)
    paths = set()
    providers = {s["id"]: set() for s in data["skills"]}
    for p in data["programs"]:
        for sid in p["skills"]:
            providers[sid].add(p["id"])
    for o in data["occupations"]:
        for sid in o["skills"]:
            for pid in providers[sid]:
                paths.add((o["id"], sid, pid))
    return [dict(occupation=o, skill=s, program=p) for o, s, p in sorted(paths)]


def coverage_proxies(data: dict, states: list[dict]) -> dict:
    """Compare *training-seat opportunities*, not people, skills achieved or jobs.

    Each feasible program seat contributes one possible training-seat opportunity
    for each skill declared by that program. Summing across programs may count
    overlapping cohorts, and the minimum across required skills is only a
    bottleneck proxy (not a guaranteed qualified-person count).

    Requires three A→B→A allocation states, computed elsewhere.
    """
    validate(data)
    if len(states) != 3 or states[0] != states[2]:
        raise AssertionError("Expected restored A→B→A allocation states")
    planned_ids = {p["id"] for p in data["programs"]}
    for state in states:
        if set(state["programs"]) != planned_ids:
            raise AssertionError("Allocation state does not match program catalog")

    providers: dict[str, list[str]] = {s["id"]: [] for s in data["skills"]}
    for p in data["programs"]:
        for sid in p["skills"]:
            providers[sid].append(p["id"])
    for sids in providers.values():
        sids.sort()

    def opportunity(state: dict, sid: str) -> int:
        return sum(state["programs"][pid]["feasible"] for pid in providers[sid])

    a, b = states[:2]
    skill_seat_opportunities = []
    for sid in sorted(providers):
        va, vb = opportunity(a, sid), opportunity(b, sid)
        skill_seat_opportunities.append({
            "skill": sid, "seat_opportunities_a": va, "seat_opportunities_b": vb,
            "delta_b_minus_a": vb - va, "provider_programs": providers[sid],
        })

    occupation_bottleneck_proxies = []
    for o in sorted(data["occupations"], key=lambda item: item["id"]):
        required = sorted(set(o["skills"]))
        # Empty requirement sets are unknown/invalid, not proof of infinite supply.
        if not required:
            raise ValueError(f"missing required skills for occupation {o['id']}")
        vals_a = {sid: opportunity(a, sid) for sid in required}
        vals_b = {sid: opportunity(b, sid) for sid in required}
        ca, cb = min(vals_a.values()), min(vals_b.values())
        occupation_bottleneck_proxies.append({
            "occupation": o["id"], "required_skills": required,
            "bottleneck_proxy_a": ca, "bottleneck_proxy_b": cb,
            "delta_b_minus_a": cb - ca,
            "bottleneck_skills_a": sorted(s for s in required if vals_a[s] == ca),
            "bottleneck_skills_b": sorted(s for s in required if vals_b[s] == cb),
            "changed_skill_opportunities": sorted(s for s in required if vals_a[s] != vals_b[s]),
        })
    changed = [r["occupation"] for r in occupation_bottleneck_proxies if r["delta_b_minus_a"] != 0]
    return {
        "skill_seat_opportunities": skill_seat_opportunities,
        "occupation_bottleneck_proxies": occupation_bottleneck_proxies,
        "occupations_with_proxy_delta": changed,
        "coverage_claim": (
            "Seat-opportunity and minimum-skill bottleneck proxies only; "
            "NOT actual skill acquisition, graduate counts, employment or policy impact."
        ),
    }
