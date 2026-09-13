import unittest
from us_equity_cross_sectional.fundamentals.sec_facts import standalone_quarter, ttm_from_quarters

class AccountingTransformTest(unittest.TestCase):
 def test_q1_q2_q3_q4(self):
  self.assertEqual(10, standalone_quarter(10,None,'Q1'))
  self.assertEqual(12, standalone_quarter(22,10,'Q2'))
  self.assertEqual(13, standalone_quarter(35,22,'Q3'))
  self.assertEqual(15, standalone_quarter(50,35,'FY'))
 def test_missing_prior_rejected(self):
  with self.assertRaises(ValueError): standalone_quarter(22,None,'Q2')
 def test_ttm_requires_four_same_unit(self):
  self.assertEqual(46,ttm_from_quarters([10,11,12,13],['USD']*4))
  with self.assertRaises(ValueError): ttm_from_quarters([10,11,12],['USD']*3)
  with self.assertRaises(ValueError): ttm_from_quarters([10,11,12,13],['USD','USD','shares','USD'])
