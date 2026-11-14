# Gate T0 — SG × Relate technical preflight

**Scenario:** A (LAB-SOC=140) → B (LAB-SOC=100) → A (LAB-SOC=140), same other facts.

## Statements that can be verified without Relate

- Independent hand-calculated synthetic oracle at A: SOC 80, CLOUD 60, DATA 40 = 180.
- At B: SOC 80, CLOUD 20, DATA 40 = 140, because priority 1 consumes 80 of the 100 LAB-SOC places first.
- Reversion returns to A; the separate Data lab remains unaffected.
- No missing capacity can be silently treated as 0; model validation rejects it.

## Relate integration status

The official docs specify `pip install relate-db`, `import relate`, `relate.connect("./graph.rl")`, `.execute(...)` and parameter binding. This package implements those calls, but the authoring container does not contain relate-db and cannot access PyPI. **The embedded graph has NOT been run or verified here.** No `.rl` file is claimed to be successfully generated.

Run on a connected local machine; only call integration PASS after `python -m unittest discover -s tests -v` reports the integration test PASS and `python -m skills_graph.demo --backend both ...` reports `same_outcome: true` with a real `.rl` store.

## Competitive verdict

**GO to local API integration preflight, not GO competitive.** The baseline JSON join finds the same pathways and the same deterministic planning results. A Relate graph provides connected-context traversal and inspectable storage but shows no measured advantage yet. We will not claim a superior national policy optimizer, workforce prediction or actual training impact.

## Next checkpoint

1. Real `relate-db` import and Cypher execution on developer machine.
2. Verify graph paths and persistent `.rl` store.
3. Record any syntax or memory limitations and correct only those that are reproducible.
4. If no meaningful benefit in graph traversal / explanation compared with baseline, simplify or stop rather than invent another product.
