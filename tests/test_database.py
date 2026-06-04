import tempfile
import unittest
from pathlib import Path

import src.database as database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data_dir = database.DATA_DIR
        self.old_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tmp.name)
        database.DB_PATH = Path(self.tmp.name) / "workbench.db"

    def tearDown(self):
        database.DATA_DIR = self.old_data_dir
        database.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    def test_init_db_creates_database_and_empty_stats(self):
        database.init_db()

        self.assertTrue(database.DB_PATH.exists())
        stats = database.get_dashboard_stats()
        self.assertEqual(stats["total_experiments"], 0)

    def test_save_functions_update_dashboard_stats(self):
        prompt_id = database.save_prompt_experiment(
            scene="客服问答",
            system_prompt="sys",
            user_prompt="hi",
            model="gpt-4o-mini",
            temperature=0.7,
            max_tokens=100,
            response="answer",
            latency_ms=12,
            input_tokens=10,
            output_tokens=20,
            cost=0.001,
            human_score=4,
        )
        compare_id = database.save_model_comparison(
            "question",
            [{"model": "gpt-4o-mini", "response": "answer", "human_score": 3}],
        )
        rag_id = database.save_rag_evaluation(
            "doc.txt",
            "question",
            "answer",
            [{"text": "source"}],
            ["引用错误"],
            2,
        )
        feedback_id = database.save_user_feedback(
            source_type="rag",
            source_id=rag_id,
            score=2,
            tags=["引用错误"],
            comment="needs source",
        )

        stats = database.get_dashboard_stats()
        self.assertGreater(prompt_id, 0)
        self.assertGreater(compare_id, 0)
        self.assertGreater(rag_id, 0)
        self.assertGreater(feedback_id, 0)
        self.assertEqual(stats["total_experiments"], 3)
        self.assertEqual(stats["avg_score"], 3.0)
        self.assertTrue(stats["tag_counts"])

    def test_demo_seed_is_idempotent(self):
        first = database.seed_demo_data_if_empty()
        second = database.seed_demo_data_if_empty()
        stats = database.get_dashboard_stats()

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertGreater(stats["total_experiments"], 0)

    def test_schema_migration_adds_generation_columns(self):
        database.init_db()
        with database.get_connection() as conn:
            for table, column in [
                ("model_comparisons", "temperature"),
                ("model_comparisons", "max_tokens"),
                ("rag_evaluations", "temperature"),
                ("rag_evaluations", "max_tokens"),
            ]:
                self.assertTrue(database._column_exists(conn, table, column))

        compare_id = database.save_model_comparison(
            "migration test",
            [{"model": "gpt-4o-mini", "response": "ok"}],
            temperature=0.5,
            max_tokens=512,
        )
        rag_id = database.save_rag_evaluation(
            "doc.txt",
            "q",
            "a",
            [],
            [],
            3,
            temperature=0.8,
            max_tokens=2048,
        )
        self.assertGreater(compare_id, 0)
        self.assertGreater(rag_id, 0)


if __name__ == "__main__":
    unittest.main()
