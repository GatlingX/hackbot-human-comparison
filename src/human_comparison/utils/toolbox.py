import requests
from urllib.parse import urlparse
from typing import List
import os
import sys
from loguru import logger as log
import csv


def is_valid_web_address(url: str | None) -> bool:
    """
    Check if the given string is a valid web address using urlparse.

    Args:
        url (str): The string to check.

    Returns:
        bool: True if the string is a valid web address, False otherwise.
    """
    if url is None:
        return False
    if url == "":
        return False
    if isinstance(url, float):
        return False

    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def contest_loader(contests_file: str) -> list:
    """
    Load contest data from a CSV file.

    This function reads a CSV file named 'contests.csv' and returns a list of dictionaries,
    where each dictionary represents a contest with its details.

    Returns:
        list: A list of dictionaries, each containing contest details.
    """
    contests = []
    try:
        with open(contests_file, mode="r") as file:
            csv_reader = csv.DictReader(file)
            contests = list(csv_reader)
            return contests

    except FileNotFoundError:
        raise FileNotFoundError(
            f"Error: File not found {contests_file}. Please run the scraper first."
        )


def download_report_md(
    repo_url: str,
    github_api_key: str,
) -> str:
    """
    Downloads the report.md file from a c4rena findings repository.
    """
    # Convert the repository URL to raw content URL format
    raw_url = repo_url.replace("github.com", "raw.githubusercontent.com")
    raw_url = f"{raw_url}/refs/heads/main/report.md"
    # Make the request to download the repository
    response = requests.get(
        raw_url,
        headers={
            "Authorization": f"token {github_api_key}",
            "Accept": "application/vnd.github.raw+json",
        },
        stream=False,
        timeout=10,
    )

    # Check if the request was successful
    if response.status_code == 200:

        # Extract the raw markdown content from the response
        raw_content = response.text

        # Return the raw markdown content directly
        return raw_content

    else:
        # Raise an exception if the request was not successful
        raise requests.exceptions.HTTPError(
            f"Failed to download repository: {response.status_code}"
        )


def get_repo_name(input: str) -> str:
    if input.startswith("https://"):
        return "-".join(input.split("/")[-1].split("-")[:-1])
    elif input.endswith(".md"):
        return input.split(".")[0].split("/")[-1]
    else:
        return input


def get_md_files(path: str) -> List[str]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Error: {path} does not exist, exiting")

    # Initialize list to store .md files to process
    md_files_to_process = []

    # Check if input is a single .md file or a directory
    if path.endswith(".md"):
        if os.path.isfile(path):
            md_files_to_process.append(path)
        else:
            raise FileNotFoundError(f"Error: {path} does not exist, exiting")
    else:
        # Get all .md files from directory
        md_files_to_process = [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".md")]

        if not md_files_to_process:
            raise FileNotFoundError(f"Error: No .md files found in {path}, exiting")
    return md_files_to_process


def set_logger(repo_name: str = None, debug: bool = False):
    log.remove()  # Remove any existing handlers
    format = None
    if repo_name:
        format = (
            f"<level>{{level: <8}}</level> | <cyan>{repo_name}</cyan> | <level>{{message}}</level>"
        )
    else:
        format = "<level>{level: <8}</level> | <cyan>{message}</cyan>"

    log.add(
        sys.stdout,
        format=format,
        level="INFO" if not debug else "DEBUG",
    )
