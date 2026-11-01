import unittest
from caretrace.compare import compare
from caretrace.metrics import score_encounter


class ComparisonTests(unittest.TestCase):
    def test_paired_bootstrap_is_repeatable_and_requires_same_encounters(self):
        gold = [{"order_type": "lab", "description": "blood test", "provenance": [1]}]
        predicted = [{"order_type": "lab", "description": "blood test", "provenance": [1], "evidence_status": "linked"}]
        a = [{"id": "one", "counts": score_encounter(gold, [])}]
        b = [{"id": "one", "counts": score_encounter(gold, predicted)}]
        self.assertEqual(compare(a, b, samples=10), compare(a, b, samples=10))
        self.assertEqual(compare(a, b, samples=10)["bootstrap_95pct_interval"], [1.0, 1.0])
        with self.assertRaises(ValueError):
            compare(a, [{"id": "different", "counts": b[0]["counts"]}], samples=10)


if __name__ == "__main__":
    unittest.main()
