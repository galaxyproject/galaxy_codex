import unittest
from unittest.mock import (
    MagicMock,
    patch,
)

import pandas as pd
from get_public_galaxy_servers import (
    check_server,
    get_public_galaxy_servers,
    is_likely_galaxy_url,
)


class TestIsLikelyGalaxyUrl(unittest.TestCase):
    def test_normal_url(self) -> None:
        self.assertTrue(is_likely_galaxy_url("https://usegalaxy.org"))

    def test_hub_docker_com(self) -> None:
        self.assertFalse(is_likely_galaxy_url("https://hub.docker.com/r/galaxy"))

    def test_github_com(self) -> None:
        self.assertFalse(is_likely_galaxy_url("https://github.com/galaxyproject"))

    def test_docker_io(self) -> None:
        self.assertFalse(is_likely_galaxy_url("https://docker.io/galaxy"))

    def test_readthedocs(self) -> None:
        self.assertFalse(is_likely_galaxy_url("https://galaxy.readthedocs.io"))

    def test_aws_amazon(self) -> None:
        self.assertFalse(is_likely_galaxy_url("https://aws.amazon.com/marketplace"))

    def test_nectar_org(self) -> None:
        self.assertFalse(is_likely_galaxy_url("https://dashboard.nectar.org"))

    def test_case_insensitive(self) -> None:
        self.assertFalse(is_likely_galaxy_url("https://DOCKER.io/image"))

    def test_empty_string(self) -> None:
        self.assertTrue(is_likely_galaxy_url(""))


class TestCheckServer(unittest.TestCase):
    @patch("get_public_galaxy_servers.requests.Session")
    def test_working_server(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_session
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = []
        mock_session.get.return_value = mock_resp

        title, url, ok = check_server("Test Instance", "https://test.galaxy.org", mock_session, 15)
        self.assertEqual(title, "Test Instance")
        self.assertEqual(url, "https://test.galaxy.org")
        self.assertTrue(ok)
        mock_session.get.assert_called_with("https://test.galaxy.org/api/tools", params={"in_panel": False}, timeout=15)

    @patch("get_public_galaxy_servers.requests.Session")
    def test_failing_server(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_session
        mock_session.get.side_effect = Exception("Connection refused")

        title, url, ok = check_server("Dead Instance", "https://dead.galaxy.org", mock_session, 5)
        self.assertEqual(title, "Dead Instance")
        self.assertEqual(url, "https://dead.galaxy.org")
        self.assertFalse(ok)

    @patch("get_public_galaxy_servers.requests.Session")
    def test_trailing_slash_stripped(self, mock_session_cls: MagicMock) -> None:
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_session
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = []
        mock_session.get.return_value = mock_resp

        _, url, ok = check_server("With Slash", "https://test.galaxy.org/", mock_session, 15)
        self.assertEqual(url, "https://test.galaxy.org")
        self.assertTrue(ok)


class TestGetPublicGalaxyServers(unittest.TestCase):
    @patch("get_public_galaxy_servers.requests.get")
    @patch("get_public_galaxy_servers.pd.read_csv")
    @patch("get_public_galaxy_servers.check_server")
    @patch("get_public_galaxy_servers.concurrent.futures.as_completed")
    @patch("get_public_galaxy_servers.sys.stderr")
    def test_custom_servers_included(
        self,
        mock_stderr: MagicMock,
        mock_as_completed: MagicMock,
        mock_check_server: MagicMock,
        mock_read_csv: MagicMock,
        mock_requests_get: MagicMock,
    ) -> None:
        feed = [{"url": "https://usegalaxy.org", "title": "UseGalaxy.org"}]
        mock_requests_get.return_value.json.return_value = feed

        custom_df = pd.DataFrame({"name": ["My Server"], "url": ["https://my.galaxy.instance"]})
        mock_read_csv.return_value = custom_df

        mock_future = MagicMock()
        mock_future.result.return_value = ("My Server", "https://my.galaxy.instance", True)
        mock_as_completed.return_value = [mock_future]

        get_public_galaxy_servers("/dev/null", workers=1, timeout=5, custom_servers="servers.tsv")

        mock_read_csv.assert_called_with("servers.tsv", sep="\t", header=0)
