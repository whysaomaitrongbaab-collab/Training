#!/usr/bin/env python3
"""Tests for Destrier Lab Playground backend using standard unittest."""
import json
import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from server import app

client = TestClient(app)


class TestPlaygroundBackend(unittest.TestCase):

    def test_health_check(self):
        response = client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("version", data)

    def test_list_houses(self):
        response = client.get("/api/houses")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("houses", data)
        self.assertIsInstance(data["houses"], list)

    def test_list_prompts(self):
        response = client.get("/api/prompts")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("subtasks", data)
        self.assertIn("plan_beam", data["subtasks"])
        self.assertIn("gridline", data["subtasks"])

    def test_prompt_assembly(self):
        payload = {
            "subtask": "plan_beam",
            "custom_body": "## TEST PROMPT BODY",
            "include_common": True,
            "grid_master_text": "GRID MASTER (X1, X2)",
            "cv_hint_text": "CV Hint: Beam #1 at (100, 200)"
        }
        response = client.post("/api/prompt/assemble", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("prompt", data)
        self.assertIn("TEST PROMPT BODY", data["prompt"])
        self.assertIn("GRID MASTER (X1, X2)", data["prompt"])
        self.assertIn("CV Hint: Beam #1", data["prompt"])

    def test_defensive_salvage(self):
        truncated_json = '{"elements": [{"element_id": "B1", "span_m": 4.0}, {"element_id": "B2", "span_m":'
        response = client.post("/api/defensive/salvage", json={"raw_text": truncated_json})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["salvaged"])
        self.assertEqual(len(data["parsed"]["elements"]), 1)
        self.assertEqual(data["parsed"]["elements"][0]["element_id"], "B1")

    def test_contract_validator(self):
        valid_payload = {
            "pattern": "beam_plan",
            "elements": [
                {
                    "element_id": "2B1",
                    "element_type": "beam",
                    "grid_ref_start": "1",
                    "grid_ref_end": "2"
                }
            ]
        }
        response = client.post("/api/contract/validate", json={"doc": valid_payload})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["valid"])
        self.assertEqual(len(data["missing_fields"]), 0)

        invalid_payload = {
            "elements": [
                {
                    "id": "2B1"
                }
            ]
        }
        response2 = client.post("/api/contract/validate", json={"doc": invalid_payload})
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()
        self.assertFalse(data2["valid"])
        self.assertGreater(len(data2["warnings"]), 0)


if __name__ == "__main__":
    unittest.main()
