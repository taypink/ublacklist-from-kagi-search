# ublacklist-from-kagi-search

基于 GitHub Actions 的无服务器（Serverless）自动化 **uBlacklist** 搜索引擎过滤规则仓库。

## 订阅链接

- **全量汇总规则集（Kagi 榜单 + 全部上游规则）**：
  `https://raw.githubusercontent.com/taypink/ublacklist-from-kagi-search/main/rules/all.txt`
- **仅 Kagi Search 屏蔽榜规则集**：
  `https://raw.githubusercontent.com/taypink/ublacklist-from-kagi-search/main/rules/kagi-most-blocked.txt`
- **仅上游订阅源聚合规则集**：
  `https://raw.githubusercontent.com/taypink/ublacklist-from-kagi-search/main/rules/merged-subscriptions.txt`

## 上游订阅源列表

## 上游订阅源列表

| name | URL | Description | Status |
| --- | --- | --- | --- |
| uBlock-Origin-dev-filter (ublacklist+global) | https://raw.githubusercontent.com/quenhus/uBlock-Origin-dev-filter/main/dist/other_format/uBlacklist/global.txt | 屏蔽机翻 GitHub、Stack Overflow | ❌ Possibly unmaintained (2025-04) |
| TMW BL wikifarms by codeshell | https://raw.githubusercontent.com/codeshell/blocklists/main/by-format/ublacklist/wikifarms.all.txt | wiki.gg、Indie Wiki Buddy 信任的 wiki 站点 | ✅ Active (2026-11) |
| Conspiracy Media blacklist | https://raw.githubusercontent.com/RubenKelevra/ublacklist_conspiracy/refs/heads/master/ublacklist-conspiracy-media-full.txt | 屏蔽大多数阴谋论媒体网站（如地平说、反疫苗或极端伪科学） | ❌ Possibly unmaintained (2025-02) |
| ublacklist_fakenews | https://raw.githubusercontent.com/RubenKelevra/ublacklist_fakenews/refs/heads/master/ublacklist-fakenews-media-full.txt | 屏蔽大多数已知的假新闻与内容农场媒体（注意：若为 hblock 格式将被自动跳过，建议确认仓库内是否有 ublacklist 前缀文件） | ❌ Possibly unmaintained (2025-02) |
| Google-Chinese-Results-Blocklist | https://raw.githubusercontent.com/cobaltdisco/Google-Chinese-Results-Blocklist/master/uBlacklist_subscription.txt | 百家号、xx云（腾讯、华为） | ✅ Active (2026-03) |
| uBlockOrigin-HUGE-AI-Blocklist | https://raw.githubusercontent.com/laylavish/uBlockOrigin-HUGE-AI-Blocklist/refs/heads/main/list_uBlacklist.txt | 仅屏蔽纯 AI 站点和垃圾 AI 内容农场 | ❌ Possibly unmaintained (2025-10) |
