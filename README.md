# ublacklist-from-kagi-search

A serverless, automated **uBlacklist** filter ruleset powered by GitHub Actions.   
基于 GitHub Actions 的无服务器自动化uBlacklist搜索引擎过滤规则仓库。

1.**Kagi Search Insights Extraction**: Automatically fetches the most **Blocked** and **Lowered** domains from Kagi Search Insights to generate uBlacklist rules.
	自动抓取Kagi 搜索引擎的统计洞察数据中的 blocked、lowered数据，自动生成一份ublacklist列表

2.**Upstream Monitoring & Deduplication**：Periodically checks upstream subscription repositories via GitHub API, tracks maintenance status, and merges deduplicated rules.
	通过 GitHub Actions 定时检测上游订阅源的活跃状态，自动合并去重。



## Subscription Links / 订阅链接

- All-in-One (Kagi Insights + Upstreams) / 全量汇总：
  `https://raw.githubusercontent.com/taypink/ublacklist-from-kagi-search/main/rules/all.txt`
- Kagi Insights Only (Blocked & Lowered) / 仅 Kagi 洞察：
  `https://raw.githubusercontent.com/taypink/ublacklist-from-kagi-search/main/rules/kagi-most-blocked.txt`
- Upstreams Only (Deduplicated) / 仅上游订阅源去重：
  `https://raw.githubusercontent.com/taypink/ublacklist-from-kagi-search/main/rules/merged-subscriptions.txt`

## Upstream subcription list / 上游订阅源列表

| name | URL | Description | Status |
| --- | --- | --- | --- |
| uBlock-Origin-dev-filter | [global.txt](https://raw.githubusercontent.com/quenhus/uBlock-Origin-dev-filter/main/dist/other_format/uBlacklist/global.txt) | 屏蔽机翻 GitHub、Stack Overflow | ❌ Possibly unmaintained (2025-04) |
| TMW BL wikifarms | [wikifarms.all.txt](https://raw.githubusercontent.com/codeshell/blocklists/main/by-format/ublacklist/wikifarms.all.txt) | wiki.gg、Indie Wiki Buddy 信任的 wiki 站点 | ✅ Active (2026-11) |
| Conspiracy Media blacklist | [ublacklist-conspiracy-media-full.txt](https://raw.githubusercontent.com/RubenKelevra/ublacklist_conspiracy/refs/heads/master/ublacklist-conspiracy-media-full.txt) | 屏蔽大多数阴谋论媒体网站（地平说、反疫苗等） | ❌ Possibly unmaintained (2025-02) |
| ublacklist_fakenews | [ublacklist-fakenews-media-full.txt](https://raw.githubusercontent.com/RubenKelevra/ublacklist_fakenews/refs/heads/master/ublacklist-fakenews-media-full.txt) | 屏蔽大多数已知的假新闻与内容农场媒体 | ❌ Possibly unmaintained (2025-02) |
| Google-Chinese-Results-Blocklist | [uBlacklist_subscription.txt](https://raw.githubusercontent.com/cobaltdisco/Google-Chinese-Results-Blocklist/master/uBlacklist_subscription.txt) | 屏蔽百家号、CSDN 及云厂商采集站 | ✅ Active (2026-03) |
| uBlockOrigin-HUGE-AI-Blocklist | [list_uBlacklist.txt](https://raw.githubusercontent.com/laylavish/uBlockOrigin-HUGE-AI-Blocklist/refs/heads/main/list_uBlacklist.txt) | 屏蔽纯 AI 站点和垃圾 AI 内容农场 | ❌ Possibly unmaintained (2025-10) |

## Approach / 实现原理

1. Lightweight HTTP Scraping / 轻量级 HTTP 抓取

   Dropped headless browsers (Playwright) in favor of direct HTTP requests. 
   Switches between Kagi's `Blocked` (`k=-2`) and `Lowered` (`k=-1`) SSR leaderboards via URL query parameters for fast, low-overhead extraction.     
   不用Playwright，直接通过 HTTP 请求解析服务端页面，再用URL参数 `k=-2`（Blocked）与 `k=-1`（Lowered）切换并提取对应榜单。

2. Validation & Deduplication / 语法校验与全局去重
   Filters out non-uBlacklist syntax (e.g., hosts format or YAML frontmatter) and performs cross-source deduplication across Kagi lists and upstream subscriptions before sorting. 
   自动过滤非uBlacklist 语法(如 hosts 格式或 YAML 元信息)，并对 Kagi 榜单、多个上游订阅源进行去重&重排。

3. Automated CI/CD & Health Tracking / 自动化与状态追踪

   Uses GitHub Actions to inspect single-file commit history via the GitHub API (`Active` within 365 days vs. `Possibly unmaintained`), atomically updates rules only when upstream SHAs change, and logs execution history to prevent scheduled workflow deactivation.
   通过 GitHub Actions 调用 GitHub Commits API 检测上游订阅的单文件更新时间（365 天内→活跃），仅在 SHA 变更时更新规则集，并每个月执行一次，记录执行日志以防Github Action超60D被ban。
