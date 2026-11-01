import unittest
from caretrace.contracts import parse_turns
from caretrace.extractive import ExtractiveEngine


class ExtractiveTests(unittest.TestCase):
    def test_every_description_is_an_exact_source_span(self):
        turns = parse_turns("Patient: I stopped the tablets.\nDoctor: We'll order a CBC. Please prescribe aspirin 2.5 mg daily.")
        result = ExtractiveEngine().extract(turns)
        self.assertEqual([item["order_type"] for item in result], ["lab", "medication"])
        for item in result:
            span = item["source_span"]
            source = next(turn.text for turn in turns if turn.id == span["turn_id"])
            self.assertEqual(source[span["start"]:span["end"]], item["description"])
        self.assertIn("2.5", result[1]["description"])

    def test_negation_history_and_patient_speech_do_not_create_orders(self):
        turns = parse_turns("Patient: Can you order an MRI?\nDoctor: Do not order an MRI. We previously used to prescribe tablets. Continue exercise.")
        self.assertEqual(ExtractiveEngine().extract(turns), [])

    def test_clinician_stop_is_an_action_and_negation_is_clause_local(self):
        turns = parse_turns("Doctor: No pain today. Order a blood test. Stop aspirin 5 mg daily.")
        result = ExtractiveEngine().extract(turns)
        self.assertEqual([item["order_type"] for item in result], ["lab", "medication"])
        self.assertTrue(result[1]["description"].startswith("Stop"))


if __name__ == "__main__":
    unittest.main()
