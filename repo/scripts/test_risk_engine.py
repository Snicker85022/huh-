from risk_engine import score
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

if __name__ == '__main__':
    unittest.main()
