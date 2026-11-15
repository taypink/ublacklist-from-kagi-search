import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

README_FILE = Path("README.md")
STATE_FILE = Path(".state/upstream_state.json")
KAGI_FILE = Path("rules/kagi-most-blocked.txt")
MERGED_FILE = Path("rules/merged-subscriptions.txt")
ALL_IN_ONE_FILE = Path("rules/all.txt")

# 兼容 standard (/branch/path) 与 refs (/refs/heads/branch/path) 两种 GitHub Raw 链接格式
RAW_URL_REGEX = re.compile(
    r"^https://raw\.githubusercontent\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/(?:refs/heads/)?(?P<branch>[^/]+)/(?P<path>.+)$"
)
TABLE_HEADER_REGEX = re.compile(
    r"^\|\s*name\s*\|\s*URL\s*\|\s*Description\s*\|\s*Status\s*\|$",
    re.IGNORECASE,
)


def build_github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ublacklist-from-kagi-search-bot",
    }
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        logger.info("未检测到 GITHUB_TOKEN，本地使用匿名 API 配额（60次/小时）")
    return headers


def fetch_latest_commit_info(
    owner: str, repo: str, branch: str, file_path: str, headers: dict[str, str]
) -> tuple[str | None, datetime | None]:
    api_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params = {
        "path": unquote(file_path),
        "sha": branch,
        "per_page": 1,
    }
    try:
        resp = requests.get(api_url, headers=headers, params=params, timeout=20)
        if resp.status_code != 200:
            logger.warning(
                "GitHub API 返回异常 [%s/%s/%s]: HTTP %d",
                owner,
                repo,
                file_path,
                resp.status_code,
            )
            return None, None

        commits = resp.json()
        if not commits or not isinstance(commits, list):
            return None, None

        latest = commits[0]
        sha = latest.get("sha")
        date_str = latest.get("commit", {}).get("committer", {}).get("date")
        if not sha or not date_str:
            return None, None

        commit_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return sha, commit_dt
    except Exception as exc:
        logger.error("请求 GitHub API 失败 [%s/%s/%s]: %s", owner, repo, file_path, exc)
        return None, None


def evaluate_status(commit_dt: datetime | None, now_utc: datetime) -> str:
    if commit_dt is None:
        return "⚠️ Error / Not Found"
    days_elapsed = (now_utc - commit_dt).days
    ym_str = commit_dt.strftime("%Y-%m")
    if days_elapsed <= 365:
        return f"✅ Active ({ym_str})"
    return f"❌ Possibly unmaintained ({ym_str})"


def is_valid_ublacklist_rule(line: str) -> bool:
    """校验是否为合法的 uBlacklist 匹配模式或正则表达式规则"""
    clean = line.lstrip("@")
    if clean.startswith(("*://", "http://", "https://")):
        return True
    if clean.startswith("/") and len(clean) > 2 and "/" in clean[1:]:
        return True
    return False


def extract_clean_rules(text: str, source_label: str = "") -> set[str]:
    rules: set[str] = set()
    skipped_count = 0
    lines = text.splitlines()

    # 跳过文件开头的 YAML frontmatter (--- ... ---)
    start_idx = 0
    for idx, raw in enumerate(lines):
        if raw.strip():
            if raw.strip() == "---":
                for end_idx in range(idx + 1, len(lines)):
                    if lines[end_idx].strip() == "---":
                        start_idx = end_idx + 1
                        break
            break

    for raw_line in lines[start_idx:]:
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if is_valid_ublacklist_rule(line):
            rules.add(line)
        else:
            skipped_count += 1

    if skipped_count > 0:
        logger.warning(
            "源 [%s] 中有 %d 行不符合 uBlacklist 规则语法（如 hosts 格式），已自动过滤",
            source_label,
            skipped_count,
        )
    return rules


def write_if_changed(target_path: Path, content: str) -> bool:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists() and target_path.read_text(encoding="utf-8") == content:
        return False
    target_path.write_text(content, encoding="utf-8")
    return True


def download_and_merge_rules(valid_urls: list[str]) -> set[str]:
    merged_rules: set[str] = set()
    for url in valid_urls:
        try:
            logger.info("下载上游规则: %s", url)
            resp = requests.get(url, timeout=25)
            resp.raise_for_status()
            extracted = extract_clean_rules(resp.text, source_label=url.split("/")[-1])
            logger.info("  -> 提取有效规则 %d 条", len(extracted))
            merged_rules.update(extracted)
        except Exception as exc:
            logger.error("下载规则失败，已跳过 [%s]: %s", url, exc)

    header = [
        "# Title: Merged Upstream uBlacklist Subscriptions",
        "# Description: Deduplicated rules aggregated from GitHub sources",
        "",
    ]
    sorted_rules = sorted(merged_rules)
    new_content = "\n".join(header + sorted_rules) + "\n"

    if write_if_changed(MERGED_FILE, new_content):
        logger.info("已更新 %s（共 %d 条去重规则）", MERGED_FILE, len(sorted_rules))
    else:
        logger.info("%s 内容无变化（共 %d 条）", MERGED_FILE, len(sorted_rules))

    return merged_rules


def rebuild_all_in_one_file(upstream_rules: set[str] | None = None) -> None:
    combined_rules: set[str] = set()
    if KAGI_FILE.exists():
        combined_rules.update(extract_clean_rules(KAGI_FILE.read_text(encoding="utf-8"), "kagi"))

    if upstream_rules is not None:
        combined_rules.update(upstream_rules)
    elif MERGED_FILE.exists():
        combined_rules.update(extract_clean_rules(MERGED_FILE.read_text(encoding="utf-8"), "merged"))

    if not combined_rules:
        logger.warning("无可用规则，跳过生成 %s", ALL_IN_ONE_FILE)
        return

    header = [
        "# Title: uBlacklist All-in-One Ruleset (Kagi Search + Upstreams)",
        "# Description: Combined and deduplicated uBlacklist subscription file",
        "",
    ]
    sorted_all = sorted(combined_rules)
    new_content = "\n".join(header + sorted_all) + "\n"

    if write_if_changed(ALL_IN_ONE_FILE, new_content):
        logger.info("已更新全量订阅文件 %s（共 %d 条去重规则）", ALL_IN_ONE_FILE, len(sorted_all))
    else:
        logger.info("%s 内容无变化（共 %d 条）", ALL_IN_ONE_FILE, len(sorted_all))


def load_previous_state() -> dict[str, str]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict[str, str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    if not README_FILE.exists():
        logger.error("未找到 README.md，终止执行")
        return

    lines = README_FILE.read_text(encoding="utf-8").splitlines()
    headers = build_github_headers()
    now_utc = datetime.now(timezone.utc)

    in_table = False
    separator_passed = False
    updated_lines: list[str] = []
    readme_changed = False

    valid_urls: list[str] = []
    current_shas: dict[str, str] = {}

    for line in lines:
        stripped = line.strip()

        if not in_table:
            if TABLE_HEADER_REGEX.match(stripped):
                in_table = True
                separator_passed = False
            updated_lines.append(line)
            continue

        if in_table and not separator_passed:
            if stripped.startswith("|") and "---" in stripped:
                separator_passed = True
                updated_lines.append(line)
                continue
            in_table = False
            updated_lines.append(line)
            continue

        if in_table and separator_passed:
            if not stripped.startswith("|"):
                in_table = False
                updated_lines.append(line)
                continue

            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) < 4:
                updated_lines.append(line)
                continue

            name, url, description, _old_status = cells[0], cells[1], cells[2], cells[3]
            match = RAW_URL_REGEX.match(url)

            if not match:
                logger.warning("URL 格式不符合 GitHub Raw 规范: %s", url)
                new_status = "⚠️ Error / Not Found"
            else:
                sha, commit_dt = fetch_latest_commit_info(
                    owner=match.group("owner"),
                    repo=match.group("repo"),
                    branch=match.group("branch"),
                    file_path=match.group("path"),
                    headers=headers,
                )
                new_status = evaluate_status(commit_dt, now_utc)
                if sha is not None:
                    valid_urls.append(url)
                    current_shas[url] = sha

            new_line = f"| {name} | {url} | {description} | {new_status} |"
            if new_line != line:
                readme_changed = True
            updated_lines.append(new_line)

    if readme_changed:
        README_FILE.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
        logger.info("已回写更新 README.md 状态表格")

    previous_shas = load_previous_state()
    need_merge = (current_shas != previous_shas) or (not MERGED_FILE.exists())

    upstream_rules: set[str] | None = None
    if need_merge:
        logger.info("检测到上游 SHA 变化或本地合并文件缺失，开始拉取并合并规则")
        upstream_rules = download_and_merge_rules(valid_urls)
        save_state(current_shas)
    else:
        logger.info("上游 Commit SHA 未变化，跳过重新下载")

    rebuild_all_in_one_file(upstream_rules)


if __name__ == "__main__":
    main()