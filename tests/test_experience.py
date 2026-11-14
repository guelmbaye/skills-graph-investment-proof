import unittest
from pathlib import Path
from skills_graph.core import load_data, worlds, plan, impact_paths, occupation_provider_paths
from skills_graph.experience import graph_payload, explain, compare_baseline

FIXTURE=Path(__file__).resolve().parents[1]/'data'/'scenario_synthetic.json'

class ExperienceTests(unittest.TestCase):
    def setUp(self):
        self.d=load_data(FIXTURE)
        self.states=[plan(w) for w in worlds(self.d)]
        self.ui=explain(self.d,self.states,impact_paths(self.d,'LAB-SOC'),occupation_provider_paths(self.d),capacity_a=140,capacity_b=100)
    def test_expected_cloud_only(self):
        self.assertEqual(self.ui['changed_programs'],['P-CLOUD'])
        self.assertEqual(self.ui['changed_roles'],['CLOUD-ENG'])
    def test_no_false_soc(self):
        soc=next(x for x in self.ui['occupation_proxies'] if x['occupation']=='SOC-ANALYST')
        self.assertEqual((soc['bottleneck_proxy_a'],soc['bottleneck_proxy_b']),(80,80))
        self.assertNotIn('SOC-ANALYST',self.ui['changed_roles'])
    def test_all_graph_edges(self):
        graph=self.ui['graph']
        self.assertEqual(len(graph['nodes']),13)
        self.assertEqual(len(graph['edges']),16)
        self.assertTrue(any(e['from']=='LAB-SOC' and e['to']=='P-CLOUD' for e in graph['edges']))
        self.assertEqual({n['id'] for n in graph['nodes'] if n['affected']},{'P-CLOUD','CLOUDSEC','SIEM','CLOUD-ENG'})
    def test_full_baseline_parity(self):
        self.assertTrue(compare_baseline(self.d,100,self.ui))
    def test_parity_detects_tamper(self):
        self.ui['programs'][0]['delta']=999
        self.assertFalse(compare_baseline(self.d,100,self.ui))
    def test_no_false_restoration(self):
        self.states[2]['feasible_total']-=1
        with self.assertRaises(AssertionError):
            explain(self.d,self.states,impact_paths(self.d,'LAB-SOC'),occupation_provider_paths(self.d),capacity_a=140,capacity_b=100)
    def test_nondefault_capacity(self):
        from skills_graph.core import set_capacity
        data=dict(self.d)
        data['scenario']=dict(data['scenario'],capacity_b=80)
        states=[plan(w) for w in worlds(data)]
        report=explain(data,states,impact_paths(data,'LAB-SOC'),occupation_provider_paths(data),capacity_a=140,capacity_b=80)
        self.assertTrue(compare_baseline(self.d,80,report))
        self.assertEqual(report['feasible_b'],120)
        self.assertEqual(report['changed_programs'], ['P-CLOUD'])
        self.assertEqual(report['changed_roles'], ['CLOUD-ENG'])

if __name__=='__main__': unittest.main()
