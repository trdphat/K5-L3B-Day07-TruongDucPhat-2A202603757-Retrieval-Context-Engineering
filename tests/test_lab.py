"""Behavioral tests for real pipeline boundaries; no mocked benchmark scores."""
import json
import unittest
from types import SimpleNamespace
from src.lab import CONFIGS, ROOT, digest, load, rrf, run_agent, render_finish
from baseline import hit, pack_context


class LabTests(unittest.TestCase):
    def test_citation_header_normalization_rejects_unknown_ids(self):
        raw = dict(status='answered', answer='A supported claim.', citations=['abc | doc.pdf | page 1'])
        rendered = render_finish(raw, ['abc'])
        self.assertEqual(rendered['citations'], ['abc'])
        self.assertIn('[abc]', rendered['answer'])
        self.assertEqual(render_finish(raw, ['different'])['status'], 'abstain')

    def test_fusion_uses_rank_and_deduplicates(self):
        a, b = {'id': 'a', 'score': -100}, {'id': 'b', 'score': 99999}
        result = rrf({'dense': [a, b], 'tfidf': [b]})
        self.assertEqual([r['id'] for r in result], ['b', 'a'])
        self.assertEqual(result[0]['ranks'], {'dense': 2, 'tfidf': 1})

    def test_benchmark_resolves_and_has_required_splits(self):
        cases, chunks = load(ROOT/'data/questions.json'), load(ROOT/'data/chunks.json')
        for split, minimum in [('dev', 15), ('test', 5)]:
            selected = [q for q in cases if q['split']==split]
            self.assertGreaterEqual(sum(q['answerable'] for q in selected), minimum)
            self.assertGreaterEqual(sum(not q['answerable'] for q in selected), 2)
            for q in selected:
                if q['answerable']:
                    self.assertTrue(any(hit(c, q['gold']) for c in chunks), q['id'])
        provenance = load(ROOT/'data/provenance.json')
        self.assertEqual(digest(chunks), provenance['corpus_sha256'])

    def test_context_has_provenance_and_budget(self):
        chunk = load(ROOT/'data/chunks.json')[0]
        text, ids = pack_context([chunk, chunk], 6000)
        self.assertEqual(ids, [chunk['id']])
        self.assertIn(chunk['source'], text)
        self.assertIn(f"page {chunk['page']}", text)
        self.assertLessEqual(len(text), 6000)

    def test_provider_error_is_error_not_abstention(self):
        class Broken:
            def create(self, **kwargs):
                raise ConnectionError('synthetic test outage')
        retrieval = SimpleNamespace(embedding_tokens=0, embedding_requests=0,
            client=SimpleNamespace(chat=SimpleNamespace(completions=Broken())))
        result = run_agent('A question', retrieval, CONFIGS['dense'])
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['error_type'], 'ConnectionError')


if __name__ == '__main__':
    unittest.main()
