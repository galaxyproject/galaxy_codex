import unittest
from unittest.mock import (
    MagicMock,
    patch,
)

from citation_manager import (
    Paper,
    Papers,
)


class TestPaper(unittest.TestCase):
    def test_paper_init(self) -> None:
        paper = Paper()
        assert paper.id == ""
        assert paper.title == ""
        assert paper.year == 1900
        assert paper.journal == ""
        assert paper.abstract == ""
        assert paper.citation_number == 0
        assert paper.citations == []
        assert paper.groups == {}

    def test_init_from_semanticscholar(self) -> None:
        paper = Paper()
        paper.init_from_semanticscholar(
            {
                "citingPaper": {
                    "title": "Test Paper",
                    "year": 2020,
                    "journal": {
                        "name": "Test Journal",
                    },
                    "abstract": "This is a test abstract.",
                },
            }
        )
        assert paper.id == ""
        assert paper.title == "Test Paper"
        assert paper.year == 2020
        assert paper.journal == "Test Journal"
        assert paper.abstract == "This is a test abstract."
        assert paper.citation_number == 0
        assert paper.citations == []
        assert paper.groups == {}

    def test_init_from_json(self) -> None:
        paper = Paper()
        paper.init_from_json(
            {
                "id": "12345",
                "title": "Test Paper",
                "year": 2020,
                "journal": "Test Journal",
                "abstract": "This is a test abstract.",
                "citation_number": 10,
                "citations": [],
                "groups": {},
            }
        )
        assert paper.id == "12345"
        assert paper.title == "Test Paper"
        assert paper.year == 2020
        assert paper.journal == "Test Journal"
        assert paper.abstract == "This is a test abstract."
        assert paper.citation_number == 10
        assert paper.citations == []
        assert paper.groups == {}

    @patch("shared.get_request_json")
    def test_extract_paper_id(self, mock_get_request_json: MagicMock) -> None:
        mock_get_request_json.return_value = {"data": [{"paperId": "12345"}]}
        paper = Paper()
        paper.title = "Test Paper"
        paper.extract_paper_id()
        assert paper.id == "12345"
        mock_get_request_json.assert_called_once()

    @patch("shared.get_request_json")
    def test_extract_citation_number(self, mock_get_request_json: MagicMock) -> None:
        mock_get_request_json.return_value = {"citationCount": 10}
        paper = Paper()
        paper.id = "12345"
        paper.extract_citation_number()
        assert paper.citation_number == 10
        mock_get_request_json.assert_called_once()

    @patch("shared.get_request_json")
    @patch("time.sleep")
    def test_extract_citations(self, mock_sleep: MagicMock, mock_get_request_json: MagicMock) -> None:
        mock_get_request_json.return_value = {"data": []}
        paper = Paper()
        paper.id = "12345"
        paper.citation_number = 1000
        paper.extract_citations()
        assert len(paper.citations) == 0
        mock_get_request_json.assert_called()

    @patch("shared.get_request_json")
    def test_extract_citation_subset(self, mock_get_request_json: MagicMock) -> None:
        mock_get_request_json.return_value = {
            "data": [
                {
                    "citingPaper": {
                        "title": "Citing Paper",
                        "year": 2021,
                        "journal": {"name": "Citing Journal"},
                        "abstract": "This is a citing paper.",
                    }
                }
            ]
        }
        paper = Paper()
        paper.id = "12345"
        paper.extract_citation_subset(0, 1)
        assert len(paper.citations) == 1
        assert paper.citations[0].title == "Citing Paper"

    def test_add_groups_given_keywords(self) -> None:
        paper = Paper()
        paper.title = "Test Paper"
        paper.abstract = "This is a test abstract."
        kwd = {"group1": {"subgroup1": ["test"]}}
        paper.add_groups_given_keywords(kwd)
        assert paper.groups == {"group1": ["subgroup1"]}

    def test_contains_keywords(self) -> None:
        paper = Paper()
        paper.title = "Test Paper"
        paper.abstract = "This is a test abstract."
        assert paper._contains_keywords(["test"]) is True
        assert paper._contains_keywords(["missing"]) is False

    def test_has_kwd(self) -> None:
        paper = Paper()
        paper.title = "Test Paper"
        paper.abstract = "This is a test abstract."
        assert paper.has_kwd(["test"]) is True
        assert paper.has_kwd(["missing"]) is False


class TestPapers(unittest.TestCase):
    @patch("shared.load_json")
    def test_init_from_json(self, mock_load_json: MagicMock) -> None:
        mock_load_json.return_value = [
            {
                "id": "12345",
                "title": "Test Paper 1",
                "year": 2020,
                "journal": "Test Journal",
                "abstract": "This is a test abstract.",
                "citation_number": 10,
                "citations": [],
                "groups": {},
            },
            {
                "id": "67890",
                "title": "Test Paper 2",
                "year": 2021,
                "journal": "Test Journal",
                "abstract": "This is another test abstract.",
                "citation_number": 5,
                "citations": [],
                "groups": {},
            },
        ]
        papers = Papers()
        papers.init_from_json("dummy_path.json")
        assert len(papers.papers) == 2
        assert papers.papers[0].title == "Test Paper 1"
        assert papers.papers[1].title == "Test Paper 2"

    def test_add_citations_from_paper(self) -> None:
        papers = Papers()
        paper = Paper()
        papers.add_citations_from_paper(paper)
        assert len(papers.papers) == 0  # No citations in sample data

    def test_clean_papers(self) -> None:
        papers = Papers()
        paper1 = Paper()
        paper1.title = "Test Paper 1"
        paper1.year = 2020
        paper2 = Paper()
        paper2.title = "Test Paper 1"  # Duplicate title
        paper2.year = 2021
        paper3 = Paper()
        paper3.title = "Test Paper 3"
        paper3.year = 2000  # Invalid year
        papers.papers = [paper1, paper2, paper3]
        papers.clean_papers()
        assert len(papers.papers) == 1
        assert papers.papers[0].title == "Test Paper 1"
        assert papers.papers[0].year == 2020

    @patch("shared.load_yaml")
    def test_filter_given_tags(self, mock_load_yaml: MagicMock) -> None:
        mock_load_yaml.return_value = {"tags": ["test"], "groups": {"group1": {"subgroup1": ["test"]}}}
        papers = Papers()
        paper1 = Paper()
        paper1.title = "Test Paper 1"
        paper1.abstract = "This is a test abstract."
        paper2 = Paper()
        paper2.title = "Other Paper 2"
        paper2.abstract = "This is another abstract."
        papers.papers = [paper1, paper2]
        papers.filter_given_tags("dummy_path.yaml")
        assert len(papers.papers) == 1
        assert papers.papers[0].title == "Test Paper 1"
        assert papers.papers[0].groups == {"group1": ["subgroup1"]}

    @patch("pandas.DataFrame.to_csv")
    def test_export_to_tsv(self, mock_to_csv: MagicMock) -> None:
        papers = Papers()
        paper = Paper()
        paper.title = "Test Paper"
        paper.year = 2020
        paper.journal = "Test Journal"
        papers.papers = [paper]
        papers.export_to_tsv("dummy_path.tsv")
        mock_to_csv.assert_called_once_with("dummy_path.tsv", sep="\t", index=False)
