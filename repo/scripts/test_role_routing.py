from role_routing import route
import unittest


class TestRouteSubtypeSelection(unittest.TestCase):
    """Spec 09: Executor subtype selection (route(), per 03's tool_access)."""

    def test_aider(self):
        result = route([3.0], chained=False, tool_access="aider")
        self.assertEqual(result["executor_subtypes"], ["Executor-Aider"])

    def test_browser(self):
        result = route([3.0], chained=False, tool_access="browser")
        self.assertEqual(result["executor_subtypes"], ["Executor-Browser"])

    def test_both(self):
        result = route([3.0], chained=False, tool_access="both")
        self.assertEqual(result["executor_subtypes"], ["Executor-Aider", "Executor-Browser"])

    def test_invalid_tool_access_raises_before_abr(self):
        # "gui" (or any value outside aider/browser/both) raises ValueError,
        # checked before ABR is even computed
        with self.assertRaises(ValueError):
            route([3.0], chained=False, tool_access="gui")


class TestRouteCombinedVectors(unittest.TestCase):
    """Spec 09: combined route vectors (ABR + subtype + DA)."""

    def test_single_band2_aider(self):
        # [3.0] | False | aider -> proceed=True, da_required=True (Band 2),
        # executor_subtypes=["Executor-Aider"], abr=1.0, outcome="ok"
        result = route([3.0], chained=False, tool_access="aider")
        self.assertTrue(result["proceed"])
        self.assertTrue(result["da_required"])
        self.assertEqual(result["executor_subtypes"], ["Executor-Aider"])
        self.assertEqual(result["abr"], 1.0)
        self.assertEqual(result["outcome"], "ok")

    def test_two_r5_both_reject_no_subtypes_key(self):
        # [5.0, 5.0] | False | both -> proceed=False,
        # reason="abr_ceiling_exceeded"; executor_subtypes must NOT appear in
        # the response (returns before reaching that line) - check absence,
        # not empty/null
        result = route([5.0, 5.0], chained=False, tool_access="both")
        self.assertFalse(result["proceed"])
        self.assertEqual(result["reason"], "abr_ceiling_exceeded")
        self.assertNotIn("executor_subtypes", result)

    def test_r5_plus_r4_aider_near_ceiling(self):
        # [5.0, 4.0] | False | aider -> proceed=True, da_required=True,
        # abr=13.0, outcome="near_ceiling"
        result = route([5.0, 4.0], chained=False, tool_access="aider")
        self.assertTrue(result["proceed"])
        self.assertTrue(result["da_required"])
        self.assertEqual(result["abr"], 13.0)
        self.assertEqual(result["outcome"], "near_ceiling")

    def test_15x_2_9_near_ceiling_only_branch(self):
        # [2.9] * 15 | False | aider -> proceed=True, da_required=True (every
        # item is Band 3 - near_ceiling-only branch; fails if the near_ceiling
        # OR is missing/misplaced), executor_subtypes=["Executor-Aider"],
        # abr=12.15, outcome="near_ceiling"
        result = route([2.9] * 15, chained=False, tool_access="aider")
        self.assertTrue(result["proceed"])
        self.assertTrue(result["da_required"])
        self.assertEqual(result["executor_subtypes"], ["Executor-Aider"])
        self.assertAlmostEqual(result["abr"], 12.15, places=4)  # float sum; oracle 12.15
        self.assertEqual(result["outcome"], "near_ceiling")


if __name__ == '__main__':
    unittest.main()
