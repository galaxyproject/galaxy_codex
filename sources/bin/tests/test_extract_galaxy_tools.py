import unittest
from typing import Any
from unittest.mock import (
    MagicMock,
    patch,
)

from extract_galaxy_tools import (
    get_github_repo,
    get_last_url_position,
    get_tool_github_repositories,
)
from github import Github


class TestGetToolGithubRepositories(unittest.TestCase):
    """
    Unit tests for the get_tool_github_repositories function.
    """

    def setUp(self) -> None:
        """
        Shared mock setup for GitHub repo hierarchy, content, and repository URLs.
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

        # The mocked content (repository URLs) that can be reused across tests
        self.mock_repositories_content = (
            "https://github.com/genouest/galaxy-tools\n"
            "https://github.com/galaxyproject/galaxy\n"
            "https://github.com/TGAC/earlham-galaxytools\n"
        )

        # Mock return value for get_string_content to be reused in each test
        self.mock_get_string_content: MagicMock = MagicMock()
        self.mock_get_string_content.return_value = self.mock_repositories_content

    @patch("extract_galaxy_tools.get_string_content")
    def test_get_tool_github_repositories(self, mock_get_string_content: MagicMock) -> None:
        """
        Test that get_tool_github_repositories returns a list of repository URLs
        when run_test=False and add_extra_repositories=False.
        """
        # No need to reset return_value as it is already set in setUp

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
        # No need to reset return_value as it is already set in setUp

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
