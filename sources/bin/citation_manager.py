#!/usr/bin/env python

import argparse
import time
from typing import (
    Any,
    Dict,
    List,
)

import pandas as pd
import shared
from scholarly import scholarly

SEMANTICSCHOLAR_API_URL_PREFIX = "https://api.semanticscholar.org/graph/v1/paper"


class Paper:
    """
    A class to represent a scientific paper, with methods to initialize from various sources,
    extract metadata, and manage citations and groups.
    """

    def __init__(self) -> None:
        """Initialize a Paper instance with default values."""
        self.id: str = ""
        self.title: str = ""
        self.year: int = 1900
        self.journal: str = ""
        self.abstract: str = ""
        self.citation_number: int = 0
        self.citations: List[Paper] = []
        self.groups: Dict[str, List[str]] = {}

    def init_from_scholarly(self, pub: Dict[str, Any]) -> None:
        """
        Initialize the paper from a Scholarly API response.

        Args:
            pub (dict): Scholarly API response dictionary.
        """
        self.title = pub["bib"]["title"]
        self.year = int(pub["bib"]["pub_year"])
        self.extract_paper_id()
        self.extract_citation_number()
        print(f"{self.title} ({self.year})")
        print(f"Citations: {self.citation_number}")
        self.extract_citations()

    def init_from_semanticscholar(self, pub: Dict[str, Any]) -> None:
        """
        Initialize the paper from a Semantic Scholar API response.

        Args:
            pub (dict): Semantic Scholar API response dictionary.
        """
        self.title = pub["citingPaper"]["title"]
        self.year = int(pub["citingPaper"]["year"]) if pub["citingPaper"]["year"] is not None else 0
        self.journal = (
            pub["citingPaper"]["journal"]["name"]
            if pub["citingPaper"]["journal"] is not None and "name" in pub["citingPaper"]["journal"]
            else ""
        )
        self.abstract = pub["citingPaper"]["abstract"] if pub["citingPaper"]["abstract"] is not None else ""

    def init_from_json(self, pub: Dict[str, Any]) -> None:
        """
        Initialize the paper from a JSON dictionary.

        Args:
            pub (dict): JSON dictionary containing paper metadata.
        """
        self.id = pub["id"]
        self.title = pub["title"]
        self.year = int(pub["year"])
        self.journal = pub["journal"]
        self.abstract = pub["abstract"]
        self.citation_number = int(pub["citation_number"])
        self.citations = pub["citations"]
        self.groups = pub["groups"]

    def get_title(self) -> str:
        """Return the title of the paper."""
        return self.title

    def get_year(self) -> int:
        """Return the publication year of the paper."""
        return self.year

    def get_citations(self) -> list:
        """Return the list of citations for the paper."""
        return self.citations

    def extract_paper_id(self) -> None:
        """
        Extract the paper ID from the Semantic Scholar API using the paper's title.
        Raises:
            ValueError: If the paper is not found.
        """
        url = f"{SEMANTICSCHOLAR_API_URL_PREFIX}/search/match?query={self.title}"
        response = shared.get_request_json(url, {"Accept": "application/json"})
        if "data" not in response:
            raise ValueError(f"Paper '{self.title}' not found")
        self.id = response["data"][0]["paperId"]

    def extract_citation_number(self) -> None:
        """
        Extract the citation count for the paper from the Semantic Scholar API.
        Raises:
            ValueError: If the citation count is not found.
        """
        if not self.id:
            self.extract_paper_id()
        url = f"{SEMANTICSCHOLAR_API_URL_PREFIX}/{self.id}?fields=citationCount"
        response = shared.get_request_json(url, {"Accept": "application/json"})
        if "citationCount" not in response:
            raise ValueError(f"No citation count found for paper ID: {self.id}")
        self.citation_number = response["citationCount"]

    def extract_citations(self) -> None:
        """
        Extract all citations for the paper from the Semantic Scholar API.
        """
        self.citations = []
        limit = 1000
        if self.citation_number == 0:
            self.extract_citation_number()

        for offset in range(0, self.citation_number, limit):
            self.extract_citation_subset(offset, limit)
            time.sleep(10)
        time.sleep(30)

    def extract_citation_subset(self, offset: int, limit: int) -> None:
        """
        Extract a subset of citations for the paper from the Semantic Scholar API.

        Args:
            offset (int): The offset for pagination.
            limit (int): The number of citations to fetch per request.
        Raises:
            ValueError: If no citations are found for the given offset and limit.
        """
        url = (
            f"{SEMANTICSCHOLAR_API_URL_PREFIX}/{self.id}/citations?"
            f"fields=title,abstract,year,journal&offset={offset}&limit={limit}"
        )
        response = shared.get_request_json(url, {"Accept": "application/json"})
        if "data" not in response:
            raise ValueError(f"No citation found for paper ID: {self.id} (offset={offset} and limit={limit})")

        for pub in response["data"]:
            citation = Paper()
            citation.init_from_semanticscholar(pub)
            self.citations.append(citation)

    def add_groups_given_keywords(self, kwd: Dict[str, Dict[str, List[str]]]) -> None:
        """
        Add groups to the paper based on keywords found in the title or abstract.

        Args:
            kwd (dict): A dictionary of groups and their associated keywords.
        """
        for group_name, group_keywords in kwd.items():
            self.groups[group_name] = []
            for subgroup_name, keywords in group_keywords.items():
                if self._contains_keywords(keywords):
                    self.groups[group_name].append(subgroup_name)

    def _contains_keywords(self, keywords: List[str]) -> bool:
        """
        Helper method to check if any keyword is present in the title or abstract.

        Args:
            keywords (list): List of keywords to search for.
        Returns:
            bool: True if any keyword is found, False otherwise.
        """
        title_lower = self.title.lower()
        abstract_lower = self.abstract.lower()
        return any(keyword.lower() in title_lower or keyword.lower() in abstract_lower for keyword in keywords)

    def has_kwd(self, keywords: List[str]) -> bool:
        """
        Check if the paper's title or abstract contains any of the given keywords.

        Args:
            keywords (list): List of keywords to search for.
        Returns:
            bool: True if any keyword is found, False otherwise.
        """
        return self._contains_keywords(keywords)


class Papers:
    """
    A class to manage a collection of scientific papers, with methods to initialize,
    filter, clean, and export papers.
    """

    def __init__(self) -> None:
        """Initialize a Papers instance with an empty list of papers."""
        self.papers: List[Paper] = []

    def init_from_major_publications(self, run_test: bool = False) -> None:
        """
        Initialize papers from major Galaxy publications using the Scholarly API.

        Args:
            run_test (bool): If True, only the first publication is processed for testing.
        """
        print("Extracting citations of the major Galaxy papers...\n")
        author = scholarly.search_author_id("3tSiRGoAAAAJ")
        author = scholarly.fill(author, sections=["publications"])

        self.papers = []
        publications = author["publications"]
        if run_test:
            publications = [publications[0]]

        for pub in publications:
            # Keep only majors Galaxy papers
            keep = any(
                keyword in pub["bib"]["title"].lower()
                for keyword in [
                    "platform",
                    "a comprehensive approach",
                    "a web-based genome analysis tool for experimentalists",
                ]
            )
            if not keep:
                continue

            paper = Paper()
            paper.init_from_scholarly(pub)
            self.add_citations_from_paper(paper)

        print(f"Initialized {len(self.papers)} citations for the major Galaxy papers.\n")

    def init_from_json(self, json_fp: str) -> None:
        """
        Initialize papers from a JSON file.

        Args:
            json_fp (str): Path to the JSON file containing paper data.
        """
        papers_data = shared.load_json(json_fp)
        self.papers = []
        for p in papers_data:
            paper = Paper()
            paper.init_from_json(p)
            self.papers.append(paper)

    def add_citations_from_paper(self, paper: Paper) -> None:
        """
        Add citations from a paper to the collection.

        Args:
            paper (Paper): The paper whose citations will be added.
        """
        self.papers.extend(paper.get_citations())

    def clean_papers(self) -> None:
        """
        Clean the papers collection by removing duplicates and papers with incorrect years.
        """
        print("Cleaning citations to remove duplicates and publications with incorrect years...")
        titles: list[str] = []
        clean_papers = []
        print(f"Before cleaning: {len(self.papers)} papers")
        for paper in self.papers:
            # Skip duplicates and papers with incorrect years
            if paper.get_title() in titles or paper.get_year() <= 2005:
                continue
            clean_papers.append(paper)
            titles.append(paper.get_title())
        self.papers = clean_papers
        print(f"After cleaning: {len(self.papers)} papers")

    def filter_given_tags(self, kwd_fp: str) -> None:
        """
        Filter papers based on keywords and add groups to matching papers.

        Args:
            kwd_fp (str): Path to the YAML file containing keywords and groups.
        """
        print("Filtering citations based on keywords and adding groups...")
        filtered_papers = []
        kwd = shared.load_yaml(kwd_fp)
        print(f"Before filtering: {len(self.papers)} papers")
        for paper in self.papers:
            if paper.has_kwd(kwd["tags"]):
                paper.add_groups_given_keywords(kwd["groups"])
                filtered_papers.append(paper)
        self.papers = filtered_papers
        print(f"After filtering: {len(self.papers)} papers")

    def export_to_dict(self) -> List[Dict[str, Any]]:
        """
        Export papers to a list of dictionaries.

        Returns:
            List[dict]: A list of dictionaries representing each paper.
        """
        return [paper.__dict__ for paper in self.papers]

    def export_to_tsv(self, output_fp: str, add_subgroups: bool = False) -> None:
        """
        Export papers to a TSV file.

        Args:
            output_fp (str): Path to the output TSV file.
            add_subgroups (bool): If True, include subgroup columns in the output.
        """
        renaming = {"title": "Title", "year": "Year", "journal": "Journal"}
        df = pd.DataFrame(self.export_to_dict()).rename(columns=renaming).fillna("")
        groups = pd.DataFrame(df["groups"].to_list())
        df = df[["Title", "Year", "Journal"]]
        if add_subgroups:
            for column in groups.columns:
                df[column] = groups[column].apply(lambda x: ", ".join(str(i) for i in x))
        df.to_csv(output_fp, sep="\t", index=False)


def extract_citations(all_json_fp: str, all_yaml_fp: str, all_tsv_fp: str, run_test: bool = False) -> None:
    """
    Extract citations from major Galaxy papers, clean them, and export to JSON, YAML, and TSV.

    Args:
        all_json_fp (str): Path to save the JSON file with all extracted citations.
        all_yaml_fp (str): Path to save the YAML file with all extracted citations.
        all_tsv_fp (str): Path to save the TSV file with all extracted citations.
        run_test (bool): If True, run a small test with limited data.
    """


def main() -> None:
    """
    Parse command-line arguments and execute the appropriate function.
    """
    parser = argparse.ArgumentParser(description="Extract and Filter Citations from Major Galaxy Papers")
    subparser = parser.add_subparsers(dest="command")

    # Extract Citation Subcommand
    extract = subparser.add_parser("extract", help="Extract all citations from major Galaxy papers")
    extract.add_argument("--all-json", "-o", required=True, help="Filepath to JSON with all extracted citations")
    extract.add_argument("--all-yaml", "-y", required=True, help="Filepath to YAML with all extracted citations")
    extract.add_argument("--all-tsv", "-t", required=True, help="Filepath to TSV with all extracted citations")
    extract.add_argument(
        "--test",
        "-a",
        action="store_true",
        default=False,
        required=False,
        help="Run a small test with limited data",
    )

    # Filter Citation Subcommand
    filterwf = subparser.add_parser("filter", help="Filter citations based on keywords and groups")
    filterwf.add_argument(
        "--all-json",
        "-a",
        required=True,
        help="Filepath to JSON with all extracted citations",
    )
    filterwf.add_argument(
        "--filtered-json",
        "-j",
        required=True,
        help="Filepath to JSON with filtered citations",
    )
    filterwf.add_argument(
        "--filtered-yaml",
        "-y",
        required=True,
        help="Filepath to YAML with filtered citations",
    )
    filterwf.add_argument(
        "--filtered-tsv",
        "-t",
        required=True,
        help="Filepath to TSV with filtered citations",
    )
    filterwf.add_argument(
        "--keywords",
        "-k",
        help="Path to a YAML file with keywords to filter citations and define groups and subgroups",
    )

    args = parser.parse_args()

    if args.command == "extract":
        citations = Papers()
        citations.init_from_major_publications(args.test)
        citations.clean_papers()
        shared.export_to_json(citations.export_to_dict(), args.all_json)
        shared.export_to_yml(citations.export_to_dict(), args.all_yaml)
        citations.export_to_tsv(args.all_tsv)
    elif args.command == "filter":
        citations = Papers()
        citations.init_from_json(args.all_json)
        citations.filter_given_tags(args.keywords)
        shared.export_to_json(citations.export_to_dict(), args.filtered_json)
        shared.export_to_yml(citations.export_to_dict(), args.filtered_yaml)
        citations.export_to_tsv(args.filtered_tsv, add_subgroups=True)


if __name__ == "__main__":
    main()
