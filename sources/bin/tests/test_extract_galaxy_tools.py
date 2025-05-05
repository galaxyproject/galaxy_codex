import unittest
from typing import Any
from unittest.mock import (
    MagicMock,
    patch,
)

from extract_galaxy_tools import get_tool_github_repositories


class TestGetToolGithubRepositories(unittest.TestCase):
    """
    Unit tests for the get_tool_github_repositories function.
    """

    def setUp(self) -> None:
        """
        Shared mock setup for GitHub repo hierarchy and content.
        """
        # Mocked file content returned by get_string_content
        self.mock_content: Any = MagicMock()

        # Mock GitHub repo object
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
        mock_get_string_content.return_value = (
            "https://github.com/genouest/galaxy-tools\n"
            "https://github.com/galaxyproject/galaxy\n"
            "https://github.com/TGAC/earlham-galaxytools\n"
        )

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
        mock_get_string_content.return_value = (
            "https://github.com/genouest/galaxy-tools\n"
            "https://github.com/galaxyproject/galaxy\n"
            "https://github.com/TGAC/earlham-galaxytools\n"
        )

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
