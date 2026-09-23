import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import pipeline


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.evidence={'type':'external','url':'https://example.org/paper','excerpt':'Exact passage',
                       'title':'Paper','searched':True,'fetched':True,'retrieved_at':'2026-01-01',
                       'primary':True,'official':True,'primary_kind':'other'}

    def test_secondary_reclassification_is_allowed_and_traced(self):
        revised={**self.evidence,'primary':False,'primary_kind':'review'}
        before=copy.deepcopy(self.evidence)
        changes=pipeline.preserve_evidence([self.evidence],[revised])
        self.assertEqual(changes[0]['fields']['primary'],{'before':True,'after':False})
        self.assertEqual(self.evidence,before)

    def test_removed_or_changed_payload_is_rejected(self):
        with self.assertRaises(ValueError):pipeline.preserve_evidence([self.evidence],[])
        for key,value in [('url','https://example.org/other'),('excerpt','Invented passage'),('fetched',False),('retrieved_at','2027-01-01')]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                pipeline.preserve_evidence([self.evidence],[{**self.evidence,key:value}])

    def test_addition_and_reordering_preserve_originals(self):
        second={**self.evidence,'url':'https://example.org/second'}
        self.assertEqual(pipeline.preserve_evidence([self.evidence],[second,self.evidence]),[])

    def test_document_identity_page_and_context_cannot_change(self):
        document={'type':'document','document_id':'hash','physical_page':4,'excerpt':'Original passage','document_context':'Original context'}
        for key in ('document_id','physical_page','excerpt','document_context'):
            with self.subTest(key=key),self.assertRaises(ValueError):
                pipeline.preserve_evidence([document],[{**document,key:'altered'}])


if __name__=='__main__':unittest.main()
