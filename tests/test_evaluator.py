import unittest

from src.evaluator import (
    build_advisor_prompt,
    estimate_api_cost,
    estimate_token_usage,
    parse_advice_sections,
)


class EvaluatorTests(unittest.TestCase):
    def test_build_advisor_prompt_handles_empty_context(self):
        prompt = build_advisor_prompt(
            {
                "stats": {
                    "total_experiments": 0,
                    "avg_score": None,
                    "version_count": 0,
                    "model_scores": [],
                    "scene_counts": [],
                    "tag_counts": [],
                },
                "low_samples": [],
            }
        )

        self.assertIn("评测数据", prompt)
        self.assertIn("暂无低分样本", prompt)

    def test_parse_advice_sections_extracts_known_headings(self):
        sections = parse_advice_sections(
            "## Prompt 优化建议\nA\n## RAG 检索优化建议\nB\n## 产品体验优化建议\nC"
        )

        self.assertEqual(sections["prompt"], "A")
        self.assertEqual(sections["rag"], "B")
        self.assertEqual(sections["product"], "C")

    def test_estimation_helpers_do_not_raise(self):
        self.assertGreaterEqual(estimate_token_usage("hello", "gpt-4o-mini"), 1)
        self.assertGreaterEqual(estimate_api_cost("gpt-4o-mini", 10, 20), 0)


if __name__ == "__main__":
    unittest.main()
