
<p align="center">
  <img src="https://github.com/GatlingX/GatlingGun-Issues/assets/38335479/a66beb1a-7953-42bb-a30b-01b24417ea1c" alt="2" width="500">

</p>

<p align="center">
  <a href="https://x.com/gatling_x">
    <img src="https://img.shields.io/twitter/follow/gatling_x?style=for-the-badge&logo=x&logoColor=white" alt="Follow us on X">
  </a>
  <a href="https://t.me/+DwI1FhzS6hxkZmI0">
    <img src="https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white&label=join our community" alt="Join our community">
  </a>
</p>


# ♨️ Hackbot Human Comparison



## ♨️ Summary

This tool analyzes contest reports to compare human and bot performance in finding vulnerabilities. It processes contest data, extracts issues and their submitters, and provides statistics on warden performance. The analysis helps understand the effectiveness of human auditors versus automated tools by tracking high and medium severity findings across contests.

## 🚀 Usage Examples

By default the tool will extract the top 10% of wardens based on their score.

### Basic usage with C4Eval github reports

```
rye run python human_comparison_app.py -c foundry_repos.csv --github-api-key $GITHUB_PERSONAL_ACCESS_TOKEN
```

### Basic usage with C4Eval github reports and save raw reports (the directory path can be relative or absolute)

```
rye run python human_comparison_app.py -c foundry_repos.csv --github-api-key $GITHUB_PERSONAL_ACCESS_TOKEN --save-raw-reports /path/to/save/raw/reports
```

### Basic usage with C4Eval local reports
```
rye run python human_comparison_app.py -r /path/to/c4eval/reports
```

### Change the top percentile to extract stats for the human top 5%

```
rye run python human_comparison_app.py -c foundry_repos.csv --github-api-key $GITHUB_PERSONAL_ACCESS_TOKEN --top-percentile 0.95
```

Join our [Telegram Community](https://t.me/+DwI1FhzS6hxkZmI0)! We are here to answer questions and help you get the most out of our hackbot.
