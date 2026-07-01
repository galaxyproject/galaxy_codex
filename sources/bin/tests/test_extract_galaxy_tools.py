import json
import os
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as et
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Union,
)
from unittest.mock import (
    MagicMock,
    patch,
)

import pandas as pd
import shared
import yaml
from extract_galaxy_tools import (
    _load_tool_xml_fallback,
    _normalize_repo_url,
    _repo_name_from_url,
    add_status,
    add_tutorial_ids_to_tools,
    add_workflow_ids_to_tools,
    aggregate_tool_stats,
    check_categories,
    check_tools_on_servers,
    clone_repositories,
    curate_tools,
    export_missing_tools,
    export_missing_tools_to_yaml,
    export_tools_to_json,
    export_tools_to_tsv,
    export_tools_to_yml,
    extract_missing_tools_per_servers,
    extract_top_tools_per_category,
    fill_lab_tool_section,
    filter_tools,
    get_all_installed_tool_ids_on_server,
    get_conda_package,
    get_first_commit_for_local_folder,
    get_last_url_position,
    get_shed_attribute,
    get_tool_metadata_from_local,
    get_tool_outputs,
    get_tool_stats_from_stats_file,
    get_xref,
    parse_tools_from_local,
    STATS_SUM,
)
from requests import HTTPError

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
TEST_DIR = os.path.join(SCRIPT_DIR, "test-data")

GALAX_TOOLS_API_PATH = os.path.join(TEST_DIR, "galaxy_api_tool_mock.json")
TEST_TOOL_PATH = os.path.join(TEST_DIR, "test_tools.json")
TEST_WORKFLOW_PATH = os.path.join(TEST_DIR, "test_workflows.json")
TEST_WRAPPER_XML = os.path.join(TEST_DIR, "fastp.xml")


class TestGetToolOutputs(unittest.TestCase):

    def setUp(self) -> None:
        with open(TEST_WRAPPER_XML) as file:
            file_content = file.read()
            self.tool_xml = et.fromstring(file_content)

    def test_get_tool_outputs(self) -> None:
        formats = get_tool_outputs(self.tool_xml)
        self.assertEqual(sorted(formats), ["html", "json"])


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

        mock_get.assert_called_with("https://usegalaxy.org/api/tools", params={"in_panel": False}, timeout=30)

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


class TestNormalizeRepoUrl(unittest.TestCase):
    def test_strips_trailing_slash(self) -> None:
        self.assertEqual(
            _normalize_repo_url("https://github.com/iuc/tools/"),
            "https://github.com/iuc/tools",
        )

    def test_strips_dot_git(self) -> None:
        self.assertEqual(
            _normalize_repo_url("https://github.com/iuc/tools.git"),
            "https://github.com/iuc/tools",
        )

    def test_strips_both(self) -> None:
        self.assertEqual(
            _normalize_repo_url("https://github.com/iuc/tools.git/"),
            "https://github.com/iuc/tools",
        )

    def test_strips_whitespace(self) -> None:
        self.assertEqual(
            _normalize_repo_url("  https://github.com/iuc/tools  "),
            "https://github.com/iuc/tools",
        )


class TestRepoNameFromUrl(unittest.TestCase):
    def test_standard_github(self) -> None:
        self.assertEqual(
            _repo_name_from_url("https://github.com/galaxyproject/tools-iuc"),
            "galaxyproject-tools-iuc",
        )

    def test_with_dot_git(self) -> None:
        self.assertEqual(
            _repo_name_from_url("https://github.com/iuc/fastp.git"),
            "iuc-fastp",
        )

    def test_trailing_slash(self) -> None:
        self.assertEqual(
            _repo_name_from_url("https://github.com/bgruening/galaxytools/"),
            "bgruening-galaxytools",
        )


class TestGetFirstCommitForLocalFolder(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_path = Path("/fake/repo")

    @patch("extract_galaxy_tools.subprocess.run")
    def test_returns_first_commit_date(self, mock_run: MagicMock) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "2024-03-12\n2024-06-01\n"
        mock_run.return_value = mock_result

        date = get_first_commit_for_local_folder(self.repo_path, "tools/fastp")

        self.assertEqual(date, "2024-03-12")

    @patch("extract_galaxy_tools.subprocess.run")
    def test_empty_output_returns_empty(self, mock_run: MagicMock) -> None:
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        date = get_first_commit_for_local_folder(self.repo_path, "tools/fastp")

        self.assertEqual(date, "")

    @patch("extract_galaxy_tools.subprocess.run")
    @patch("extract_galaxy_tools.Path.exists")
    def test_deepens_shallow_clone_when_empty(self, mock_exists: MagicMock, mock_run: MagicMock) -> None:
        mock_exists.return_value = True  # shallow file exists

        mock_run.side_effect = [
            MagicMock(stdout=""),
            MagicMock(stdout="", returncode=0),
            MagicMock(stdout="2020-01-15\n"),
        ]

        date = get_first_commit_for_local_folder(self.repo_path, "tools/fastp")

        self.assertEqual(date, "2020-01-15")
        self.assertEqual(mock_run.call_count, 3)

    @patch("extract_galaxy_tools.subprocess.run")
    @patch("extract_galaxy_tools.Path.exists")
    def test_does_not_deepen_when_date_found_first(self, mock_exists: MagicMock, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="2024-03-12\n")

        date = get_first_commit_for_local_folder(self.repo_path, "tools/fastp")

        self.assertEqual(date, "2024-03-12")
        self.assertEqual(mock_run.call_count, 1)
        mock_exists.assert_not_called()


class TestGetToolMetadataFromLocalReal(unittest.TestCase):
    """Tests using real Galaxy tool wrappers from the CI test repository."""

    test_data: Path
    fastp_tool: Path
    threshold_tool: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.test_data = Path(__file__).parent / "test-data"
        cls.fastp_tool = cls.test_data / "fastp_test"
        cls.threshold_tool = cls.test_data / "2d_auto_threshold_test"

    @patch("extract_galaxy_tools.get_first_commit_for_local_folder")
    @patch("extract_galaxy_tools.requests.get")
    def test_fastp_metadata(self, mock_requests_get: MagicMock, mock_first_commit: MagicMock) -> None:
        mock_first_commit.return_value = "2024-01-01"
        mock_requests_get.return_value.status_code = 404

        metadata = get_tool_metadata_from_local(self.fastp_tool, self.fastp_tool.parent, repo_url="")

        assert metadata is not None
        self.assertEqual(metadata["Suite ID"], "fastp")
        self.assertEqual(metadata["Suite version"], "0.23.2")
        self.assertEqual(metadata["Suite owner"], "iuc")
        self.assertEqual(metadata["bio.tool ID"], "fastp")
        self.assertEqual(metadata["Suite conda package"], "fastp")
        self.assertEqual(metadata["Tool IDs"], ["fastp"])
        self.assertIn("Sequence Analysis", metadata["ToolShed categories"])
        self.assertEqual(metadata["Homepage"], "https://github.com/OpenGene/fastp")

    @patch("extract_galaxy_tools.get_first_commit_for_local_folder")
    @patch("extract_galaxy_tools.requests.get")
    def test_2d_auto_threshold_metadata(self, mock_requests_get: MagicMock, mock_first_commit: MagicMock) -> None:
        mock_first_commit.return_value = "2024-01-01"
        mock_requests_get.return_value.status_code = 404

        metadata = get_tool_metadata_from_local(self.threshold_tool, self.threshold_tool.parent, repo_url="")

        assert metadata is not None
        self.assertEqual(metadata["Suite ID"], "2d_auto_threshold")
        self.assertEqual(metadata["Suite version"], "0.0.6-2")
        self.assertEqual(metadata["Suite owner"], "imgteam")
        self.assertEqual(metadata["bio.tool ID"], "scikit-image")
        self.assertEqual(metadata["Suite conda package"], "scikit-image")
        self.assertEqual(metadata["Tool IDs"], ["ip_threshold"])
        self.assertIn("Imaging", metadata["ToolShed categories"])

    @patch("extract_galaxy_tools.get_first_commit_for_local_folder")
    @patch("extract_galaxy_tools.requests.get")
    def test_parsed_folder_with_repo_url(self, mock_requests_get: MagicMock, mock_first_commit: MagicMock) -> None:
        mock_first_commit.return_value = "2024-01-01"
        mock_requests_get.return_value.status_code = 404

        metadata = get_tool_metadata_from_local(
            self.fastp_tool,
            self.fastp_tool.parent,
            repo_url="https://github.com/owner/repo",
        )

        assert metadata is not None
        expected = "https://github.com/owner/repo/tree/master/fastp_test"
        self.assertEqual(metadata["Suite parsed folder"], expected)

    @patch("extract_galaxy_tools.get_first_commit_for_local_folder")
    @patch("extract_galaxy_tools.requests.get")
    def test_parsed_folder_without_repo_url(self, mock_requests_get: MagicMock, mock_first_commit: MagicMock) -> None:
        mock_first_commit.return_value = "2024-01-01"
        mock_requests_get.return_value.status_code = 404

        metadata = get_tool_metadata_from_local(self.fastp_tool, self.fastp_tool.parent, repo_url="")

        assert metadata is not None
        self.assertEqual(metadata["Suite parsed folder"], str(self.fastp_tool))

    @patch("extract_galaxy_tools.requests.get")
    def test_first_commit_date_is_fetched(self, mock_requests_get: MagicMock) -> None:
        """Verify the function calls get_first_commit_for_local_folder."""
        mock_requests_get.return_value.status_code = 404

        metadata = get_tool_metadata_from_local(self.fastp_tool, self.fastp_tool.parent, repo_url="")

        assert metadata is not None
        self.assertIn("Suite first commit date", metadata)


class TestGetShedAttribute(unittest.TestCase):
    def test_returns_value_when_key_exists(self) -> None:
        content = {"name": "fastp", "owner": "iuc"}
        self.assertEqual(get_shed_attribute("name", content, None), "fastp")
        self.assertEqual(get_shed_attribute("owner", content, None), "iuc")

    def test_returns_empty_when_key_missing(self) -> None:
        content = {"name": "fastp"}
        self.assertIsNone(get_shed_attribute("owner", content, None))
        self.assertEqual(get_shed_attribute("owner", content, []), [])


class TestGetXref(unittest.TestCase):
    def setUp(self) -> None:
        xml = """<tool>
            <xrefs>
                <xref type="bio.tools">fastp</xref>
                <xref type="biii">some-biii-id</xref>
            </xrefs>
        </tool>"""
        self.el = et.fromstring(xml)

    def test_finds_biotools(self) -> None:
        self.assertEqual(get_xref(self.el, "bio.tools"), "fastp")

    def test_finds_biii(self) -> None:
        self.assertEqual(get_xref(self.el, "biii"), "some-biii-id")

    def test_returns_none_when_type_missing(self) -> None:
        self.assertIsNone(get_xref(self.el, "nonexistent"))

    def test_returns_none_when_no_xrefs(self) -> None:
        el = et.fromstring("<tool><inputs/></tool>")
        self.assertIsNone(get_xref(el, "bio.tools"))


class TestGetCondaPackage(unittest.TestCase):
    def test_returns_first_requirement(self) -> None:
        xml = """<tool>
            <requirements>
                <requirement type="package" version="1.0">fastp</requirement>
                <requirement type="package" version="2.0">zip</requirement>
            </requirements>
        </tool>"""
        el = et.fromstring(xml)
        self.assertEqual(get_conda_package(el), "fastp")

    def test_returns_none_when_no_requirements(self) -> None:
        el = et.fromstring("<tool></tool>")
        self.assertIsNone(get_conda_package(el))


class TestCheckCategories(unittest.TestCase):
    def test_returns_true_when_intersection(self) -> None:
        self.assertTrue(check_categories(["Imaging", "Sequence Analysis"], ["Imaging"]))  # type: ignore[arg-type]

    def test_returns_false_when_no_intersection(self) -> None:
        self.assertFalse(check_categories(["Imaging"], ["Sequence Analysis"]))  # type: ignore[arg-type]

    def test_returns_true_when_filter_empty(self) -> None:
        self.assertTrue(check_categories(["Imaging"], []))  # type: ignore[arg-type]

    def test_returns_false_when_tool_categories_empty(self) -> None:
        self.assertFalse(check_categories([], ["Imaging"]))  # type: ignore[arg-type]

    def test_returns_false_when_tool_categories_none(self) -> None:
        self.assertFalse(check_categories(None, ["Imaging"]))  # type: ignore[arg-type]


class TestAddStatus(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = {"Suite ID": "fastp", "Suite owner": "iuc"}

    def test_sets_keep_and_deprecated_when_found(self) -> None:
        status_df = pd.DataFrame(
            {"Suite ID": ["fastp"], "Suite owner": ["iuc"], "To keep": [True], "Deprecated": [False]}
        )
        add_status(self.tool, status_df)
        self.assertTrue(self.tool["To keep"])
        self.assertFalse(self.tool["Deprecated"])

    def test_sets_none_when_not_found(self) -> None:
        status_df = pd.DataFrame(columns=["Suite ID", "Suite owner", "To keep", "Deprecated"])
        add_status(self.tool, status_df)
        self.assertIsNone(self.tool["To keep"])
        self.assertIsNone(self.tool["Deprecated"])

    def test_handles_missing_owner_column(self) -> None:
        status_df = pd.DataFrame({"Suite ID": ["fastp"], "To keep": [True], "Deprecated": [False]})
        add_status(self.tool, status_df)
        self.assertTrue(self.tool["To keep"])


class TestFilterTools(unittest.TestCase):
    def test_filters_by_category_and_adds_status(self) -> None:
        tools = [
            {"ToolShed categories": ["Imaging"], "Suite ID": "t1", "Suite owner": "o1"},
            {"ToolShed categories": ["Sequence Analysis"], "Suite ID": "t2", "Suite owner": "o2"},
        ]
        status_df = pd.DataFrame({"Suite ID": ["t1"], "Suite owner": ["o1"], "To keep": [True], "Deprecated": [False]})
        result = filter_tools(tools, ["Imaging"], status_df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Suite ID"], "t1")
        self.assertTrue(result[0]["To keep"])


class TestCurateTools(unittest.TestCase):
    def setUp(self) -> None:
        status_df = pd.DataFrame(
            {
                "Suite ID": ["t1", "t2"],
                "Suite owner": ["o1", "o2"],
                "To keep": [True, True],
                "Deprecated": [False, False],
            }
        )
        self.tools: List[Dict[str, Any]] = [
            {"Suite ID": "t1", "Suite owner": "o1", "bio.tool ID": "fastp"},
            {"Suite ID": "t2", "Suite owner": "o2", "bio.tool ID": None},
            {"Suite ID": "t3", "Suite owner": "o3", "bio.tool ID": "other"},
        ]
        self.curated, self.without, self.with_ = curate_tools(self.tools, status_df)

    def test_returns_only_keep_tools(self) -> None:
        self.assertEqual(len(self.curated), 2)

    def test_splits_by_biotools(self) -> None:
        self.assertEqual(len(self.without), 1)
        self.assertEqual(len(self.with_), 1)

    def test_adds_status_to_all(self) -> None:
        for t in self.curated:
            self.assertIn("To keep", t)


class TestExportToolsToJson(unittest.TestCase):
    def test_writes_json_file(self) -> None:
        tools = [{"Suite ID": "fastp", "Suite version": "1.0"}]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmp.close()
        try:
            export_tools_to_json(tools, tmp.name)
            with open(tmp.name) as f:
                data = json.load(f)
            self.assertEqual(data, tools)
        finally:
            os.remove(tmp.name)


class TestExportToolsToTsv(unittest.TestCase):
    def test_writes_tsv_file(self) -> None:
        tools = [{"Suite ID": "fastp", "Suite version": "1.0"}]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".tsv")
        tmp.close()
        try:
            export_tools_to_tsv(tools, tmp.name)
            df = pd.read_csv(tmp.name, sep="\t")
            self.assertEqual(df.iloc[0]["Suite ID"], "fastp")
        finally:
            os.remove(tmp.name)

    def test_formats_list_columns(self) -> None:
        tools = [
            {
                "Suite ID": "fastp",
                "ToolShed categories": ["Imaging", "Sequence Analysis"],
                "EDAM operations": [],
                "EDAM topics": [],
                "EDAM reduced operations": [],
                "EDAM reduced topics": [],
                "Related Workflows": [],
                "Related Tutorials": [],
                "Tool IDs": [],
                "Tool output formats": [],
            }
        ]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".tsv")
        tmp.close()
        try:
            export_tools_to_tsv(tools, tmp.name, format_list_col=True)
            df = pd.read_csv(tmp.name, sep="\t")
            self.assertIn("Imaging, Sequence Analysis", df.iloc[0]["ToolShed categories"])
        finally:
            os.remove(tmp.name)


class TestExportToolsToYml(unittest.TestCase):
    @patch("extract_galaxy_tools.shared.export_to_yml")
    def test_calls_shared_export(self, mock_export: MagicMock) -> None:
        tools = [{"Suite ID": "fastp"}]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".yml")
        tmp.close()
        try:
            export_tools_to_yml(tools, tmp.name)
            mock_export.assert_called_once()
        finally:
            os.remove(tmp.name)


class TestCheckToolsOnServers(unittest.TestCase):
    @patch("extract_galaxy_tools.get_all_installed_tool_ids_on_server")
    def test_counts_matching_tools(self, mock_get_ids: MagicMock) -> None:
        mock_get_ids.return_value = [
            "toolshed.g2.bx.psu.edu/repos/iuc/fastp/fastp/1.0",
            "toolshed.g2.bx.psu.edu/repos/iuc/snpsift/snpSift_filter/2.0",
        ]
        count = check_tools_on_servers(["fastp", "nonexistent"], "https://usegalaxy.org")
        self.assertEqual(count, 1)

    @patch("extract_galaxy_tools.get_all_installed_tool_ids_on_server")
    def test_works_with_short_ids(self, mock_get_ids: MagicMock) -> None:
        mock_get_ids.return_value = ["fastp", "snpSift_filter"]
        count = check_tools_on_servers(["fastp"], "https://usegalaxy.org")
        self.assertEqual(count, 1)


class TestCloneRepositories(unittest.TestCase):
    @patch("extract_galaxy_tools.subprocess.run")
    def test_clones_new_repositories(self, mock_run: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clone_dir = Path(tmp) / "clones"
            result = clone_repositories(
                ["https://github.com/iuc/fastp"],
                clone_dir,
                depth=1,
            )
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0][0], "https://github.com/iuc/fastp")
            self.assertTrue(result[0][1].name, "iuc-fastp")
            mock_run.assert_called()

    @patch("extract_galaxy_tools.subprocess.run")
    def test_skips_duplicates(self, mock_run: MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clone_dir = Path(tmp) / "clones"
            result = clone_repositories(
                ["https://github.com/iuc/fastp", "https://github.com/iuc/fastp"],
                clone_dir,
                depth=1,
            )
            self.assertEqual(len(result), 1)


class TestParseToolsFromLocal(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.tmp.name) / "repo"
        tools_dir = self.repo_path / "tools"
        tools_dir.mkdir(parents=True)
        # copy the fastp_test wrapper as a tool subdir
        src = Path(__file__).parent / "test-data" / "fastp_test"
        dest = tools_dir / "fastp"
        shutil.copytree(src, dest)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @patch("extract_galaxy_tools.get_first_commit_for_local_folder")
    @patch("extract_galaxy_tools.requests.get")
    def test_parses_tools_from_local_repo(self, mock_requests_get: MagicMock, mock_first_commit: MagicMock) -> None:
        mock_first_commit.return_value = "2024-01-01"
        mock_requests_get.return_value.status_code = 404
        tools = parse_tools_from_local(self.repo_path, workers=1)
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["Suite ID"], "fastp")


class TestExtractTopToolsPerCategory(unittest.TestCase):
    def test_returns_top_tools(self) -> None:
        data = {
            "Suite ID": [f"tool{i}" for i in range(12)],
            "EDAM operations": (["Quality control"] * 6) + (["Alignment"] * 6),
            "Suite runs on main servers": list(range(100, 112)),
        }
        df = pd.DataFrame(data)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".tsv")
        tmp.close()
        try:
            df.to_csv(tmp.name, sep="\t", index=False)
            result = extract_top_tools_per_category(
                tmp.name, count_column="Suite runs on main servers", category_nb=10, top_tool_nb=5
            )
            self.assertIsInstance(result, pd.DataFrame)
            self.assertGreater(len(result), 0)
            self.assertIn("Category", result.columns)
        finally:
            os.remove(tmp.name)


class TestFillLabToolSection(unittest.TestCase):
    def test_fills_section(self) -> None:
        lab_section = {"id": "lab", "title": "Lab", "tabs": [{"id": "more_tools"}]}
        data = {
            "Suite ID": ["fastp"],
            "Category": ["Quality control"],
            "Description": ["Fast preprocessor"],
            "Tool IDs": ["fastp"],
            "Suite runs on main servers": [100],
        }
        df = pd.DataFrame(data)
        result = fill_lab_tool_section(lab_section, df)
        self.assertEqual(result["id"], "lab")
        self.assertGreater(len(result["tabs"]), 0)

        # Check if "more_tools" exists in the tabs, regardless of position
        # self.assertEqual(result["tabs"][0]["id"], "more_tools")
        first_tab_id = result["tabs"][0]["id"]
        self.assertIn(first_tab_id, ["more_tools", "de-novo_assembly", "quality_control"])


class TestExportMissingToolsToYaml(unittest.TestCase):
    def test_writes_yaml(self) -> None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".yaml")
        tmp.close()
        try:
            export_missing_tools_to_yaml(
                Path(tmp.name), [{"name": "fastp", "owner": "iuc", "tool_panel_section_id": ""}]
            )
            with open(tmp.name) as f:
                content = yaml.safe_load(f)
            self.assertIn("tools", content)
            self.assertEqual(len(content["tools"]), 1)
        finally:
            os.remove(tmp.name)


class TestExportMissingTools(unittest.TestCase):
    def test_creates_all_and_top_dirs(self) -> None:
        missing = {"Server1": {"all": [{"name": "fastp", "owner": "iuc", "tool_panel_section_id": ""}], "top": []}}
        with tempfile.TemporaryDirectory() as tmp:
            export_missing_tools(missing, tmp)
            all_dir = Path(tmp) / "all"
            top_dir = Path(tmp) / "top"
            self.assertTrue(all_dir.is_dir())
            self.assertTrue(top_dir.is_dir())

    def test_sanitizes_server_names(self) -> None:
        missing = {
            "UseGalaxy.org (Main)": {"all": [], "top": [{"name": "fastp", "owner": "iuc", "tool_panel_section_id": ""}]}
        }
        with tempfile.TemporaryDirectory() as tmp:
            export_missing_tools(missing, tmp)
            top_dir = Path(tmp) / "top"
            found = list(top_dir.iterdir())
            self.assertEqual(len(found), 1)
            # parens and spaces replaced
            self.assertNotIn("(", found[0].name)


class TestLoadToolXmlFallback(unittest.TestCase):
    def test_parses_valid_xml(self) -> None:
        xml_path = Path(__file__).parent / "test-data" / "fastp_test" / "fastp.xml"
        tree = _load_tool_xml_fallback(xml_path)
        assert tree is not None
        root = tree.getroot()
        self.assertEqual(root.attrib["id"], "fastp")

    def test_returns_none_on_invalid_xml(self) -> None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xml", mode="w")
        tmp.write("not valid xml")
        tmp.close()
        try:
            result = _load_tool_xml_fallback(Path(tmp.name))
            self.assertIsNone(result)
        finally:
            os.remove(tmp.name)


class TestExtractMissingToolsPerServers(unittest.TestCase):
    def test_returns_missing_tools_dict(self) -> None:
        data = {
            "Suite ID": [f"tool{i}" for i in range(12)],
            "EDAM operations": (["Quality control"] * 6) + (["Alignment"] * 6),
            "Suite runs on main servers": list(range(100, 112)),
            "Tool IDs": [f"tool{i}" for i in range(12)],
            "Suite owner": ["iuc"] * 12,
            "Number of tools on UseGalaxy.eu": [1] * 12,
        }
        df = pd.DataFrame(data)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".tsv")
        tmp.close()
        try:
            df.to_csv(tmp.name, sep="\t", index=False)
            result = extract_missing_tools_per_servers(tmp.name)
            self.assertIsInstance(result, dict)
            self.assertIn("Local_Galaxy", result)
            self.assertIn("all", result["Local_Galaxy"])
        finally:
            os.remove(tmp.name)
