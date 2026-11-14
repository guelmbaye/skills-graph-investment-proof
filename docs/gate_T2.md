# Gate T2 — Evidence filtering and occupation bottleneck proxy

**Scope**: isolated, fictional SG/Relate contest prototype. No field evidence, no personal data, no prediction of actual skills or jobs.

## Validated user result from T1 (14 Nov 2026)

Windows host reported `relate_version=1.0.1`, `same_outcome=true`, restored A→B→A, only P-CLOUD `feasible=60→20` and 3 affected paths. This **does not** by itself validate this T2 package.

## Why T2 exists

T1 returns an `affected_paths` entry for `SOC-ANALYST` because P-CLOUD also teaches SIEM, but SOC Analyst additionally requires INCIDENT, taught by unchanged P-SOC. An affected path is not proof that the role's skill-seat coverage changed.

T2 explicitly separates:

1. `impact_paths`: all structural paths reachable from the changed resource, 6 paths.
2. `program_deltas` and `affected_paths`: seats actually changed and the 3 associated paths.
3. `skill_seat_opportunities`: sum of per-program **feasible training seats** declaring each skill. Not unique people or skills acquired.
4. `occupation_bottleneck_proxies`: minimum skill-seat opportunities among the declared required skills of each occupation. This is a **capacity bottleneck proxy, not skilled workers / jobs**.
5. `occupation_provider_paths`: relationship explanations read from Cypher in Relate and JSON joins in the fair baseline.

## Exact fixture oracle — do not compute expected answers from the code under test

| Metric | World A | World B | Delta |
|---|---:|---:|---:|
| P-SOC seats | 80 | 80 | 0 |
| P-CLOUD seats | 60 | 20 | −40 |
| SIEM opportunities | 140 | 100 | −40 |
| CLOUDSEC opportunities | 60 | 20 | −40 |
| INCIDENT opportunities | 80 | 80 | 0 |
| SOC-ANALYST bottleneck proxy | 80 | 80 | 0 |
| CLOUD-ENG bottleneck proxy | 60 | 20 | −40 |
| DATA-ANALYST bottleneck proxy | 40 | 40 | 0 |

The apparent SOC-ANALYST impact must be filtered out of `occupations_with_proxy_delta`. If that role is changed to require only `SIEM`, its bottleneck proxy must change 140→100; the graph test also checks this counterfactual when `relate-db` is installed.

## Fairness and limitations

- Python's fixed-priority greedy algorithm is shared by both backends: `same_outcome` means graph storage and joins agree, **not independent optimization or a competitive advantage**.
- External mathematical checks cover the **small fixed fixture**; more general correctness requires a separately implemented solver and independent, varied examples.
- Aggregated training seats per skill may double count programs taken by one learner. Required skills may be taught by different programs to different people. Do **not** call these numbers graduates, qualifications achieved, workforce capacity, or jobs.
- An occupation bottleneck proxy does not guarantee those seats are compatible, accessible, temporally feasible, or lead to assessed skills.
- Relate and JSON/SQL can produce identical answers; this is a **functional comparison**, not an originality claim.
- No measured operational gain, procurement buyer, or superiority to a serious baseline has been established.

## Gate T2 exit rule

**Technical pass only** if Windows Relate 1.0.1 runs tests including mutation, `same_outcome=true`, and the two counts above (`SOC-ANALYST` unchanged, `CLOUD-ENG` −40). **Competition readiness remains HOLD**, unless a 2-minute demo clearly showcases connected provenance and the team documents its true limits.
