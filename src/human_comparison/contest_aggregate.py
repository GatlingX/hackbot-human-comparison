from typing import Dict, List, Callable, Any
from loguru import logger as log
from human_comparison.contest_processor import (
    ContestProcessor,
    Warden,
    LocalWardenContainer,
    ContestInput,
)
from human_comparison.utils.toolbox import set_logger


class GlobalWardenStats:
    name: str
    total_findings: int
    total_high: int
    total_medium: int
    total_issues: int
    contest_participations: int
    avg_findings_per_contest: float

    def __init__(self, warden: Warden, report_issues: int):
        self.name = warden.name
        self.total_findings = warden.get_total_findings()
        self.total_high = warden.findings_high
        self.total_medium = warden.findings_medium
        self.total_issues = report_issues
        self.contest_participations = 1
        self.avg_findings_per_contest = warden.get_total_findings()
        self.avg_findings_per_issues = float(self.total_findings) / float(self.total_issues)

    def update(self, warden: Warden, exclusive: bool, report_issues: int) -> None:
        assert warden.name == self.name
        if exclusive and warden.get_total_findings() == 0:
            return
        self.total_findings += warden.get_total_findings()
        self.total_high += warden.findings_high
        self.total_medium += warden.findings_medium
        self.total_issues += report_issues
        self.contest_participations += 1
        self.avg_findings_per_contest = float(self.total_findings) / float(
            self.contest_participations
        )
        self.avg_findings_per_issues = float(self.total_findings) / float(self.total_issues)

    def __repr__(self) -> str:
        return f"GlobalWardenStats(name={self.name}, total_findings={self.total_findings}, total_high={self.total_high}, total_medium={self.total_medium}, contest_participations={self.contest_participations}, avg_findings_per_contest={self.avg_findings_per_contest})"


class GlobalWardenContainer:
    """Container for wardens in all contests"""

    _wardens_stats: Dict[str, GlobalWardenStats]
    _exclusive: bool

    def __init__(self, exclusive: bool):
        self._wardens_stats = {}
        self._exclusive = exclusive

    def get_all_wardens(self) -> List[GlobalWardenStats]:
        return list(self._wardens_stats.values())

    def get_warden(self, warden_name: str) -> GlobalWardenStats:
        if warden_name not in self._wardens_stats:
            raise ValueError(f"Warden {warden_name} not found")
        return self._wardens_stats[warden_name]

    def update_warden_stats(self, wardens: LocalWardenContainer, report_issues: int) -> None:
        for warden in wardens.get_wardens().values():
            if warden.name not in self._wardens_stats:
                self._wardens_stats[warden.name] = GlobalWardenStats(warden, report_issues)
            else:
                self._wardens_stats[warden.name].update(warden, self._exclusive, report_issues)

    def sort_wardens(
        self,
        sort_by: Callable[[GlobalWardenStats], Any] = lambda x: x.avg_findings_per_contest,
        reverse=True,
    ) -> List[GlobalWardenStats]:
        sorted_wardens = sorted(self._wardens_stats.values(), key=sort_by, reverse=reverse)
        return sorted_wardens

    def _get_warden_stats_str(self, sort_by: Callable[[GlobalWardenStats], Any]) -> str:
        # Filter wardens with total findings > 0
        hm_wardens = [stats for stats in self._wardens_stats.values() if stats.total_findings > 0]
        sorted_hm_wardens = sorted(hm_wardens, key=sort_by, reverse=True)
        stats_str = f"\n  Total H/M wardens: {len(hm_wardens)}\n"
        stats_str += "\n".join([f"  - {warden.name}: {warden}" for warden in sorted_hm_wardens])
        if self._exclusive:  # Changed from _inclusive to not _exclusive
            # Filter wardens with total findings = 0
            no_findings_wardens = [
                stats for stats in self._wardens_stats.values() if stats.total_findings == 0
            ]
            sorted_no_findings_wardens = sorted(no_findings_wardens, key=sort_by, reverse=True)
            stats_str += f"\n  Total wardens with no findings: {len(no_findings_wardens)}\n"
            stats_str += "\n".join(
                [f"  - {warden.name}: {warden}" for warden in sorted_no_findings_wardens]
            )

        return stats_str

    def __repr__(self) -> str:
        return f"GlobalWardenContainer(\n{self._get_warden_stats_str(lambda x: x.avg_findings_per_contest)}\n)"


class ContestAggregator:
    def __init__(
        self,
        exclusive: bool = False,
        verbose: bool = False,
        debug: bool = False,
    ):
        self._exclusive = exclusive
        self._verbose = verbose or debug
        self._debug = debug
        self._global_wardens = GlobalWardenContainer(exclusive=exclusive)
        set_logger()

    def get_warden(self, warden_name: str) -> Warden:
        return self._global_wardens.get_warden(warden_name)

    def get_warden_stats(self) -> List[GlobalWardenStats]:
        return self._global_wardens.get_warden_stats()

    def process_contests(self, contests: List[ContestInput]) -> None:
        for contest in contests:
            contest_processor = ContestProcessor(
                exclusive=self._exclusive, verbose=self._verbose, debug=self._debug
            )
            set_logger(contest.repo_name)
            report = contest_processor.process_contest(contest)
            if report is None:
                continue
            self._global_wardens.update_warden_stats(report.wardens)
            log.debug(report)
            log.debug("********" * 10)

        set_logger()
        log.debug(self._global_wardens)

    def get_top_performer_stats(self, contests: List[ContestInput]) -> None:
        for contest in contests:
            set_logger(contest.repo_name)
            contest_processor = ContestProcessor(
                exclusive=self._exclusive, verbose=self._verbose, debug=self._debug
            )
            report = contest_processor.process_contest(contest)
            if report is None:
                continue
            self._global_wardens.update_warden_stats(report.wardens, len(report.issues))

        set_logger()

        total_ratio = 0.0
        num_wardens = float(len(self._global_wardens.get_all_wardens()))
        log.info(f"Total number of wardens on all contests: {num_wardens}")
        # Sort wardens by average findings per issues
        sorted_wardens = self._global_wardens.sort_wardens(lambda x: x.avg_findings_per_issues)
        # Get top 10% of wardens sorted by avg findings per issues
        num_top_wardens = max(1, int(num_wardens * 0.1))  # At least 1 warden
        top_wardens = sorted_wardens[:num_top_wardens]  # Get first N since sorted ascending

        log.info(f"Number of top wardens: {num_top_wardens}")
        # Get max lengths for alignment
        max_name_len = max(len(w.name) for w in top_wardens)
        max_findings_len = max(len(str(w.total_findings)) for w in top_wardens)
        max_issues_len = max(len(str(w.total_issues)) for w in top_wardens)
        max_contests_len = max(len(str(w.contest_participations)) for w in top_wardens)
        if num_wardens > 0:
            for warden_stats in top_wardens:
                if warden_stats.total_findings == 0:
                    continue
                log.info(
                    f"- {warden_stats.name:<{max_name_len}} findings: {warden_stats.total_findings:>{max_findings_len}}, issues: {warden_stats.total_issues:>{max_issues_len}}, contests: {warden_stats.contest_participations:>{max_contests_len}}, avg_findings_per_issues: {warden_stats.avg_findings_per_issues:.2f}"
                )
                if warden_stats.total_issues > 0:
                    total_ratio += warden_stats.total_findings / float(warden_stats.total_issues)
            avg = total_ratio / len(top_wardens)
            log.info(f"Average ratio of findings/total_reports: {avg:.2f}")
