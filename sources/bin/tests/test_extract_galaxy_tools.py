import json
import os
import tempfile
import unittest
from typing import (
    Any,
    Dict,
    List,
    Union,
)
from unittest.mock import (
    MagicMock,
    Mock,
    patch,
)

import pandas as pd
import shared
from extract_galaxy_tools import (
    add_tutorial_ids_to_tools,
    add_workflow_ids_to_tools,
    aggregate_tool_stats,
    get_all_installed_tool_ids_on_server,
    get_github_repo,
    get_last_url_position,
    get_suite_ID_fallback,
    get_tool_github_repositories,
    get_tool_stats_from_stats_file,
    STATS_SUM,
)
from github import Github
from requests import HTTPError

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
GALAX_TOOLS_API_PATH = os.path.join(SCRIPT_DIR, "test-data", "galaxy_api_tool_mock.json")

TEST_TOOL_PATH = os.path.join(SCRIPT_DIR, "test-data", "test_tools.json")
TEST_WORKFLOW_PATH = os.path.join(SCRIPT_DIR, "test-data", "test_workflows.json")


class TestGetToolStatsFromStatsFile(unittest.TestCase):

    def setUp(self) -> None:
        # Sample dataframe mocking stats data
        self.df = pd.DataFrame(
            {
                "tool_name": [
                    "toolshed.g2.bx.psu.edu/repos/iuc/snpsift/snpSift_filter",
                    "toolshed.g2.bx.psu.edu/repos/iuc/snpsift/snpSift_filter",
                    "toolshed.g2.bx.psu.edu/repos/iuc/freebayes/freebayes",
                    "toolshed.g2.bx.psu.edu/repos/iuc/freebayes/freebayes",
                ],
                "count": [5, 10, 20, 25],
            }
        )

    def test_sum_mode(self) -> None:
        tool_ids: List[str] = ["snpSift_filter", "freebayes"]
        result: int = get_tool_stats_from_stats_file(self.df, tool_ids, mode="sum")
        self.assertEqual(result, 60)  # 15 + 45

    def test_max_mode(self) -> None:
        tool_ids: List[str] = ["snpSift_filter", "freebayes"]
        result: int = get_tool_stats_from_stats_file(self.df, tool_ids, mode="max")
        self.assertEqual(result, 45)  # max(15, 45)

    def test_tool_not_present(self) -> None:
        tool_ids: List[str] = ["nonexistent"]
        result: int = get_tool_stats_from_stats_file(self.df, tool_ids, mode="sum")
        self.assertEqual(result, 0)


class TestAggregateToolStats(unittest.TestCase):
    def test_basic_aggregation(self) -> None:
        tool: Dict[str, Union[int, float]] = {
            "Suite users (usegalaxy.eu)": 4130,
            "Suite users (last 5 years) (usegalaxy.eu)": 4097,
            "Suite users (usegalaxy.org)": 2915,
            "Suite users (last 5 years) (usegalaxy.org)": 2915,
            "Suite runs (usegalaxy.eu)": 622353,
            "Suite runs (last 5 years) (usegalaxy.eu)": 619817,
            "Suite runs (usegalaxy.org)": 320454,
            "Suite runs (last 5 years) (usegalaxy.org)": 320454,
        }

        result: Dict[str, Union[int, float]] = aggregate_tool_stats(tool.copy(), STATS_SUM)

        expected_users_max: int = 4130 + 2915
        self.assertEqual(result["Suite users on main servers"], expected_users_max)

        expected_users_5y_max: int = 4097 + 2915
        self.assertEqual(result["Suite users (last 5 years) on main servers"], expected_users_5y_max)

        expected_runs_sum: int = 622353 + 320454
        self.assertEqual(result["Suite runs on main servers"], expected_runs_sum)

        expected_runs_5y_sum: int = 619817 + 320454
        self.assertEqual(result["Suite runs (last 5 years) on main servers"], expected_runs_5y_sum)


class TestAddTutorialIdsToTools(unittest.TestCase):

    def setUp(self) -> None:
        # Sample tools data
        self.tools: List[Dict[str, Any]] = [
            {"Tool IDs": ["taxonomy_krona_chart"], "name": "Krona"},
            {"Tool IDs": ["humann2"], "name": "HUMAnN2"},
            {"Tool IDs": ["non_matching_tool"], "name": "UnknownTool"},
        ]

        # Sample tutorials JSON (as a list)
        self.tutorials = [
            {"id": "microbiome/introduction", "short_tools": ["taxonomy_krona_chart", "humann2"]},
            {"id": "metagenomics/analysis", "short_tools": ["humann2"]},
        ]

        # Write tutorial data to a temp file
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json")
        json.dump(self.tutorials, self.temp_file)
        self.temp_file.close()
        self.tutorial_path = self.temp_file.name

    def tearDown(self) -> None:
        os.remove(self.tutorial_path)

    def test_add_tutorial_ids_to_tools(self) -> None:
        updated_tools = add_tutorial_ids_to_tools(self.tools, self.tutorial_path)

        expected = {
            "taxonomy_krona_chart": ["microbiome/introduction"],
            "humann2": ["microbiome/introduction", "metagenomics/analysis"],
            "non_matching_tool": [],
        }

        for tool in updated_tools:
            tool_id = tool["Tool IDs"][0]
            self.assertEqual(sorted(tool["Related Tutorials"]), sorted(expected[tool_id]))


class TestAddWorkflowIdsToTools(unittest.TestCase):

    def setUp(self) -> None:
        self.tools = shared.load_json(TEST_TOOL_PATH)

    def test_adds_related_workflows(self) -> None:
        result: List[Dict[str, Any]] = add_workflow_ids_to_tools(self.tools, TEST_WORKFLOW_PATH)
        # check for some tools if the correct workflows are added
        expected_mapping: Dict[str, List] = {
            "aldex2": [],
            "shovill": ["https://usegalaxy.eu/published/workflow?id=7e48134082dab0a3"],
            "fastp": [
                "https://usegalaxy.eu/published/workflow?id=2fa2f67603772413",
                "https://usegalaxy.eu/published/workflow?id=96c61a584cb2e5e9",
                "https://usegalaxy.eu/published/workflow?id=aff44f1665a14e23",
                "https://usegalaxy.eu/published/workflow?id=b14845359b702444",
                "https://usegalaxy.eu/published/workflow?id=b426e137396acb14",
                "https://usegalaxy.eu/published/workflow?id=deec04097a871646",
                "https://workflowhub.eu/workflows/1103?version=3",
                "https://workflowhub.eu/workflows/1104?version=2",
            ],
        }
        for res in result:
            if res["Suite ID"] in expected_mapping:
                self.assertEqual(sorted(expected_mapping[res["Suite ID"]]), sorted(res["Related Workflows"]))


class TestGetSuiteIDFallback(unittest.TestCase):

    def test_suite_id_already_set(self) -> None:
        metadata: Dict[str, Any] = {"Suite ID": "existing_suite", "bio.tool ID": "SomeTool"}
        tool = Mock()
        tool.path = "some/path/to/tool_folder"
        result = get_suite_ID_fallback(metadata, tool)
        self.assertEqual(result["Suite ID"], "existing_suite")

    def test_suite_id_none_bio_tool_id_present(self) -> None:
        metadata: Dict[str, Any] = {"Suite ID": None, "bio.tool ID": "MyToolSuite"}
        tool = Mock()
        tool.path = "some/path/to/tool_folder"
        result = get_suite_ID_fallback(metadata, tool)
        self.assertEqual(result["Suite ID"], "mytoolsuite")

    def test_suite_id_and_bio_tool_id_none(self) -> None:
        metadata: Dict[str, Any] = {"Suite ID": None, "bio.tool ID": None}
        tool = Mock()
        tool.path = "toolshed/repos/dev/suite_xyz"
        result = get_suite_ID_fallback(metadata, tool)
        self.assertEqual(result["Suite ID"], "suite_xyz")


class TestGetToolGithubRepositories(unittest.TestCase):
    """
    Unit tests for the get_tool_github_repositories function.
    """

    def setUp(self) -> None:
        """
        Shared mock setup for GitHub repo hierarchy and content.
        """
        # Mocked file content returned by get_string_content
        self.mock_repositories_content: str = (
            "https://github.com/genouest/galaxy-tools\n"
            "https://github.com/galaxyproject/galaxy\n"
            "https://github.com/TGAC/earlham-galaxytools\n"
        )

        # Mock GitHub repo object
        self.mock_content: Any = MagicMock()
        self.mock_repo: Any = MagicMock()
        self.mock_repo.get_contents.return_value = self.mock_content

        # Mock GitHub user
        self.mock_user: Any = MagicMock()
        self.mock_user.get_repo.return_value = self.mock_repo

        # Mock GitHub instance
        self.mock_g: Any = MagicMock()
        self.mock_g.get_user.return_value = self.mock_user

    @patch("extract_galaxy_tools.get_string_content")
    def test_get_tool_github_repositories(self, mock_get_string_content: MagicMock) -> None:
        """
        Test that get_tool_github_repositories returns a list of repository URLs
        when run_test=False and add_extra_repositories=False.
        """
        mock_get_string_content.return_value = self.mock_repositories_content

        result: list[str] = get_tool_github_repositories(
            g=self.mock_g,
            repository_list="repositories01.list",
            run_test=False,
            add_extra_repositories=False,
        )

        self.assertEqual(
            result,
            [
                "https://github.com/genouest/galaxy-tools",
                "https://github.com/galaxyproject/galaxy",
                "https://github.com/TGAC/earlham-galaxytools",
            ],
        )

        self.mock_repo.get_contents.assert_called_once_with("repositories01.list")
        mock_get_string_content.assert_called_once_with(self.mock_content)

    @patch("extract_galaxy_tools.configs", {"extra-repositories": ["https://github.com/extra/repo"]})
    @patch("extract_galaxy_tools.get_string_content")
    def test_get_tool_github_repositories_with_extra(self, mock_get_string_content: MagicMock) -> None:
        """
        Test that get_tool_github_repositories appends extra repositories from config
        when add_extra_repositories=True.
        """
        mock_get_string_content.return_value = self.mock_repositories_content

        result: list[str] = get_tool_github_repositories(
            g=self.mock_g,
            repository_list="repositories01.list",
            run_test=False,
            add_extra_repositories=True,
        )

        self.assertEqual(
            result,
            [
                "https://github.com/genouest/galaxy-tools",
                "https://github.com/galaxyproject/galaxy",
                "https://github.com/TGAC/earlham-galaxytools",
                "https://github.com/extra/repo",
            ],
        )


class TestGetGithubRepo(unittest.TestCase):
    """
    Unit tests for the get_github_repo function.
    """

    def test_valid_repo_url(self) -> None:
        """
        Test that a valid GitHub URL returns the correct mocked repository object.
        """
        mock_repo = MagicMock()
        mock_user = MagicMock()
        mock_user.get_repo.return_value = mock_repo

        mock_g = MagicMock(spec=Github)
        mock_g.get_user.return_value = mock_user

        url = "https://github.com/galaxyproject/galaxy"
        result = get_github_repo(url, mock_g)

        self.assertEqual(result, mock_repo)
        mock_g.get_user.assert_called_once_with("galaxyproject")
        mock_user.get_repo.assert_called_once_with("galaxy")

    def test_url_with_trailing_slash(self) -> None:
        """
        Test that URLs ending with a slash are handled correctly.
        """
        mock_repo = MagicMock()
        mock_user = MagicMock()
        mock_user.get_repo.return_value = mock_repo

        mock_g = MagicMock()
        mock_g.get_user.return_value = mock_user

        url = "https://github.com/usegalaxy-eu/tools-iuc/"
        result = get_github_repo(url, mock_g)

        self.assertEqual(result, mock_repo)
        mock_g.get_user.assert_called_once_with("usegalaxy-eu")
        mock_user.get_repo.assert_called_once_with("tools-iuc")

    def test_url_with_dot_git_suffix(self) -> None:
        """
        Test that URLs ending with .git are cleaned and handled.
        """
        mock_repo = MagicMock()
        mock_user = MagicMock()
        mock_user.get_repo.return_value = mock_repo

        mock_g = MagicMock()
        mock_g.get_user.return_value = mock_user

        url = "https://github.com/usegalaxy-eu/tools-iuc.git"
        result = get_github_repo(url, mock_g)

        self.assertEqual(result, mock_repo)
        mock_g.get_user.assert_called_once_with("usegalaxy-eu")
        mock_user.get_repo.assert_called_once_with("tools-iuc")

    def test_invalid_url(self) -> None:
        """
        Test that a ValueError is raised when the URL does not start with the expected prefix.
        """
        mock_g = MagicMock()

        with self.assertRaises(ValueError):
            get_github_repo("http://example.com/repo", mock_g)


class TestGetLastUrlPosition(unittest.TestCase):
    """
    Unit tests for the get_last_url_position function.
    """

    def test_toolshed_url(self) -> None:
        """
        Should return the last component of a toolshed-style ID.
        """
        tool_id = "toolshed.g2.bx.psu.edu/repos/iuc/snpsift/snpSift_filter"
        expected = "snpSift_filter"
        self.assertEqual(get_last_url_position(tool_id), expected)

    def test_no_slashes(self) -> None:
        """
        Should return the input unchanged if there's no '/'.
        """
        tool_id = "fastqc"
        expected = "fastqc"
        self.assertEqual(get_last_url_position(tool_id), expected)


class TestGetAllInstalledToolIdsOnServer(unittest.TestCase):
    """
    Unit tests for get_all_installed_tool_ids_on_server.
    """

    def setUp(self) -> None:
        # Clear the cache so each test starts fresh
        get_all_installed_tool_ids_on_server.cache_clear()

        # Load the JSON Galaxy API mock data
        with open(GALAX_TOOLS_API_PATH, encoding="utf-8") as f:
            self.sample_json = json.load(f)

    @patch("extract_galaxy_tools.requests.get")
    def test_successful_fetch(self, mock_get: MagicMock) -> None:
        """When the server returns valid JSON, we get back the list of IDs."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = self.sample_json
        mock_get.return_value = mock_resp

        ids1 = get_all_installed_tool_ids_on_server("https://usegalaxy.org")
        ids2 = get_all_installed_tool_ids_on_server("https://usegalaxy.org/")

        expected = ["upload1", "ds_seek_test"]
        self.assertEqual(ids1, expected)
        self.assertEqual(ids2, expected)

        mock_get.assert_called_with("https://usegalaxy.org/api/tools", params={"in_panel": False})

    @patch("extract_galaxy_tools.requests.get")
    def test_raise_for_status_failure(self, mock_get: MagicMock) -> None:
        """If raise_for_status raises, return an empty list."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = HTTPError("Bad request")
        mock_get.return_value = mock_resp

        result = get_all_installed_tool_ids_on_server("https://usegalaxy.org")
        self.assertEqual(result, [])

    @patch("extract_galaxy_tools.requests.get")
    def test_json_parse_failure(self, mock_get: MagicMock) -> None:
        """If .json() raises, return an empty list."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_resp

        result = get_all_installed_tool_ids_on_server("https://usegalaxy.org")
        self.assertEqual(result, [])
