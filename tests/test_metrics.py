import unittest

from caretrace.metrics import aggregate, score_encounter, token_f1


class MetricsTests(unittest.TestCase):
    def test_one_gold_cannot_match_two_predictions(self):
        gold = [{"order_type": "lab", "description": "blood test", "provenance": [2, 4]}]
        pred = [{"order_type": "lab", "description": "blood test", "provenance": [2], "evidence_status": "linked"},
                {"order_type": "lab", "description": "blood test", "provenance": [4], "evidence_status": "linked"}]
        result = aggregate([score_encounter(gold, pred)])
        self.assertEqual((result["gold"], result["predicted"], result["matched"]), (1, 2, 1))
        self.assertEqual(result["reference_id_overlap_recall_diagnostic"], 0.5)

    def test_type_mismatch_is_not_matched(self):
        gold = [{"order_type": "lab", "description": "test", "provenance": [1]}]
        pred = [{"order_type": "imaging", "description": "test", "provenance": [1], "evidence_status": "linked"}]
        self.assertEqual(score_encounter(gold, pred)["matched"], 0)
        self.assertEqual(token_f1("", "anything"), 0)

    def test_invalid_reference_evidence_is_not_scored_as_ground_truth(self):
        gold = [{"order_type": "lab", "description": "blood test", "provenance": [-2, 5]}]
        pred = [{"order_type": "lab", "description": "blood test", "provenance": [5], "evidence_status": "linked"}]
        result = aggregate([score_encounter(gold, pred, valid_turns={1, 5})])
        self.assertEqual(result["matched"], 1)
        self.assertEqual(result["invalid_reference_evidence"], 1)
        self.assertIsNone(result["reference_id_overlap_recall_diagnostic"])

    def test_dose_disagreement_is_not_counted_as_a_match(self):
        gold = [{"order_type": "medication", "description": "drug 50 mg daily", "provenance": [1]}]
        pred = [{"order_type": "medication", "description": "drug 5 mg daily", "provenance": [1], "evidence_status": "linked"}]
        self.assertEqual(score_encounter(gold, pred)["matched"], 0)


if __name__ == "__main__":
    unittest.main()
