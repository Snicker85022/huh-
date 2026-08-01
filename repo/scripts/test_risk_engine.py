from risk_engine import aggregate_batch_risk, score
import unittest

class TestRiskEngine(unittest.TestCase):
    def test_table_a(self):
        # S=3,O=3,D=3
        result = score(3, 3, 3)
        self.assertEqual(round(result["r"], 4), 3.0)
        self.assertEqual(result["band"], 2)
        self.assertFalse(result["conundrum"])
        self.assertTrue(result["out_of_control"])
        self.assertEqual(result["color"], "coral")
        self.assertEqual(result["research_tier"], 2)
        
        # S=1,O=5,D=1
        result = score(1, 5, 1)
        self.assertEqual(round(result["r"], 4), 1.3077)
        self.assertEqual(result["band"], 4)
        self.assertFalse(result["conundrum"])
        self.assertFalse(result["out_of_control"])
        self.assertEqual(result["color"], "green")
        self.assertEqual(result["research_tier"], 4)
        
        # S=5,O=1,D=1
        result = score(5, 1, 1)
        self.assertEqual(round(result["r"], 4), 1.7100)
        self.assertEqual(result["band"], 4)
        self.assertFalse(result["conundrum"])
        self.assertFalse(result["out_of_control"])
        self.assertEqual(result["color"], "green")
        self.assertEqual(result["research_tier"], 4)
        
        # S=1,O=1,D=5
        result = score(1, 1, 5)
        self.assertEqual(round(result["r"], 4), 2.2361)
        self.assertEqual(result["band"], 3)
        self.assertFalse(result["conundrum"])
        self.assertFalse(result["out_of_control"])
        self.assertEqual(result["color"], "amber")
        self.assertEqual(result["research_tier"], 3)
        
        # S=5,O=1,D=5
        result = score(5, 1, 5)
        self.assertEqual(round(result["r"], 4), 3.8236)
        self.assertEqual(result["band"], 2)
        self.assertTrue(result["conundrum"])
        self.assertFalse(result["out_of_control"])
        self.assertEqual(result["color"], "coral")
        self.assertEqual(result["research_tier"], 2)
        
        # S=4,O=2,D=5
        result = score(4, 2, 5)
        self.assertEqual(round(result["r"], 4), 3.9842)
        self.assertEqual(result["band"], 2)
        self.assertTrue(result["conundrum"])
        self.assertFalse(result["out_of_control"])
        self.assertEqual(result["color"], "coral")
        self.assertEqual(result["research_tier"], 2)
        
        # S=5,O=5,D=5
        result = score(5, 5, 5)
        self.assertEqual(round(result["r"], 4), 5.0)
        self.assertEqual(result["band"], 1)
        self.assertTrue(result["conundrum"])
        self.assertFalse(result["out_of_control"])
        self.assertEqual(result["color"], "red")
        self.assertEqual(result["research_tier"], 1)
        
        # S=2,O=5,D=4
        result = score(2, 5, 4)
        self.assertEqual(round(result["r"], 4), 3.2951)
        self.assertEqual(result["band"], 2)
        self.assertTrue(result["conundrum"])
        self.assertFalse(result["out_of_control"])
        self.assertEqual(result["color"], "coral")
        self.assertEqual(result["research_tier"], 2)
        
        # S=5,O=2,D=4
        result = score(5, 2, 4)
        self.assertEqual(round(result["r"], 4), 3.8388)
        self.assertEqual(result["band"], 2)
        self.assertTrue(result["conundrum"])
        self.assertFalse(result["out_of_control"])
        self.assertEqual(result["color"], "coral")
        self.assertEqual(result["research_tier"], 2)
        
        # S=3,O=4,D=4
        result = score(3, 4, 4)
        self.assertEqual(round(result["r"], 4), 3.6342)
        self.assertEqual(result["band"], 2)
        self.assertTrue(result["conundrum"])
        self.assertTrue(result["out_of_control"])
        self.assertEqual(result["color"], "coral")
        self.assertEqual(result["research_tier"], 2)
        
        # S=3,O=3,D=4
        result = score(3, 3, 4)
        self.assertEqual(round(result["r"], 4), 3.4641)
        self.assertEqual(result["band"], 2)
        self.assertFalse(result["conundrum"])
        self.assertTrue(result["out_of_control"])
        self.assertEqual(result["color"], "coral")
        self.assertEqual(result["research_tier"], 2)
        
        # S=2,O=3,D=4
        result = score(2, 3, 4)
        self.assertEqual(round(result["r"], 4), 3.0262)
        self.assertEqual(result["band"], 2)
        self.assertFalse(result["conundrum"])
        self.assertFalse(result["out_of_control"])
        self.assertEqual(result["color"], "coral")
        self.assertEqual(result["research_tier"], 2)
        
        # S=2,O=2,D=2
        result = score(2, 2, 2)
        self.assertEqual(round(result["r"], 4), 2.0)
        self.assertEqual(result["band"], 3)
        self.assertFalse(result["conundrum"])
        self.assertFalse(result["out_of_control"])
        self.assertEqual(result["color"], "amber")
        self.assertEqual(result["research_tier"], 3)
    
    def test_table_b(self):
        # S=2,O=2,D=2 (raw 2.0000000000000004)
        result = score(2, 2, 2)
        self.assertEqual(round(result["r"], 4), 2.0)
        self.assertEqual(result["band"], 3)
        
        # S=3,O=3,D=3 (raw 2.9999999999999996)
        result = score(3, 3, 3)
        self.assertEqual(round(result["r"], 4), 3.0)
        self.assertEqual(result["band"], 2)
        
        # S=4,O=4,D=4 (raw 4.0)
        result = score(4, 4, 4)
        self.assertEqual(round(result["r"], 4), 4.0)
        self.assertEqual(result["band"], 1)
        
        # S=5,O=5,D=5 (raw 4.999999999999999)
        result = score(5, 5, 5)
        self.assertEqual(round(result["r"], 4), 5.0)
        self.assertEqual(result["band"], 1)
    
    def test_value_errors(self):
        with self.assertRaises(ValueError):
            score(0, 1, 1)
        with self.assertRaises(ValueError):
            score(6, 1, 1)
        with self.assertRaises(ValueError):
            score(1, 1, 0)
        with self.assertRaises(ValueError):
            score(-1, 1, 1)
        with self.assertRaises(ValueError):
            score(1, 5, 7)

class TestAggregateBatchRisk(unittest.TestCase):
    """Spec 09 ABR table (8 rows): aggregate_batch_risk(item_scores, chained)."""

    def test_any_number_of_r_le_2_items(self):
        # Any number of items with R <= 2.0 | No | 0 | ok
        result = aggregate_batch_risk([2.0, 2.0, 2.0], chained=False)
        self.assertEqual(result["abr"], 0.0)
        self.assertEqual(result["outcome"], "ok")

    def test_one_item_r_3(self):
        # One item, R = 3.0 | No | 1.0 | ok
        result = aggregate_batch_risk([3.0], chained=False)
        self.assertEqual(result["abr"], 1.0)
        self.assertEqual(result["outcome"], "ok")

    def test_fourteen_items_r_3(self):
        # Fourteen items, each R = 3.0 | No | 14.0 | near_ceiling
        result = aggregate_batch_risk([3.0] * 14, chained=False)
        self.assertEqual(result["abr"], 14.0)
        self.assertEqual(result["outcome"], "near_ceiling")

    def test_one_item_r_5(self):
        # One item, R = 5.0 | No | 9.0 | ok
        result = aggregate_batch_risk([5.0], chained=False)
        self.assertEqual(result["abr"], 9.0)
        self.assertEqual(result["outcome"], "ok")

    def test_two_items_r_5(self):
        # Two items, each R = 5.0 | No | 18.0 | reject
        result = aggregate_batch_risk([5.0, 5.0], chained=False)
        self.assertEqual(result["abr"], 18.0)
        self.assertEqual(result["outcome"], "reject")

    def test_r_5_plus_r_4_not_chained(self):
        # One item R = 5.0 + one item R = 4.0 | No | 13.0 | near_ceiling
        result = aggregate_batch_risk([5.0, 4.0], chained=False)
        self.assertEqual(result["abr"], 13.0)
        self.assertEqual(result["outcome"], "near_ceiling")

    def test_r_5_plus_r_4_chained(self):
        # One item R = 5.0 + one item R = 4.0 | Yes | 19.5 | reject (13.0 x 1.5)
        result = aggregate_batch_risk([5.0, 4.0], chained=True)
        self.assertEqual(result["abr"], 19.5)
        self.assertEqual(result["outcome"], "reject")

    def test_three_items_r_3_chained(self):
        # Three items, R = 3.0 each, chained | Yes | 4.5 | ok (3 x 1.0 x 1.5)
        result = aggregate_batch_risk([3.0, 3.0, 3.0], chained=True)
        self.assertEqual(result["abr"], 4.5)
        self.assertEqual(result["outcome"], "ok")

if __name__ == '__main__':
    unittest.main()
