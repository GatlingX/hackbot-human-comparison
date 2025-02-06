import re
from typing import Dict, List, Tuple, Callable, Any
from dataclasses import dataclass
from loguru import logger as log
from human_comparison.utils.known_replacements import KnownReplacements
from human_comparison.utils.mdprocessor import MdProcessor

# Regex to extract issue title, severity and id from the issue title
issue_title_regex = re.compile(r"## \[\[(H|M)-(\d+)\] ((?:\[[^\]]*\]|[^\]])*)\]\(https?://[^\)]+\)")

# Regex to extract issue title, severity and id from the issue title without hyperlink
issue_title_regex_nohyperlink = re.compile(r"## \[(H|M)-(\d+)\] (.*)")


# Sanitize special characters in the "Submitted by" line
def replace_special_chars(text: str) -> str:
    return text.replace("&#95;", "_").replace("\\_", "_").replace("&lowbar;", "_")


# Sanitize final characters in the "Submitted by" line
def replace_final_chars(text: str) -> str:
    if text.endswith("*.\n"):
        return text[:-3] + "\n"
    elif text.endswith(".*\n"):
        return text[:-3] + "\n"
    elif text.endswith("*\n"):
        return text[:-2] + "\n"
    elif text.endswith("_\n"):
        return text[:-2] + "\n"
    return text


@dataclass
class ContestInput:
    repo_name: str
    contest_url: str
    raw_report: str


@dataclass
class Issue:
    title: str
    severity: str
    id: int
    uid: int
    found_by: "LocalWardenContainer"
    repo_name: str


@dataclass
class Warden:
    name: str
    findings: List[Issue]
    findings_high: int
    findings_medium: int

    def get_name(self) -> str:
        return self.name

    def get_total_findings(self) -> int:
        assert len(self.findings) == self.findings_high + self.findings_medium
        return len(self.findings)

    def __repr__(self) -> str:
        return f"Warden(name={self.get_name()}, N findsings={self.get_total_findings()}, findings_high={self.findings_high}, findings_medium={self.findings_medium})"


class LocalWardenContainer:
    """Container for wardens in one contest"""

    _wardens: Dict[str, Warden]

    def __init__(self):
        self._wardens = {}

    def get_wardens(self) -> List[Warden]:
        return self._wardens

    def get_warden(self, warden_name: str) -> Warden:
        return self._wardens[warden_name]

    def set_warden(self, warden_name: str, warden: Warden) -> None:
        self._wardens[warden_name] = warden

    def get_total_findings(self) -> int:
        return sum(warden.get_total_findings() for warden in self._wardens)

    def get_warden_findings(self, warden_name: str) -> int:
        return self.get_warden(warden_name).get_total_findings()

    def sort_wardens(
        self, sort_by: Callable[[Warden], Any] = lambda x: x[1].get_total_findings()
    ) -> Dict[str, Warden]:
        return sorted(self._wardens.items(), key=sort_by, reverse=True)

    def prune_wardens(self) -> None:
        self._wardens = [w for w in self._wardens if w.get_total_findings() > 0]

    def __repr__(self) -> str:
        wardens_str = " ".join([warden_name for warden_name, _ in self._wardens.items()])
        return f"LocalWardenContainer(\n{wardens_str}\n)"


@dataclass
class ContestReport:
    repo_name: str
    repo_url: str
    wardens: LocalWardenContainer
    issues: List[Issue]

    def __repr__(self):
        return f"ContestReport(repo_name={self.repo_name}, repo_url={self.repo_url}"


class ContestProcessor:
    def __init__(
        self,
        exclude_zero_score: bool = False,
        upload: bool = False,
        verbose: bool = False,
        debug: bool = False,
    ):
        self._exclude_zero_score = exclude_zero_score
        self._upload = upload
        self._verbose = verbose or debug
        self._debug = debug
        self._wardens = LocalWardenContainer()
        self._issues = []
        self._bots = []
        self._typos = {}
        self._repo_name = None
        self._raw_report = None
        self._contest_url = None

    def _debug_messages(self):
        if not self._debug:
            return

        log.debug("********" * 10)
        findings_count = sum(1 for warden in self._wardens.get_wardens() if warden.findings)
        log.debug(f"Wardens that found High or Medium severity issues ({findings_count})")
        for warden in self._wardens.get_wardens():
            if warden.findings:
                log.debug(warden.name)
                for issue in warden.findings:
                    log.debug(f" - {issue.uid}-[{issue.severity}-{issue.id}]: {issue.title}")

        log.debug("********" * 10)
        no_findings_count = sum(1 for warden in self._wardens.get_wardens() if not warden.findings)
        log.debug(f"Wardens that did not find High or Medium severity issues ({no_findings_count})")
        for warden in self._wardens.get_wardens():
            if not warden.findings:
                log.debug(warden.name)

        log.debug("********" * 10)
        log.debug(f"Issues found ({len(self._issues)}) per warden")
        for issue in self._issues:
            log.debug(f"Issue {issue.uid}-[{issue.severity}-{issue.id}]: {issue.title}")
            for warden in issue.found_by.values():
                log.debug(f"  - {warden.name}")

    def _set_known_replacements(self):
        self._bots = KnownReplacements.get_bots(self._repo_name)
        self._typos = KnownReplacements.get_typos(self._repo_name)

    def _extract_issue_info(self, text: str) -> Tuple[str, int, str]:
        """Extract severity, id and title from issue header.

        Args:
            text (str): Text containing issue header in format '## [[H-02] Title](url)'

        Returns:
            tuple[str, int, str]: Tuple containing (severity, id number, title)
        """
        if not text.startswith("## [") and not text.startswith("# "):
            log.debug(f"Input '{text[:10]}...' is not an issue title, skipping")
            return None
        match = issue_title_regex.search(text)
        if not match:
            log.debug("No issue title with hyperlink found, retrying without hyperlink")
            match = issue_title_regex_nohyperlink.search(text)
        if not match:
            log.warning("Failed to extract issue info, skipping")
            return None

        severity = match.group(1)  # H or M
        id_num = int(match.group(2))  # Convert "02" to 2
        title = match.group(3)

        return severity, id_num, title

    def _extract_submitted_by(self, text: str) -> List[str]:
        """Extract list of submitter names from issue text.

        Args:
            text (str): Text containing issue details including "Submitted by" line
            typos (Dict[str, str]): Dictionary mapping known typos to correct names

        Returns:
            List[str]: List of submitter names extracted from text

        The function parses the "Submitted by" line in the issue text to extract submitter names.
        It handles various formats including:
        - Names with hyperlinks
        - Names with special characters
        - Names with comments/annotations
        - Multiple names separated by commas
        - Known typos that need to be corrected
        """
        line = None
        # Parse the text to find the "submitted by" line
        for line in text.split("\n"):
            # print(f"Line: {line}")
            if line.startswith("*Submitted by "):
                line = line.replace("*Submitted by ", "")
                break
            elif line.startswith("_Submitted by "):
                line = line.replace("_Submitted by ", "")
                break
        if line is None:
            log.error("No submitted by line found")
            exit(1)
        line = line + "\n"
        log.debug(f"Raw Line: {line}")

        # Clean up the line to make parsing easier (though inefficient)
        # Remove "also found by" and "and"
        line = line.replace("also found by ", "")
        line = line.replace(" and ", ", ")
        # Replace special characters
        line = replace_special_chars(line)
        # Replace endings only if they match exactly at the end
        line = replace_final_chars(line)

        log.debug(f"Cleaned Line: {line}")

        comment_queue = []  # Stack to track nested comments/hyperlinks
        name_buffer = []  # Buffer to accumulate characters for a name
        names = []  # Final list of names

        # Parse the line to extract names, char by char
        for char in line:
            if char == "(":
                comment_queue.append(char)
                continue
            elif char == ")":
                if comment_queue and comment_queue[-1] == "(":
                    comment_queue.pop()
                else:
                    log.error("Unmatched closing parenthesis")
                    exit(1)
                continue
            elif char == "[":
                continue
            elif char == "]":
                continue
            elif char == "," and not comment_queue:
                # Only split on commas outside of comments/hyperlinks
                if name_buffer:
                    name = "".join(name_buffer).strip()
                    if name in self._typos.keys():
                        name = self._typos[name]
                    names.append(name)
                    name_buffer = []
            elif not comment_queue:
                # Only collect characters when not in comments/hyperlinks
                name_buffer.append(char)

        # Add final name if buffer not empty
        if name_buffer:
            names.append("".join(name_buffer).strip())

        log.debug(f"Names: {names}")
        return names

    def _extract_wardens(self, md_data: str) -> LocalWardenContainer:
        """Extract list of warden names from report text."""
        md_wardens = None
        for md in md_data:
            if (
                "Topic" in md.metadata
                and md.metadata["Topic"] == "Overview"
                and md.metadata["Item"] == "Wardens"
            ):
                log.debug(md.metadata)
                md_wardens = md
                break
        line_counter = 1
        for line in md_wardens.page_content.split("\n"):
            if line.startswith("1. ") or line.startswith(f"{line_counter}. "):
                no_index = (
                    line.split("1. ")[1]
                    if line.startswith("1. ")
                    else line.split(f"{line_counter}. ")[1]
                )
                warden_name = None
                if no_index.startswith("["):
                    warden_name = no_index.split("[")[1].split("]")[0]
                else:
                    warden_name = no_index.strip()
                if "(" in warden_name:
                    warden_name = warden_name.split("(")[0].strip()
                warden_name = replace_special_chars(warden_name)

                self._wardens.set_warden(
                    warden_name,
                    Warden(
                        name=warden_name,
                        findings=[],
                        findings_high=0,
                        findings_medium=0,
                    ),
                )

                line_counter += 1

        for bot in self._bots:
            self._wardens.set_warden(
                f"bot-{bot}",
                Warden(name=f"bot-{bot}", findings=[], findings_high=0, findings_medium=0),
            )

        if self._debug:
            log.debug(f"All wardens ({len(self._wardens.get_wardens())} total)")
            log.debug("********" * 10)
            self._wardens.sort_wardens()
            for warden_name in self._wardens.get_wardens():
                log.debug(f"  - {warden_name}")

        return self._wardens

    def _extract_issues(self, md_data: str) -> List[Issue]:
        """Extract list of issues from report text."""
        # Filter the previous result to keep only high and medium risk issues
        issues_md = MdProcessor.filter_topic(md_data)

        # Categorize based on their index and drop the markdown language
        categorized_md = [MdProcessor.split(i, [("###", "Details")], True) for i in issues_md]

        # Filter the results to keep only the description, the impact and the proof of concept
        issues_filtered = [MdProcessor.filter_issue(i) for i in categorized_md]

        log.debug(f"Found {len(issues_filtered)} high and medium severity issues")

        # Process each issue to get the number of submitters and organize the data
        uid = 1
        for issue in issues_filtered:
            submitters = self._extract_submitted_by(issue[0])
            issue_info = self._extract_issue_info(issue[0])
            found_by = {}
            issue_data = None
            if issue_info:
                severity, id, title = issue_info
                log.debug(f"Issue {uid}-[{severity}-{id}] ({len(submitters)}): {title}")
                issue_data = Issue(
                    title=title,
                    severity=severity,
                    id=id,
                    uid=uid,
                    found_by=found_by,
                    repo_name=self._repo_name,
                )
            else:
                log.trace("No issue info found")
                continue
            for submitter in submitters:
                if submitter in self._bots:
                    submitter = f"bot-{submitter}"
                try:
                    warden = self._wardens.get_warden(submitter)
                except KeyError:
                    log.trace(f"Warden {submitter} is a bot, skipping")
                    continue
                issue_data.found_by[submitter] = warden
                warden.findings.append(issue_data)
                if severity == "H":
                    warden.findings_high += 1
                else:
                    warden.findings_medium += 1
            self._issues.append(issue_data)
            uid += 1
        return self._issues

    def _extract_top_stats(self) -> Tuple[int, int, LocalWardenContainer]:
        # If exclusive mode, remove wardens with 0 findings before calculating stats
        if self._exclude_zero_score:
            # Filter out wardens with no findings
            self._wardens.prune_wardens()

        # Sort wardens by total findings (high + medium)
        sorted_wardens = self._wardens.sort_wardens()
        # Calculate cutoff indices for top 10% and 50%
        total_wardens = len(sorted_wardens)
        top_10_cutoff = max(1, round(total_wardens * 0.1))
        top_50_cutoff = max(1, round(total_wardens * 0.5))
        # Access the Warden object from the tuple (warden_name, warden)
        top_10_min = sorted_wardens[top_10_cutoff - 1][1].get_total_findings()
        top_50_min = sorted_wardens[top_50_cutoff - 1][1].get_total_findings()

        if self._verbose:
            log.info(f"Top 10% performers ({top_10_cutoff} wardens) [{top_10_min} total]")
            for warden_name, warden in sorted_wardens[:top_10_cutoff]:
                log.info(
                    f"  - {warden.name}: {warden.findings_high} high, {warden.findings_medium} medium"
                )

        if self._verbose:
            log.info(f"Top 50% performers ({top_50_cutoff} wardens) [{top_50_min} total]")
            for warden_name, warden in sorted_wardens[:top_50_cutoff]:
                log.info(
                    f"  - {warden.name}: {warden.findings_high} high, {warden.findings_medium} medium"
                )

        findings_list = [warden[1].get_total_findings() for warden in sorted_wardens]
        return top_10_min, top_50_min, findings_list

    def process_contest(self, contest: ContestInput) -> ContestReport:
        """Process a single contest report.

        Args:
            contest (ContestInput): Contest input containing repo name, url and raw report
            inclusive (bool): Include wardens with no findings
            verbose (bool): Enable verbose output
            debug (bool): Enable debug logging

        Returns:
            ContestReport: Report containing contest details, wardens and issues
        """
        self._repo_name = contest.repo_name
        self._raw_report = contest.raw_report
        self._contest_url = contest.contest_url

        self._set_known_replacements()

        log.debug(f"Processing contest: {self._repo_name}")

        md_processor = MdProcessor()
        md_data = md_processor.split(self._raw_report)

        self._extract_wardens(md_data)

        self._extract_issues(md_data)

        if len(self._issues) == 0:
            log.warning("No High or Medium severity issues found in this contest, skipping")
            return

        self._debug_messages()

        report = ContestReport(
            repo_name=self._repo_name,
            repo_url=self._contest_url,
            wardens=self._wardens,
            issues=self._issues,
        )

        return report
