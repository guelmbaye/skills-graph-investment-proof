import unittest
from copy import deepcopy
from pathlib import Path
from skills_graph.core import load_data, evaluate_baseline, validate, coverage_proxies, occupation_provider_paths

FIX = Path(__file__).resolve().parents[1] / "data" / "scenario_synthetic.json"

class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.d = load_data(FIX)
        self.result = evaluate_baseline(self.d)

    def test_skill_seat_opportunities(self):
        got = {x['skill']: (x['seat_opportunities_a'], x['seat_opportunities_b'])
               for x in self.result['skill_seat_opportunities']}
        # Independent hand-calculated fixture expectations, not a second call to the planner.
        self.assertEqual(got, {
            'SIEM': (140, 100), 'INCIDENT': (80, 80),
            'CLOUDSEC': (60, 20), 'DATAENG': (40, 40),
        })

    def test_bottleneck_proxy_avoids_false_occupation_impact(self):
        got = {r['occupation']: r for r in self.result['occupation_bottleneck_proxies']}
        self.assertEqual((got['CLOUD-ENG']['bottleneck_proxy_a'],
                          got['CLOUD-ENG']['bottleneck_proxy_b']), (60, 20))
        self.assertEqual(got['CLOUD-ENG']['bottleneck_skills_b'], ['CLOUDSEC'])
        self.assertEqual((got['SOC-ANALYST']['bottleneck_proxy_a'],
                          got['SOC-ANALYST']['bottleneck_proxy_b']), (80, 80))
        self.assertEqual(got['SOC-ANALYST']['bottleneck_skills_b'], ['INCIDENT'])
        self.assertIn('SIEM', got['SOC-ANALYST']['changed_skill_opportunities'])
        self.assertEqual((got['DATA-ANALYST']['bottleneck_proxy_a'],
                          got['DATA-ANALYST']['bottleneck_proxy_b']), (40, 40))
        self.assertEqual(self.result['occupations_with_proxy_delta'], ['CLOUD-ENG'])

    def test_consequence_differs_from_reachability(self):
        self.assertIn('SOC-ANALYST', {p['occupation'] for p in self.result['affected_paths']})
        self.assertNotIn('SOC-ANALYST', self.result['occupations_with_proxy_delta'])
        self.assertEqual(len(self.result['occupation_provider_paths']), 7)
        self.assertEqual(self.result['occupation_provider_paths'], occupation_provider_paths(self.d))

    def test_equal_capacity_no_skill_or_occupation_delta(self):
        d = deepcopy(self.d)
        d['scenario']['capacity_b'] = d['scenario']['capacity_a']
        r = evaluate_baseline(d)
        self.assertEqual(r['occupations_with_proxy_delta'], [])
        self.assertTrue(all(x['delta_b_minus_a'] == 0 for x in r['skill_seat_opportunities']))

    def test_requirement_mutation_flips_soc_analyst_proxy(self):
        d = deepcopy(self.d)
        for o in d['occupations']:
            if o['id'] == 'SOC-ANALYST':
                o['skills'] = ['SIEM']
        r = evaluate_baseline(d)
        got = {x['occupation']: x for x in r['occupation_bottleneck_proxies']}
        self.assertEqual((got['SOC-ANALYST']['bottleneck_proxy_a'],
                          got['SOC-ANALYST']['bottleneck_proxy_b']), (140, 100))
        self.assertEqual(set(r['occupations_with_proxy_delta']), {'SOC-ANALYST','CLOUD-ENG'})

    def test_zero_provider_is_zero_proxy_not_imagined_skills(self):
        d = deepcopy(self.d)
        for p in d['programs']:
            if p['id'] == 'P-CLOUD':
                p['skills'] = ['SIEM']
        r = evaluate_baseline(d)
        got = {x['occupation']: x for x in r['occupation_bottleneck_proxies']}
        self.assertEqual((got['CLOUD-ENG']['bottleneck_proxy_a'],
                          got['CLOUD-ENG']['bottleneck_proxy_b']), (0,0))
        self.assertNotIn('CLOUD-ENG', r['occupations_with_proxy_delta'])

    def test_reject_missing_occupation_requirement(self):
        d = deepcopy(self.d)
        d['occupations'][0]['skills'] = []
        with self.assertRaisesRegex(ValueError, 'missing required skills'):
            evaluate_baseline(d)

    def test_reject_not_really_restored_state(self):
        states = deepcopy(self.result['states'])
        states[2]['feasible_total'] += 1
        with self.assertRaisesRegex(AssertionError, 'restored'):
            coverage_proxies(self.d, states)

if __name__ == '__main__':
    unittest.main()
