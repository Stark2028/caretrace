import unittest

from caretrace.contracts import decode_json, parse_enumerated, parse_turns, validate_orders
from caretrace.engine import OllamaEngine, RuleEngine
from unittest.mock import patch


class ContractTests(unittest.TestCase):
    def test_dataset_multiline_and_empty_turns_preserve_ids(self):
        turns = parse_enumerated("1 [doctor] First sentence\ncontinuation\n2 [patient]\n3 [doctor] Next")
        self.assertEqual([(t.id, t.text) for t in turns], [(1, "First sentence continuation"), (2, ""), (3, "Next")])

    def test_duplicate_ids_and_missing_speaker_are_rejected(self):
        for text in ("1 [doctor] First\n1 [patient] Second", "hello there"):
            with self.assertRaises(ValueError):
                parse_turns(text)
        with self.assertRaises(ValueError):
            parse_enumerated("1 [doctor] Hello\n2 [nurse] Unknown speaker")

    def test_unknown_or_missing_evidence_is_visible(self):
        turns = parse_turns("Doctor: Arrange a blood test.")
        orders = validate_orders({"orders": [
            {"order_type": "lab", "description": "blood test", "provenance": [12]},
            {"order_type": "lab", "description": "blood test", "provenance": []},
        ]}, turns)
        self.assertEqual([x["evidence_status"] for x in orders], ["invalid_turn", "missing"])

    def test_boolean_evidence_is_not_a_turn_id(self):
        with self.assertRaises(ValueError):
            validate_orders({"orders": [{"order_type": "lab", "description": "test", "provenance": [True]}]}, parse_turns("Doctor: Hi"))

    def test_rule_engine_does_not_turn_history_or_patient_speech_into_orders(self):
        turns = parse_turns("Patient: I stopped taking a tablet.\nDoctor: We will arrange a blood test.\nPatient: Can I schedule an MRI?\nDoctor: Do not order an MRI.")
        orders = RuleEngine().extract(turns)
        self.assertEqual(len(orders), 1)
        self.assertEqual((orders[0]["order_type"], orders[0]["provenance"]), ("lab", [2]))

    def test_json_fence_is_supported_but_extra_prose_fails(self):
        self.assertEqual(decode_json('```json\n{"orders": []}\n```'), {"orders": []})
        with self.assertRaises(ValueError):
            decode_json('Here are orders: {"orders": []}')

    def test_model_endpoint_cannot_be_remote(self):
        with patch.dict("os.environ", {"CARETRACE_OLLAMA_URL": "http://example.com:11434"}):
            with self.assertRaisesRegex(ValueError, "loopback"):
                OllamaEngine("qwen2.5:3b")


if __name__ == "__main__":
    unittest.main()
