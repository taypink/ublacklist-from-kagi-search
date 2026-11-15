import logging
import re
import sys
from pathlib import Path
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

TARGET_URL = "https://kagi.com/stats?stat=insights"
OUTPUT_FILE = Path("rules/kagi-most-blocked.txt")

DOMAIN_PATTERN = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,15}$",
    re.IGNORECASE,
)


def is_valid_domain(candidate: str) -> bool:
    domain = candidate.strip().lower()
    if not domain or domain == "kagi.com" or domain.endswith(".kagi.com"):
        return False
    return bool(DOMAIN_PATTERN.match(domain))


def extract_most_blocked_domains() -> list[str]:
    logger.info("请求 Kagi Insights 页面: %s", TARGET_URL)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(TARGET_URL, headers=headers, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        logger.error("请求 Kagi 页面失败: %s", exc)
        sys.exit(1)

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select("tbody.leaderboard_body tr")
    if not rows:
        logger.error("未找到 tbody.leaderboard_body 表格行，页面结构可能已变更")
        sys.exit(1)

    seen: set[str] = set()
    domains: list[str] = []

    for tr in rows:
        first_td = tr.find("td")
        if not first_td:
            continue
        cleaned = first_td.get_text(strip=True).lower()
        if is_valid_domain(cleaned) and cleaned not in seen:
            seen.add(cleaned)
            domains.append(cleaned)

    return domains


def main() -> None:
    domains = extract_most_blocked_domains()
    if not domains:
        logger.error("提取结果为空，终止写入以保护现有文件")
        sys.exit(1)

    rules = [f"*://*.{d}/*" for d in domains]
    header = [
        "# Title: uBlacklist from Kagi Search Insights",
        "# Source: https://kagi.com/stats?stat=insights",
        "",
    ]
    new_content = "\n".join(header + rules) + "\n"

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_FILE.exists() and OUTPUT_FILE.read_text(encoding="utf-8") == new_content:
        logger.info("规则内容无变化（共 %d 条），无需覆写", len(rules))
        return

    OUTPUT_FILE.write_text(new_content, encoding="utf-8")
    logger.info("成功写入 %s（共 %d 条规则）", OUTPUT_FILE, len(rules))


if __name__ == "__main__":
    main()