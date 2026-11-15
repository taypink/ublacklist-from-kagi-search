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

KAGI_ENDPOINTS = {
    "Blocked": "https://kagi.com/stats?stat=insights&sub_ins=domains&k=-2",
    "Lowered": "https://kagi.com/stats?stat=insights&sub_ins=domains&k=-1",
}
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


def fetch_leaderboard_domains(category: str, url: str) -> list[str]:
    logger.info("请求 Kagi Insights [%s] 榜单: %s", category, url)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        logger.error("请求 Kagi [%s] 页面失败: %s", category, exc)
        sys.exit(1)

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select("tbody.leaderboard_body tr")
    if not rows:
        logger.error("Kagi [%s] 未找到 tbody.leaderboard_body 表格行，页面结构或参数可能已失效", category)
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

    if not domains:
        logger.error("Kagi [%s] 提取有效域名为 0 条，终止写入以保护现有规则", category)
        sys.exit(1)

    logger.info("Kagi [%s] 成功提取 %d 个有效域名", category, len(domains))
    return domains


def main() -> None:
    blocked_domains = fetch_leaderboard_domains("Blocked", KAGI_ENDPOINTS["Blocked"])
    lowered_domains = fetch_leaderboard_domains("Lowered", KAGI_ENDPOINTS["Lowered"])

    blocked_set = set(blocked_domains)
    unique_lowered = [d for d in lowered_domains if d not in blocked_set]
    overlap_count = len(lowered_domains) - len(unique_lowered)
    if overlap_count > 0:
        logger.info("Lowered 榜单中有 %d 个域名与 Blocked 重叠，已自动去重", overlap_count)

    blocked_rules = [f"*://*.{d}/*" for d in blocked_domains]
    lowered_rules = [f"*://*.{d}/*" for d in unique_lowered]
    total_count = len(blocked_rules) + len(lowered_rules)

    content_lines = [
        "# Title: uBlacklist from Kagi Search Insights (Blocked & Lowered)",
        "# Source: https://kagi.com/stats?stat=insights",
        "# Description: Most blocked (k=-2) and lowered (k=-1) domains from Kagi Search",
        "",
        "# === Kagi Insights: Blocked ===",
        *blocked_rules,
        "",
        "# === Kagi Insights: Lowered ===",
        *lowered_rules,
        "",
    ]
    new_content = "\n".join(content_lines)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_FILE.exists() and OUTPUT_FILE.read_text(encoding="utf-8") == new_content:
        logger.info("规则内容无变化（共 %d 条），无需覆写", total_count)
        return

    OUTPUT_FILE.write_text(new_content, encoding="utf-8")
    logger.info(
        "成功写入 %s（Blocked: %d 条, Lowered: %d 条, 合计: %d 条）",
        OUTPUT_FILE,
        len(blocked_rules),
        len(lowered_rules),
        total_count,
    )


if __name__ == "__main__":
    main()