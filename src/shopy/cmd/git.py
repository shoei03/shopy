from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import sleep

from dateutil.relativedelta import relativedelta

import shopy as sp


def get_monthly_commits(
    repo_path: str,
    branch: str = "main",
    start_date: str = "2023-01-01",
    end_date: str = "2024-12-31",
) -> tuple[str, str]:
    """
    各月の最後のコミットのハッシュとUTCのISO形式日時を取得する

    Returns:
        dict[str, tuple[commit_hash, commit_date]]
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    monthly_commits: dict[str, tuple[str, str]] = {}
    current = start

    while current <= end:
        next_month = current + relativedelta(months=1)
        since = current.strftime("%Y-%m-%d")
        until = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")

        cmd = (
            f"git log {branch} "
            f'--after="{since}" --before="{until}" '
            f"--pretty=format:'%H|%aI' --reverse"
        )

        commits = sp.run_cmd(cmd, cwd=repo_path)
        if commits:
            last_commit_line = commits[-1]
            if "|" in last_commit_line:
                commit_hash, commit_date = last_commit_line.split("|", 1)
                commit_date_utc = datetime.fromisoformat(commit_date).astimezone(
                    timezone.utc
                )
                monthly_key = since[:7]
                monthly_commits[monthly_key] = (commit_hash, commit_date_utc)

        current = next_month

        sorted_months = sorted(monthly_commits.keys())
        filtered_hashes = [monthly_commits[month][0] for month in sorted_months]
        filtered_dates = [monthly_commits[month][1] for month in sorted_months]

    return filtered_hashes, filtered_dates


def get_last_commit_date(repo_path: Path, limit_year: str) -> tuple[str, str]:
    all_commits: list[str] = sp.run_cmd(
        cmd=f"git log --before={limit_year}-01-01T00:00:00+00:00 --pretty=format:'%H|%aI' --reverse",
        cwd=repo_path,
    )
    last_commit_hash: str = all_commits[-1].split("|")[0]
    last_commit_date: str = all_commits[-1].split("|")[1]
    return last_commit_hash, last_commit_date


def reset_repo_state(repo_path: Path, commit_hash: str) -> None:
    sp.run_cmd(cmd=f"git reset --hard {commit_hash}", cwd=repo_path)
    sleep(2)
