import json
import os
import sys
import unittest
from typing import Dict
from unittest.mock import (
    MagicMock,
    patch,
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import shared
from extract_galaxy_workflows import Workflows


class TestAddWorkflowsFromWorkflowHub(unittest.TestCase):

    def setUp(self) -> None:
        """Set up the test environment and prepare mock data."""
        # Get the directory where the script is located
        self.script_dir = os.path.dirname(os.path.realpath(__file__))

        # Construct the path to the JSON file (relative to the script's location)
        json_file_path = os.path.join(self.script_dir, "test-data", "workflowhub_api_mock.json")

        # Open and load the JSON file
        with open(json_file_path) as file:
            self.mock_responses = json.load(file)

        # Define the side effect function
        def mock_side_effect(url: str, headers: Dict[str, str]) -> Dict:
            if url == "https://workflowhub.eu/workflows?filter[workflow_type]=galaxy":
                return self.mock_responses[0]
            elif url == "https://workflowhub.eu/workflows/1189":
                return self.mock_responses[1]
            elif url == "https://workflowhub.eu/workflows/1190":
                return self.mock_responses[2]
            else:
                return {"data": []}  # Default empty response for any other URL

        self.mock_side_effect = mock_side_effect  # Store for reuse in tests

        # Construct the path to the JSON file (relative to the script's location)
        self.test_tools_file_path = os.path.join(self.script_dir, "test-data", "test_tools.json")

    @patch("shared.get_request_json")
    def test_add_workflows_from_workflowhub(self, mock_get_request_json: MagicMock) -> None:

        # Mock the first call to get_request_json to return the mock list response
        mock_get_request_json.side_effect = self.mock_side_effect

        # Create the Workflows instance and invoke the method
        workflows_instance = Workflows(test=True)  # Set test=True to limit data processed
        workflows_instance.tools = shared.read_suite_per_tool_id(self.test_tools_file_path)
        workflows_instance.add_workflows_from_workflowhub()

        # Assert that the correct number of workflows were added
        self.assertEqual(len(workflows_instance.workflows), 2)  # Should have added all 6 workflows

        # Check details of the first added workflow as an example
        first_workflow = workflows_instance.workflows[0]
        self.assertEqual(first_workflow.id, "1189")
        self.assertEqual(first_workflow.name, "AMR-Pathfinder")
        self.assertEqual(first_workflow.link, "https://workflowhub.eu/workflows/1189?version=1")

        # Optionally check that the mock was called with the expected URLs
        mock_get_request_json.assert_any_call(
            "https://workflowhub.eu/workflows?filter[workflow_type]=galaxy", {"Accept": "application/json"}
        )
        mock_get_request_json.assert_any_call("https://workflowhub.eu/workflows/1189", {"Accept": "application/json"})
        mock_get_request_json.assert_any_call("https://workflowhub.eu/workflows/1190", {"Accept": "application/json"})

        self.assertEqual(mock_get_request_json.call_count, 7)  # Adjust based on the expected number of calls

        # check if edam terms are transferred from the tools to the workflow
        self.assertEqual(
            set(first_workflow.edam_operation), set(["Antimicrobial resistance prediction", "Genome assembly"])
        )


# Run the tests
if __name__ == "__main__":
    unittest.main()


class TestSkipBrokenWorkflows(unittest.TestCase):
    """A single workflow failing on the server API should not crash the whole extraction."""

    def setUp(self) -> None:
        self.wfs = Workflows()
        self.wfs.tools = {}

    @patch("extract_galaxy_workflows.Workflow.init_from_search")
    @patch("extract_galaxy_workflows.shared.get_request_json")
    def test_public_server_broken_workflow_is_skipped(self, mock_get: MagicMock, mock_init: MagicMock) -> None:
        listing = [
            {"id": wid, "published": True, "importable": True, "deleted": False, "hidden": False}
            for wid in ["ok1", "broken", "ok2"]
        ]

        def side_effect(url: str, headers: Dict[str, str]) -> Dict:
            if url.endswith("/api/workflows/"):
                return listing  # type: ignore[return-value]
            if url.endswith("/broken"):
                raise ConnectionError("Connection aborted after multiple retries")
            return {"id": url.rsplit("/", 1)[-1]}

        mock_get.side_effect = side_effect
        self.wfs.add_workflows_from_a_server("https://usegalaxy.example")
        self.assertEqual(len(self.wfs.workflows), 2)
        self.assertEqual([url for url, _ in self.wfs.skipped], ["https://usegalaxy.example/api/workflows/broken"])
        self.assertEqual([c.kwargs["wf"]["id"] for c in mock_init.call_args_list], ["ok1", "ok2"])

    @patch("extract_galaxy_workflows.Workflow.init_from_search")
    @patch("extract_galaxy_workflows.shared.get_request_json")
    def test_public_server_request_exit_is_skipped(self, mock_get: MagicMock, mock_init: MagicMock) -> None:
        listing = [{"id": "broken", "published": True, "importable": True, "deleted": False, "hidden": False}]

        def side_effect(url: str, headers: Dict[str, str]) -> Dict:
            if url.endswith("/api/workflows/"):
                return listing  # type: ignore[return-value]
            raise SystemExit("Request failed: 500 Server Error")

        mock_get.side_effect = side_effect
        self.wfs.add_workflows_from_a_server("https://usegalaxy.example")
        self.assertEqual(self.wfs.workflows, [])

    @patch("extract_galaxy_workflows.Workflow.init_from_search")
    @patch("extract_galaxy_workflows.shared.get_request_json")
    def test_workflowhub_broken_workflow_is_skipped(self, mock_get: MagicMock, mock_init: MagicMock) -> None:
        listing = {"data": [{"links": {"self": f"/workflows/{i}"}} for i in [1, 2, 3]]}

        def side_effect(url: str, headers: Dict[str, str]) -> Dict:
            if "filter[workflow_type]" in url:
                return listing
            if url.endswith("/workflows/2"):
                raise ConnectionError("Connection aborted after multiple retries")
            return {"data": {"id": url.rsplit("/", 1)[-1]}}

        mock_get.side_effect = side_effect
        self.wfs.add_workflows_from_workflowhub()
        self.assertEqual(len(self.wfs.workflows), 2)


class TestReportSkippedWorkflows(unittest.TestCase):
    """Skipped workflows are reported on the GitHub Actions run, and too many skipped workflows fail the run."""

    def setUp(self) -> None:
        self.wfs = Workflows()
        self.wfs.skipped = [("https://usegalaxy.example/api/workflows/broken", "Connection aborted")]

    def test_nothing_skipped(self) -> None:
        self.assertTrue(Workflows().report_skipped(max_skipped=0))

    def test_under_threshold_writes_summary(self) -> None:
        import tempfile

        with tempfile.NamedTemporaryFile("r", suffix=".md") as summary:
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": summary.name}):
                self.assertTrue(self.wfs.report_skipped(max_skipped=10))
            content = summary.read()
        self.assertIn("1 workflow(s) could not be fetched", content)
        self.assertIn("https://usegalaxy.example/api/workflows/broken", content)

    def test_over_threshold_fails(self) -> None:
        self.wfs.skipped = self.wfs.skipped * 3
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_STEP_SUMMARY", None)
            self.assertFalse(self.wfs.report_skipped(max_skipped=2))
