import json
import unittest
from copy import deepcopy
from pathlib import Path
from skills_graph.core import load_data, plan, set_capacity, impact_paths, evaluate_baseline, validate

FIX = Path(__file__).resolve().parents[1] / "data" / "scenario_synthetic.json"

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.d = load_data(FIX)

    def test_world_a_expected(self):
        p = plan(self.d)
        self.assertEqual(p["planned_total"], 180)
        self.assertEqual(p["feasible_total"], 180)
        self.assertEqual([p["programs"][x]["feasible"] for x in ("P-SOC", "P-CLOUD", "P-DATA")], [80,60,40])

    def test_world_b_oracle_independent_of_planner(self):
        # External arithmetic oracle: A gets 80 first; B gets min(60,100-80)=20; C unaffected=40.
        mutated = set_capacity(self.d, "LAB-SOC", 100)
        p = plan(mutated)
        self.assertEqual(p["feasible_total"], 80 + min(60, 100-80) + 40)
        self.assertEqual(p["programs"]["P-CLOUD"]["gap"], 40)

    def test_restore_exact_a_b_a(self):
        r = evaluate_baseline(self.d)
        self.assertEqual(r["states"][0], r["states"][2])
        self.assertNotEqual(r["states"][0], r["states"][1])

    def test_impacted_programs_but_no_data(self):
        paths = impact_paths(self.d, "LAB-SOC")
        self.assertEqual({p["program"] for p in paths}, {"P-SOC", "P-CLOUD"})
        self.assertNotIn("DATA-ANALYST", {p["occupation"] for p in paths})
        self.assertIn("SOC-ANALYST", {p["occupation"] for p in paths})
        self.assertIn("CLOUD-ENG", {p["occupation"] for p in paths})

    def test_reachability_is_not_observed_impact(self):
        result = evaluate_baseline(self.d)
        # Both P-SOC and P-CLOUD touch the lab but ONLY P-CLOUD loses seats.
        self.assertEqual({p["program"] for p in result["impact_paths"]},
                         {"P-SOC", "P-CLOUD"})
        self.assertEqual(result["program_deltas"], [{
            "program": "P-CLOUD", "feasible_a": 60, "feasible_b": 20,
            "delta_b_minus_a": -40,
        }])
        self.assertEqual(len(result["affected_paths"]), 3)
        self.assertEqual({p["program"] for p in result["affected_paths"]},
                         {"P-CLOUD"})
        self.assertEqual({p["occupation"] for p in result["affected_paths"]},
                         {"SOC-ANALYST", "CLOUD-ENG"})

    def test_equal_capacity_makes_no_observed_impact_despite_paths(self):
        d = deepcopy(self.d)
        d["scenario"]["capacity_b"] = d["scenario"]["capacity_a"]
        result = evaluate_baseline(d)
        self.assertTrue(result["impact_paths"])
        self.assertEqual(result["affected_paths"], [])
        self.assertEqual(result["program_deltas"], [])

    def test_restoration_preserves_impact_classification(self):
        result = evaluate_baseline(self.d)
        self.assertEqual(result["states"][0], result["states"][2])
        self.assertEqual(result["states"][1]["feasible_total"], 140)

    def test_no_mutation_of_source(self):
        before = json.dumps(self.d, sort_keys=True)
        set_capacity(self.d, "LAB-SOC", 100)
        self.assertEqual(json.dumps(self.d, sort_keys=True), before)

    def test_zero_lab_capacity(self):
        p = plan(set_capacity(self.d, "LAB-SOC", 0))
        self.assertEqual(p["programs"]["P-SOC"]["feasible"], 0)
        self.assertEqual(p["programs"]["P-CLOUD"]["feasible"], 0)
        self.assertEqual(p["programs"]["P-DATA"]["feasible"], 40)

    def test_unknown_capacity_is_not_zero(self):
        d = deepcopy(self.d)
        d["resources"][0]["capacity"] = None
        with self.assertRaisesRegex(ValueError, "unknown/invalid"):
            validate(d)

    def test_unknown_resource_rejected(self):
        d = deepcopy(self.d)
        d["programs"][0]["resources"] = ["ABSENT"]
        with self.assertRaises(ValueError):
            validate(d)

    def test_duplicate_id_rejected(self):
        d = deepcopy(self.d)
        d["resources"].append(deepcopy(d["resources"][0]))
        with self.assertRaises(ValueError):
            validate(d)

    def test_priority_swap_changes_allocations_not_total(self):
        d = set_capacity(self.d, "LAB-SOC", 100)
        d["programs"][0]["priority"] = 5
        d["programs"][1]["priority"] = 1
        p = plan(d)
        self.assertEqual(p["programs"]["P-CLOUD"]["feasible"], 60)
        self.assertEqual(p["programs"]["P-SOC"]["feasible"], 40)
        self.assertEqual(p["feasible_total"], 140)

    def test_no_programs_rejected(self):
        d = deepcopy(self.d)
        d["programs"] = []
        with self.assertRaises(ValueError):
            validate(d)

if __name__ == "__main__":
    unittest.main()
