import unittest
from app.data import normalize, ElectionStore

class ElectionTests(unittest.TestCase):
    def test_normalize_and_never_call_race(self):
        raw={'year':2026,'office':'House','live':True,'as_of':'2026-11-03T23:00:00+00:00','races':{'VA-10':{'leader':'D','called':True,'winner':'D','total':300,'cands':[{'n':'Example A','p':'D','v':200,'pct':66.67},{'n':'Example B','p':'R','v':100,'pct':33.33}]}}}
        result=normalize('House',raw)
        self.assertEqual(result['races'][0]['called'],False)
        self.assertIsNone(result['races'][0]['winner'])
        self.assertEqual(result['races'][0]['candidates'][0]['votes'],200)
    def test_reject_wrong_year(self):
        with self.assertRaises(ValueError): normalize('House', {'year':2024,'office':'House'})
    def test_initial_feed_does_not_narrate(self):
        s=ElectionStore();race={'key':'VA-10','total':1000,'candidates':[{'name':'A','party':'D','votes':600}], 'office':'House'}
        s.process('House',{'races':[race]})
        self.assertEqual(len(s.events),0)

if __name__=='__main__':unittest.main()
