# Gate T1 — Observation vs reachability

**Status:** baseline tests locally verified; Relate engine execution remains to be verified on the Windows host.

## False-positive exposed in T0

T0 returned 6 resource-reachable paths containing programs `P-SOC` and `P-CLOUD`. That traversal was technically correct but could be misread as actual impact. The SOC program does **not** lose any seat when LAB-SOC changes from 140 to 100 because of fixed priority.

## T1 correction

1. Preserve `impact_paths` as raw connected structural paths, for backward compatibility.
2. Compare states A/B and report `program_deltas` for **observed seat-count changes only**.
3. Intersect those changed programs with the structural paths to produce `affected_paths`.
4. Verify A→B→A equality and baseline/Relate same-outcome over every new field.

**Expected:** 6 reachable paths, 3 affected paths, only one changed program `P-CLOUD` with delta −40; `P-SOC` and `P-DATA` unchanged.

## Scientific and commercial limits

These are synthetic seats in a fixed-priority model. An affected path connecting a program to a skill and occupation **does not** quantify acquired skills, actual economic impact or employment. The graph is useful for provenance/traversal, but is not yet shown to outperform a competent deterministic JSON/SQL baseline.

**Next gate:** not a new product. Prove on developer's Relate 1.0.1 that the patched report has no false attribution, then assess if the graph earns its complexity.
