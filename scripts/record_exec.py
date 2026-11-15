import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

RECORD_FILE = Path(".state/exec_record.md")
KAGI_FILE = Path("rules/kagi-most-blocked.txt")
MERGED_FILE = Path("rules/merged-subscriptions.txt")
ALL_IN_ONE_FILE = Path("rules/all.txt")
MAX_RECORDS = 36


def count_rules(file_path: Path) -> int:
    if not file_path.exists():
        return 0
    count = 0
    for line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("!"):
            count += 1
    return count


def format_status() -> str:
    kagi_out = os.getenv("KAGI_OUTCOME", "success").lower()
    up_out = os.getenv("UPSTREAM_OUTCOME", "success").lower()
    if kagi_out == "success" and up_out == "success":
        return "✅ Success"
    issues = []
    if kagi_out != "success":
        issues.append("Kagi")
    if up_out != "success":
        issues.append("Upstreams")
    return f"⚠️ Partial Error ({', '.join(issues)})"


def main() -> None:
    tz_cn = timezone(timedelta(hours=8))
    now_str = datetime.now(tz_cn).strftime("%Y-%m-%d %H:%M:%S")

    kagi_cnt = count_rules(KAGI_FILE)
    merged_cnt = count_rules(MERGED_FILE)
    all_cnt = count_rules(ALL_IN_ONE_FILE)
    status_str = format_status()

    new_row = f"| {now_str} | {kagi_cnt} | {merged_cnt} | {all_cnt} | {status_str} |"

    existing_rows: list[str] = []
    if RECORD_FILE.exists():
        for line in RECORD_FILE.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if (
                stripped.startswith("|")
                and not stripped.startswith("| Date")
                and "---" not in stripped
            ):
                existing_rows.append(stripped)

    updated_rows = [new_row] + existing_rows[: MAX_RECORDS - 1]

    content = [
        "# Execution Record",
        "",
        "自动运行日志（确保每次调度均产生有效提交，防止 GitHub Actions 因连续 60 天无活动被自动禁用）。",
        "",
        "| Date (UTC+8) | Kagi Rules | Upstream Rules | All-in-One Rules | Status |",
        "| --- | --- | --- | --- | --- |",
        *updated_rows,
        "",
    ]

    RECORD_FILE.parent.mkdir(parents=True, exist_ok=True)
    RECORD_FILE.write_text("\n".join(content), encoding="utf-8")
    logger.info("已更新执行记录 %s: %s", RECORD_FILE, new_row)


if __name__ == "__main__":
    main()