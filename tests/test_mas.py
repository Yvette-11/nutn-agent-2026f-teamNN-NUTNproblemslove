import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import MCPClient
from mas import OfflineModel, GeminiModel, run_mas, checked_tool, validate_return, CONTRACTS

P = '宿舍冷氣壞掉了'
L = '學生宿舍'

class MASTests(unittest.TestCase):
    def setUp(self):
        self.client = MCPClient()
        self.addCleanup(self.client.close)

    def test_normal_trace_and_baseline(self):
        raw = self.client.call_tool('get_repair_information', {'problem_description': P, 'location': L})
        self.assertFalse(raw['isError'])
        baseline = raw['structuredContent']
        result = run_mas(self.client, OfflineModel(), P, L)
        self.assertEqual(result['status'], 'OFFLINE_PASS')
        self.assertEqual(result['model_calls'], 6)
        self.assertEqual(result['real_model_calls'], 0)
        for field in ('repair_system', 'repair_category'):
            self.assertIn(baseline[field], result['final_answer'])
        for field in baseline['required_information']:
            self.assertIn(field, result['final_answer'])
        self.assertEqual(set(result['ledger']), {'route', 'fields'})
        Path('docs/week08/evidence/normal.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        Path('docs/week08/evidence/baseline.json').write_text(json.dumps({'mode':'original_read_tool', 'tool_result':baseline, 'note':'原選項1唯讀工具；非SAS模型品質測試'},ensure_ascii=False,indent=2),encoding='utf-8')

    def test_missing_input(self):
        result = run_mas(self.client, OfflineModel(), '', L)
        self.assertEqual(result['error'], 'INPUT_REQUIRED')
        self.assertEqual(result['model_calls'], 0)

    def test_out_of_scope(self):
        result = run_mas(self.client, OfflineModel(), '飲水機壞了', '教室')
        self.assertEqual(result['status'], 'FAILED')
        self.assertNotIn('final_answer', result)

    def test_write_tool_denied_before_execution(self):
        with self.assertRaisesRegex(ValueError, 'PERMISSION'):
            checked_tool(self.client,'routing','create_repair_draft',{},CONTRACTS['routing'])

    def test_server_role_and_version_validation(self):
        for changed in ({'role':'requirements'}, {'version':'stale'}, {'task_id':'fields'}, {'extra':'x'}):
            args = {'problem_description':P,'location':L,'role':'routing','task_id':'route','version':'route-v1', **changed}
            result = self.client.call_tool('read_repair_route',args)
            self.assertTrue(result['isError'])

    def test_sources_and_stale_delivery_rejected(self):
        fact = checked_tool(self.client,'routing','read_repair_route',{'problem_description':P,'location':L},CONTRACTS['routing'])
        good = OfflineModel().step('routing', {'tool_result':fact})
        for change in ({'version':'old'}, {'source_id':'fake'}, {'chunk_ids':[]}):
            with self.assertRaises(ValueError):
                validate_return('routing', {**good, **change}, fact)

    def test_model_failure_bounded(self):
        class Failing(OfflineModel):
            def step(self, role, context):
                raise TimeoutError('injected timeout')
        result = run_mas(self.client, Failing(), P, L)
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(result['model_calls'], 1)

    def test_early_finish_rejected(self):
        class Early(OfflineModel):
            def step(self, role, context):
                return {'action':'finish'}
        self.assertEqual(run_mas(self.client, Early(),P,L)['status'],'FAILED')

    def test_context_scope_and_fresh_run(self):
        first = run_mas(self.client,OfflineModel(),P,L)
        second = run_mas(self.client,OfflineModel(),'',L)
        self.assertNotEqual(first['run_id'],second['run_id'])
        self.assertEqual(second['board'],{})
        contexts = [e for e in first['events'] if e['kind']=='model_input' and e['from']=='requirements']
        self.assertTrue(all('board' not in e['context'] for e in contexts))

    def test_mas_does_not_authorize_draft(self):
        run_mas(self.client,OfflineModel(),P,L)
        result = self.client.call_tool('create_repair_draft', {'problem_description':P,'location':L,
            'repair_category':'土木、空調或水電／其他維修','unit':'測試','building':'測試','request_id':'TEST-NO-WRITE'})
        self.assertTrue(result['isError'])
        self.assertIn('READ_REQUIRED',str(result))

if __name__ == '__main__':
    unittest.main(verbosity=2)
