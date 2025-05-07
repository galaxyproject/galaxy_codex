import unittest
from unittest.mock import (
    MagicMock,
    patch,
)

from extract_gtn_tutorials import (
    filter_tutorials,
    format_tutorial,
    get_visits,
    get_youtube_stats,
)


class TestGetVisits(unittest.TestCase):
    """
    Unit tests for the get_visits function (Plausible API).
    """

    # Test successful response from the API
    @patch("extract_gtn_tutorials.shared.get_request_json")
    def test_get_visits_success(self, mock_get_request_json):
        mock_get_request_json.return_value = {
            "results": {
                "visitors": {"value": 123},
                "pageviews": {"value": 456},
                "visit_duration": {"value": 789},
            }
        }

        # Create tutorial object to test
        tuto = {
            "tutorial_name": "example_tutorial",
            "hands_on": True,
            "topic_name": "microbiome",
            "pub_date": "2025-01-01",
            "slides": False,
            "visitors": 0,
            "pageviews": 0,
            "visit_duration": 0,
        }

        get_visits(tuto, "fake_api_key")

        # Assertions to verify that values were correctly updated
        self.assertEqual(tuto["visitors"], 123)
        self.assertEqual(tuto["pageviews"], 456)
        self.assertEqual(tuto["visit_duration"], 789)

    # Test when the API response has no results
    @patch("extract_gtn_tutorials.shared.get_request_json")
    def test_get_visits_no_results(self, mock_get_request_json):
        mock_get_request_json.return_value = {}
        tuto = {
            "tutorial_name": "example_tutorial",
            "hands_on": True,
            "topic_name": "microbiome",
            "pub_date": "2025-01-01",
            "slides": False,
            "visitors": 0,
            "pageviews": 0,
            "visit_duration": 0,
        }
        get_visits(tuto, "fake_api_key")

        # Verify no changes in values when no data is returned
        self.assertEqual(tuto["visitors"], 0)
        self.assertEqual(tuto["pageviews"], 0)
        self.assertEqual(tuto["visit_duration"], 0)

    # Test when the API response is malformed or unexpected
    @patch("extract_gtn_tutorials.shared.get_request_json")
    def test_get_visits_malformed_response(self, mock_get_request_json):
        mock_get_request_json.return_value = {"unexpected_key": "unexpected_value"}
        tuto = {
            "tutorial_name": "example_tutorial",
            "hands_on": True,
            "topic_name": "microbiome",
            "pub_date": "2025-01-01",
            "slides": False,
            "visitors": 0,
            "pageviews": 0,
            "visit_duration": 0,
        }
        get_visits(tuto, "fake_api_key")

        # Check if the function safely handles a malformed response
        self.assertEqual(tuto["visitors"], 0)
        self.assertEqual(tuto["pageviews"], 0)
        self.assertEqual(tuto["visit_duration"], 0)


class TestGetYoutubeStats(unittest.TestCase):
    """
    Unit tests for the get_youtube_stats function.
    """

    # Test successful retrieval of YouTube video statistics
    @patch("yt_dlp.YoutubeDL")
    def test_youtube_stats_success(self, mock_ytdl_class):
        mock_ytdl_instance = mock_ytdl_class.return_value.__enter__.return_value
        mock_ytdl_instance.extract_info.return_value = {"view_count": 1000}
        mock_ytdl_instance.sanitize_info.return_value = {"view_count": 1000}

        tutorial = {"tutorial_name": "example_tutorial", "recordings": [{"youtube_id": "dQw4w9WgXcQ"}]}

        get_youtube_stats(tutorial)

        # Assertions to check if the view count and video versions are correct
        self.assertEqual(tutorial["video_view"], 1000)
        self.assertEqual(tutorial["video_versions"], 1)

    # Test failure case when the video is not found
    @patch("yt_dlp.YoutubeDL")
    def test_youtube_stats_failure(self, mock_ytdl_class):
        mock_ytdl_instance = mock_ytdl_class.return_value.__enter__.return_value
        mock_ytdl_instance.extract_info.side_effect = Exception("Video not found")

        # Expect an exception to be raised
        with self.assertRaises(Exception) as context:
            get_youtube_stats({"tutorial_name": "example_tutorial", "recordings": [{"youtube_id": "dQw4w9WgXcQ"}]})
        self.assertIn("Video not found", str(context.exception))

    # Test when there are no recordings in the tutorial
    @patch("yt_dlp.YoutubeDL")
    def test_youtube_stats_no_recordings(self, mock_ytdl_class):
        tutorial = {"tutorial_name": "example_tutorial", "recordings": []}
        get_youtube_stats(tutorial)

        # Verify that video views and versions are zero
        self.assertEqual(tutorial["video_view"], 0)
        self.assertEqual(tutorial["video_versions"], 0)

    # Test when there are multiple YouTube videos for a tutorial
    @patch("yt_dlp.YoutubeDL")
    def test_youtube_stats_multiple_videos(self, mock_ytdl_class):
        mock_ytdl_instance = mock_ytdl_class.return_value.__enter__.return_value
        mock_ytdl_instance.extract_info.return_value = {"view_count": 500}
        mock_ytdl_instance.sanitize_info.return_value = {"view_count": 500}

        tutorial = {
            "tutorial_name": "example_tutorial",
            "recordings": [{"youtube_id": "dQw4w9WgXcQ"}, {"youtube_id": "dQw4w9WgYz"}],
        }
        get_youtube_stats(tutorial)

        # Check if total views and video count are correctly calculated
        self.assertEqual(tutorial["video_view"], 1000)
        self.assertEqual(tutorial["video_versions"], 2)


class TestFormatTutorial(unittest.TestCase):
    """
    Unit tests for the format_tutorial function.
    """

    def setUp(self):
        # Setup initial tutorial data for testing
        self.test_tutorial = {
            "url": "training-material/topics/microbiome/tutorials/amr/path",
            "mod_date": "2023-05-01",
            "pub_date": "2023-04-01",
            "supported_servers": {
                "exact": [{"name": "usegalaxy.eu"}],
                "inexact": [{"name": "usegalaxy.org"}],
            },
            "tools": ["toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.72"],
            "edam_ontology": ["https://edamontology.org/topic_3174"],
            "hands_on": True,
            "slides": True,
            "recordings": [{"youtube_id": "dQw4w9WgXcQ"}],
            "title": "Microbiome AMR Tutorial",
            "topic_name": "microbiome",
            "tutorial_name": "amr",
            "video": True,
            "video_versions": 1,
        }

        self.mock_edam_ontology = {"https://edamontology.org/topic_3174": MagicMock(label=["Microbiology"])}
        self.mock_tools = {"fastqc": {"edam_operations": ["Sequence quality control"]}}
        self.mock_feedback = {"Microbiome AMR Tutorial": {"number": 5, "mean note": 4.2}}
        self.plausible_api = "dummy_token"

    # Test formatting the tutorial data
    @patch("extract_gtn_tutorials.get_youtube_stats", return_value={"view_count": "500"})
    @patch("extract_gtn_tutorials.get_visits", return_value=200)
    @patch("extract_gtn_tutorials.shared.get_edam_operation_from_tools", return_value=["Sequence quality control"])
    @patch("extract_gtn_tutorials.shared.shorten_tool_id", return_value="fastqc")
    @patch("extract_gtn_tutorials.shared.format_date", side_effect=lambda x: x)
    def test_format_tutorial_full(
        self, mock_format_date, mock_shorten_tool_id, mock_get_edam_ops, mock_get_visits, mock_get_youtube_stats
    ):
        formatted = format_tutorial(
            self.test_tutorial,
            self.mock_edam_ontology,
            self.mock_tools,
            self.mock_feedback,
            self.plausible_api,
        )

        # Assertions to verify the formatting is correct
        self.assertEqual(formatted["exact_supported_servers"], ["usegalaxy.eu"])
        self.assertEqual(formatted["video_versions"], 1)
        self.assertTrue(formatted["video"])
        self.assertEqual(formatted["feedback_number"], 5)
        self.assertEqual(formatted["edam_topic"], ["Microbiology"])
        self.assertEqual(formatted["short_tools"], ["fastqc"])

        # Check if external functions were called
        mock_get_visits.assert_called_once()
        mock_get_youtube_stats.assert_called_once()


class TestFilterTutorials(unittest.TestCase):
    """
    Unit tests for the filter_tutorials function.
    """

    # Test filtering tutorials when no tags are provided
    def test_filter_tutorials_empty_tags(self):
        tutorials = [
            {"tags": ["bioinformatics", "genomics"], "tutorial_name": "tuto1"},
            {"tags": ["python", "bioinformatics"], "tutorial_name": "tuto2"},
        ]
        tags = []
        filtered_tutorials = filter_tutorials(tutorials, tags)
        self.assertEqual(filtered_tutorials, [])

    # Test when no tutorials match the given tags
    def test_filter_tutorials_no_matching_tags(self):
        tutorials = [
            {"tags": ["bioinformatics", "genomics"], "tutorial_name": "tuto1"},
            {"tags": ["python", "bioinformatics"], "tutorial_name": "tuto2"},
        ]
        tags = ["data science"]
        filtered_tutorials = filter_tutorials(tutorials, tags)
        self.assertEqual(filtered_tutorials, [])

    # Test filtering tutorials when some have no tags
    def test_filter_tutorials_no_tags(self):
        tutorials = [
            {"tags": ["bioinformatics", "genomics"], "tutorial_name": "tuto1"},
            {"tags": [], "tutorial_name": "tuto2"},
        ]
        tags = ["bioinformatics"]
        filtered_tutorials = filter_tutorials(tutorials, tags)
        self.assertEqual(filtered_tutorials, [{"tags": ["bioinformatics", "genomics"], "tutorial_name": "tuto1"}])
