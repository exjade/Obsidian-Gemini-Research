import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import unittest
import source_metadata as metadata


class MetadataTests(unittest.TestCase):
    def test_identifier_normalization(self):
        self.assertEqual(metadata.normalize_doi('https://doi.org/10.1234/AbC.X'), '10.1234/abc.x')
        self.assertEqual(metadata.normalize_doi('doi: 10.1234/AbC.X'), '10.1234/abc.x')
        self.assertEqual(metadata.normalize_identifier('pmid', 'PMID: 12345'), '12345')
        self.assertEqual(metadata.normalize_identifier('pmcid', 'pmc12345'), 'PMC12345')
        self.assertEqual(metadata.normalize_identifier('pmid', 'not-an-id'), '')

    def test_conflicts_keep_provenance_and_do_not_choose(self):
        result = metadata.consolidate([
            metadata.assertion('doi', '10.1234/a', 'evidence.declared.doi', 'declared', reference='e1'),
            metadata.assertion('doi', 'https://doi.org/10.1234/B', 'source_check.final_url_identifier', 'observed', reference='check1'),
            metadata.assertion('title', 'Paper title', 'evidence.declared.title', 'declared'),
            metadata.assertion('title', 'Publisher page title', 'source_check.page_title', 'observed'),
            metadata.assertion('original_url', 'https://example.org/a?utm_source=x', 'source_check.original_url'),
            metadata.assertion('final_url', 'https://example.org/b', 'source_check.final_url'),
        ])
        self.assertEqual(result['policy'], 'source-metadata-v1')
        self.assertIsNone(result['fields']['doi']['value'])
        doi_conflict = next(item for item in result['conflicts'] if item['field'] == 'doi')
        self.assertEqual({x['provenance'] for x in doi_conflict['assertions']},
                         {'evidence.declared.doi', 'source_check.final_url_identifier'})
        self.assertEqual(result['fields']['title']['value'], None)
        self.assertNotIn('original_url', [x['field'] for x in result['conflicts']])
        self.assertNotIn('final_url', [x['field'] for x in result['conflicts']])

    def test_equivalent_identifiers_and_merge_are_deterministic(self):
        assertions = [metadata.assertion('doi', '10.1234/X', 'declared'),
                      metadata.assertion('doi', 'https://doi.org/10.1234/x', 'observed')]
        first = metadata.consolidate(assertions)
        second = metadata.consolidate(reversed(assertions))
        self.assertEqual(first, second)
        self.assertEqual(first['fields']['doi']['value'], '10.1234/x')
        self.assertEqual(first['conflicts'], [])

    def test_invalid_url_and_document_hash_are_rejected(self):
        self.assertIsNone(metadata.assertion('url', 'file:///local/path', 'declared'))
        self.assertIsNone(metadata.assertion('document_sha256', 'short', 'declared'))

    def test_full_and_scheme_less_urls_remain_distinct(self):
        full = metadata.assertion('final_url', 'HTTPS://Example.org:443/article#section', 'receipt')
        canonical = metadata.assertion('normalized_final_url', 'example.org/article', 'receipt')
        self.assertEqual(full['value'], 'https://example.org/article')
        self.assertEqual(canonical['value'], 'example.org/article')
        self.assertIsNone(metadata.assertion('normalized_final_url', 'https://example.org/article', 'receipt'))

    def test_resolver_assertions_keep_provider_and_raw_value(self):
        receipt = {'policy': metadata.RESOLUTION_POLICY, 'outcome': 'resolved', 'provider': 'crossref',
                   'lookup_field': 'doi', 'lookup_value': '10.1234/abc', 'id': 'receipt-1',
                   'retrieved_at': '2026-09-23T00:00:00Z',
                   'metadata': {'doi': {'raw': '10.1234/ABC', 'normalized': '10.1234/abc'}}}
        assertions = metadata.resolution_assertions(receipt)
        self.assertEqual(assertions[0]['provenance'], 'resolver.crossref.doi')
        result = metadata.consolidate(assertions)
        saved = result['fields']['doi']['assertions'][0]
        self.assertEqual(saved['value'], '10.1234/abc')
        self.assertEqual(saved['raw_value'], '10.1234/ABC')

    def test_conflict_and_untrusted_policy_do_not_contribute_assertions(self):
        receipt = {'policy': metadata.RESOLUTION_POLICY, 'outcome': 'conflict', 'provider': 'crossref',
                   'lookup_field': 'doi', 'metadata': {'doi': {'raw': '10.1234/x', 'normalized': '10.1234/x'}}}
        self.assertEqual(metadata.resolution_assertions(receipt), [])
        receipt['policy'] = 'foreign-policy'
        receipt['outcome'] = 'resolved'
        self.assertEqual(metadata.resolution_assertions(receipt), [])


if __name__ == '__main__':
    unittest.main()
