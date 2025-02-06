import argparse
from pathlib import Path
from human_comparison.contest_processor import ContestInput
from human_comparison.contest_aggregate import ContestAggregator
from human_comparison.utils.toolbox import (
    contest_loader,
    get_repo_name,
    get_md_files,
    download_report_md,
)


def get_contest_data_from_raw(raw_report: str, file_name: str) -> ContestInput:
    """
    Get contest data from a raw report (md file).
    """
    repo_name = file_name.split("/")[-1]
    contest_data = ContestInput(
        repo_name=repo_name,
        raw_report=raw_report,
        contest_url=file_name,
    )
    return contest_data


def get_contest_data_from_url(url: str, github_api_key: str) -> ContestInput:
    """
    Get contest data from a URL.
    """
    repo_name = get_repo_name(url)
    raw_report = download_report_md(url, github_api_key)
    contest_data = ContestInput(
        repo_name=repo_name,
        raw_report=raw_report,
        contest_url=url,
    )
    return contest_data


def save_raw_report(raw_report: str, file_path: Path) -> None:
    """
    Save the raw report to a file.
    """
    with open(file_path, "w") as f:
        f.write(raw_report)


def main(args: argparse.Namespace):
    """
    Main function to process the contest data.
    """
    contest_data = []
    if args.contests_csv_file:
        # Load contests from CSV file
        print(f"Loading contests from: {args.contests_csv_file}")
        contests = contest_loader(args.contests_csv_file)
        count = 1
        for contest in contests:
            print(
                f"\rLoading {contest['findingsRepo']} - {count}/{len(contests)}".ljust(100),
                end="\r",
            )
            contest_data.append(
                get_contest_data_from_url(contest["findingsRepo"], args.github_api_key)
            )
            if args.save_raw_reports:
                Path(args.save_raw_reports).mkdir(exist_ok=True)
                save_raw_report(
                    contest_data[-1].raw_report,
                    Path(args.save_raw_reports) / f"{contest_data[-1].repo_name}.md",
                )
            count += 1
        if args.save_raw_reports:
            print(f"Saved raw reports to: {args.save_raw_reports}.")
            print(
                f"You can now run the tool with the option --from-raw-path {args.save_raw_reports} instead of --contests_csv_file and --github-api-key."
            )
    else:
        # Load raw reports from a directory
        print(f"Loading raw reports from: {args.from_raw_path}")
        md_files_to_process = get_md_files(args.from_raw_path)
        for file in md_files_to_process:
            with open(file, "r") as f:
                raw_report = f.read()
                contest_data.append(get_contest_data_from_raw(raw_report, file))

    # Initialize the aggregator
    aggregator = ContestAggregator(
        exclude_zero_score=args.exclude_zero_score,
        top_percentile=float(args.top_percentile),
    )

    # Process the contest data, aggregat and compute stats
    aggregator.get_top_performer_stats(contest_data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Tool to load C4 reports and compute a score for the Archimedes Hackbot."
    )
    parser.add_argument(
        "-e",
        "--exclude-zero-score",
        help="Whether to exclude low severity issue contributors from the computation.",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "-p",
        "--top-percentile",
        help="The percentile of the top performers to compute the stats for.",
        default=0.9,
        action="store",
    )
    parser.add_argument(
        "-c",
        "--contests_csv_file",
        help="The path to the Code4rena contests CSV file to process.",
        default=None,
    )
    parser.add_argument(
        "-r",
        "--from-raw-path",
        help="The path to the raw report to process.",
        default=None,
        action="store",
    )
    parser.add_argument(
        "--github-api-key",
        help="The GitHub API key to use for downloading reports.",
        default=None,
        action="store",
    )
    parser.add_argument(
        "--save-raw-reports",
        help="Whether to save the raw reports to the given directory.",
        default=None,
    )
    args = parser.parse_args()

    if not args.contests_csv_file and not args.from_raw_path:
        parser.error("Either --contests_csv_file (-c) or --from-raw-path (-r) must be specified")
    if args.contests_csv_file and args.from_raw_path:
        parser.error(
            "Only one of --contests_csv_file (-c) or --from-raw-path (-r) can be specified"
        )
    if args.contests_csv_file and not args.github_api_key:
        parser.error("The GitHub API key must be specified when using --contests_csv_file (-c)")
    if args.from_raw_path and args.save_raw_reports:
        parser.error(
            "The save-raw-reports flag cannot be specified when using --from-raw-path (-r)"
        )
    main(args)
