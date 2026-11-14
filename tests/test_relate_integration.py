import tempfile
import unittest
from pathlib import Path
from skills_graph.core import load_data, evaluate_baseline
from skills_graph.relate_backend import run_relate

DATA = Path(__file__).resolve().parents[1] / "data" / "scenario_synthetic.json"

class RelateIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(__import__('importlib').util.find_spec("relate") is not None,
                         "relate-db not installed in this environment; NO runtime PASS claim")
    def test_real_embedded_graph_and_restoration(self):
        data = load_data(DATA)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"demo.rl"
            result = run_relate(data, str(path))
            baseline = evaluate_baseline(data)
            self.assertTrue(path.exists())
            self.assertEqual(baseline["states"], result["states"])
            for key in ("impact_paths", "program_deltas", "affected_paths",
                        "occupation_provider_paths", "skill_seat_opportunities",
                        "occupation_bottleneck_proxies", "occupations_with_proxy_delta", "coverage_claim"):
                self.assertEqual(baseline[key], result[key])
            self.assertEqual({p["program"] for p in result["affected_paths"]}, {"P-CLOUD"})
            self.assertEqual(result["occupations_with_proxy_delta"], ["CLOUD-ENG"])

    @unittest.skipUnless(__import__('importlib').util.find_spec("relate") is not None,
                         "relate-db not installed in this environment; NO runtime PASS claim")
    def test_graph_relationship_mutation_changes_occupation_conclusion(self):
        from copy import deepcopy
        d = deepcopy(load_data(DATA))
        # If SOC Analyst only requires SIEM, it is sensitive to the changed SIEM opportunities.
        for o in d["occupations"]:
            if o["id"] == "SOC-ANALYST":
                o["skills"] = ["SIEM"]
        with tempfile.TemporaryDirectory() as td:
            result = run_relate(d, str(Path(td) / "changed-role.rl"))
            baseline = evaluate_baseline(d)
            self.assertEqual(result["occupation_bottleneck_proxies"],
                             baseline["occupation_bottleneck_proxies"])
            self.assertEqual(set(result["occupations_with_proxy_delta"]),
                             {"CLOUD-ENG", "SOC-ANALYST"})

if __name__ == "__main__":
    unittest.main()
