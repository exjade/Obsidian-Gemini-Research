import hashlib
import json
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import source_resolver as resolver
import source_metadata


def response(url, payload, status=200):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode('utf-8')
    return {'status': status, 'url': url, 'body': body}


class ResolverTests(unittest.TestCase):
    def test_doi_crossref_resolution_is_normalized_and_attributed(self):
        url = resolver._crossref_url('10.1234/a.b')
        calls = []

        def transport(requested):
            calls.append(requested)
            return response(requested, {'message': {'DOI': '10.1234/A.B', 'title': [' A   useful title '],
                                                    'URL': 'https://doi.org/10.1234/a.b'}})

        receipt = resolver.resolve('doi', 'https://doi.org/10.1234/A.B', transport)
        self.assertEqual(calls, [url])
        self.assertEqual(receipt['outcome'], 'resolved')
        self.assertEqual(receipt['provider'], 'crossref')
        self.assertEqual(receipt['lookup_value'], '10.1234/a.b')
        self.assertEqual(receipt['metadata']['title']['normalized'], 'A useful title')
        self.assertEqual(receipt['metadata']['doi']['normalized'], '10.1234/a.b')
        self.assertEqual(receipt['response_sha256'], hashlib.sha256(transport(url)['body']).hexdigest())

    def test_provider_identifier_mismatch_is_conflict_not_assertion(self):
        url = resolver._crossref_url('10.1234/a')
        receipt = resolver.resolve('doi', '10.1234/a', lambda requested: response(
            requested, {'message': {'DOI': '10.1234/b', 'title': ['Different work']}}))
        self.assertEqual(receipt['outcome'], 'conflict')
        self.assertEqual(source_metadata.resolution_assertions(receipt), [])

    def test_pmid_resolution_extracts_provider_identifiers(self):
        url = resolver._ncbi_summary_url('12345')
        payload = {'result': {'uids': ['12345'], '12345': {
            'uid': '12345', 'title': 'Study of a system', 'articleids': [
                {'idtype': 'doi', 'value': '10.1234/study'}, {'idtype': 'pmc', 'value': 'PMC456'}]}}}
        receipt = resolver.resolve('pmid', '12345', lambda requested: response(requested, payload))
        self.assertEqual(receipt['outcome'], 'resolved')
        self.assertEqual(receipt['metadata']['pmid']['normalized'], '12345')
        self.assertEqual(receipt['metadata']['doi']['normalized'], '10.1234/study')
        self.assertEqual(receipt['metadata']['pmcid']['normalized'], 'PMC456')
        self.assertEqual(receipt['endpoint'], url)

    def test_pmid_accepts_ncbi_pmcid_identifier_type(self):
        payload = {'result': {'uids': ['12345'], '12345': {
            'uid': '12345', 'title': 'Study of a system', 'articleids': [
                {'idtype': 'pmcid', 'value': 'PMC456'}]}}}
        receipt = resolver.resolve('pmid', '12345', lambda requested: response(requested, payload))
        self.assertEqual(receipt['outcome'], 'resolved')
        self.assertEqual(receipt['metadata']['pmcid']['normalized'], 'PMC456')

    def test_pmcid_uses_fixed_converter_then_pubmed_summary(self):
        expected = [resolver._ncbi_pmcid_url('PMC456'), resolver._ncbi_summary_url('12345')]
        calls = []

        def transport(requested):
            calls.append(requested)
            if len(calls) == 1:
                return response(requested, {'records': [{'pmcid': 'PMC456', 'pmid': '12345', 'doi': '10.1234/a'}]})
            return response(requested, {'result': {'uids': ['12345'], '12345': {
                'uid': '12345', 'title': 'Resolved title', 'articleids': []}}})

        receipt = resolver.resolve('pmcid', 'pmc456', transport)
        self.assertEqual(calls, expected)
        self.assertEqual(receipt['outcome'], 'resolved')
        self.assertEqual(receipt['metadata']['title']['normalized'], 'Resolved title')
        self.assertEqual(receipt['metadata']['pmcid']['normalized'], 'PMC456')

    def test_not_found_malformed_timeout_and_http_error(self):
        doi_url = resolver._crossref_url('10.1234/a')
        self.assertEqual(resolver.resolve('doi', '10.1234/a',
            lambda url: response(url, b'', 404))['outcome'], 'not_found')
        self.assertEqual(resolver.resolve('doi', '10.1234/a',
            lambda url: response(url, b'not json'))['outcome'], 'error')
        self.assertEqual(resolver.resolve('doi', '10.1234/a',
            lambda url: response(url, b'', 503))['outcome'], 'error')

        def timeout(url):
            raise TimeoutError('timeout fixture')
        self.assertIn('timeout fixture', resolver.resolve('doi', '10.1234/a', timeout)['error'])
        self.assertEqual(doi_url, resolver._crossref_url('10.1234/a'))

    def test_unknown_destination_redirect_and_oversize_are_rejected(self):
        with self.assertRaises(ValueError):
            resolver._allowed_url('https://example.org/works/10.1234/a')
        with self.assertRaises(ValueError):
            resolver._allowed_url('http://api.crossref.org/works/10.1234/a')
        with self.assertRaises(ValueError):
            resolver._request_json('https://api.crossref.org/works/10.1234/a',
                lambda url: {'status': 302, 'url': 'https://api.crossref.org/elsewhere', 'body': b''})
        with self.assertRaises(ValueError):
            resolver._request_json('https://api.crossref.org/works/10.1234/a',
                lambda url: {'status': 200, 'url': url, 'body': b' ' * (resolver.MAX_BYTES + 1)})

    def test_identifier_input_is_validated_before_transport(self):
        called = []
        with self.assertRaises(ValueError):
            resolver.resolve('doi', 'https://example.org/10.1234/a', lambda url: called.append(url))
        with self.assertRaises(ValueError):
            resolver.resolve('title', 'A title', lambda url: called.append(url))
        self.assertEqual(called, [])

    def test_receipt_integrity_and_catalog_lookup_gate_are_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_id = 'a' * 64
            catalog = root / '.project-intelligence/library/sources.json'
            catalog.parent.mkdir(parents=True)
            catalog.write_text(json.dumps({'sources': [{'source_id': source_id,
                'identity_policy': 'source-identity-v1', 'metadata': {'fields': {
                    'doi': {'values': ['10.1234/a']}}}}]}), encoding='utf-8')
            calls = []

            def transport(url):
                calls.append(url)
                return response(url, {'message': {'DOI': '10.1234/a', 'title': ['Paper']}})

            first = resolver.resolve_for_source(root, source_id, 'doi', '10.1234/a', transport=transport)
            second = resolver.resolve_for_source(root, source_id, 'doi', '10.1234/a', transport=transport)
            self.assertEqual(first, second)
            self.assertEqual(len(calls), 1)
            self.assertTrue(resolver.valid_receipt(first, source_id))
            self.assertEqual(resolver.trusted_receipts_for_source(root, source_id), [first])
            tampered = dict(first, lookup_value='10.1234/other')
            self.assertFalse(resolver.valid_receipt(tampered, source_id))
            with self.assertRaises(ValueError):
                resolver.resolve_for_source(root, source_id, 'doi', '10.1234/not-catalogued', transport=transport)

    def test_tampered_persisted_receipt_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_id = 'b' * 64
            receipt = resolver.resolve('doi', '10.1234/a', lambda url: response(
                url, {'message': {'DOI': '10.1234/a', 'title': ['Paper']}}))
            saved = resolver.save_receipt(root, source_id, receipt)
            path = root / resolver.DIRECTORY / (saved['id'] + '.json')
            payload = json.loads(path.read_text(encoding='utf-8'))
            payload['metadata']['title']['normalized'] = 'Tampered'
            path.write_text(json.dumps(payload), encoding='utf-8')
            self.assertEqual(resolver.trusted_receipts_for_source(root, source_id), [])


if __name__ == '__main__':
    unittest.main()
