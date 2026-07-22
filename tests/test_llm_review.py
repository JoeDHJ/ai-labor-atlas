import unittest

from ai_labor_atlas.llm_review import (
    LLMConfig,
    LLMNotConfiguredError,
    LLMReviewClient,
    _json_object,
)


class FakeReviewClient(LLMReviewClient):
    def __init__(self, response):
        super().__init__(LLMConfig("test-key", "https://example.test/v1", "test-model"))
        self.response = response

    def complete_json(self, system_prompt, user_prompt):
        return self.response


class LLMReviewTests(unittest.TestCase):
    def test_json_object_accepts_code_fence(self):
        self.assertEqual(
            _json_object('```json\n{"decision":"review"}\n```'), {"decision": "review"}
        )

    def test_disabled_client_fails_closed(self):
        client = LLMReviewClient(LLMConfig("", "https://example.test/v1", ""))
        with self.assertRaises(LLMNotConfiguredError):
            client.complete_json("system", "user")

    def test_occupation_review_cannot_select_an_unlisted_soc_code(self):
        client = FakeReviewClient(
            {
                "decision": "accept",
                "confidence": 1.4,
                "selected_soc_code": "99-9999",
                "rationale": "unsupported selection",
                "evidence": "title only",
            }
        )
        result = client.review_occupation(
            {"title": "Economist"}, [{"soc_2018_code": "19-3011"}]
        )
        self.assertEqual(result["decision"], "review")
        self.assertIsNone(result["selected_soc_code"])
        self.assertEqual(result["confidence"], 1.0)
        self.assertEqual(result["evidence"], ["title only"])


if __name__ == "__main__":
    unittest.main()
