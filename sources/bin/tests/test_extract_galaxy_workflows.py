import json
import os
import unittest
from typing import Dict
from unittest.mock import (
    MagicMock,
    patch,
)

from bin.extract_galaxy_workflows import Workflows

from bin import shared


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

        self.assertEqual(mock_get_request_json.call_count, 3)  # Adjust based on the expected number of calls

        # check if edam terms are transferred from the tools to the workflow
        self.assertEqual(
            set(first_workflow.edam_operation), set(["Antimicrobial resistance prediction", "Genome assembly"])
        )


# Run the tests
if __name__ == "__main__":
    unittest.main()
