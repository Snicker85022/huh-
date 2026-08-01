from dispatch_design import check_dispatch_design
import unittest


class TestDispatchDesign(unittest.TestCase):
    """Spec 09: Dispatch design 4-row table."""

    def test_all_true_approved(self):
        # True True True True -> approved=True, failures=[]
        result = check_dispatch_design(True, True, True, True)
        self.assertTrue(result["approved"])
        self.assertEqual(result["failures"], [])

    def test_scope_false(self):
        # False True True True -> approved=False, failures=["scope"]
        result = check_dispatch_design(False, True, True, True)
        self.assertFalse(result["approved"])
        self.assertEqual(result["failures"], ["scope"])

    def test_sequencing_and_efficiency_false(self):
        # True False False True -> approved=False, failures=["sequencing", "efficiency"]
        result = check_dispatch_design(True, False, False, True)
        self.assertFalse(result["approved"])
        self.assertEqual(result["failures"], ["sequencing", "efficiency"])

    def test_ambiguity_false(self):
        # True True True False -> approved=False, failures=["ambiguity"]
        result = check_dispatch_design(True, True, True, False)
        self.assertFalse(result["approved"])
        self.assertEqual(result["failures"], ["ambiguity"])

    def test_unambiguous_defaults_true_for_harnessed(self):
        # unambiguous_ok defaults True (harnessed executors, spec 05): omitting
        # it must not fail the check
        result = check_dispatch_design(True, True, True)
        self.assertTrue(result["approved"])
        self.assertEqual(result["failures"], [])


if __name__ == '__main__':
    unittest.main()
