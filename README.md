# Weekly Team Sync Tool

Web-based tool for submitting weekly team sync responses directly to GitHub issues.

## Quick Start

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python weekly_team_sync.py
```

## Prerequisites

- Python 3.8+
- GitHub CLI (`gh auth login`)
- Repository access permissions

## How It Works

1. Finds current week's team meeting issue (with `team-meeting` label)
2. Opens web form in your browser
3. Displays Question of the Week from the issue
4. Submit responses → auto-posts as GitHub comment

## Configuration

Update repository in `weekly_team_sync.py`:
```python
url = "https://api.github.com/repos/YOUR_ORG/YOUR_REPO/issues"
```

## Questions

1. How have you been this week?
2. Your response to the question of the week (QOTW)
3. Do you have any accounts at risk?
4. What challenges are you working on?
5. What did you learn this week that others should know?
6. What have you explored with AI this week?
7. Anything else on your mind?
8. Any upcoming time off?
9. Any L&D scheduled?

## Troubleshooting

**No weekly issue found**: Check for open issue with `team-meeting` label from past 7 days

**Auth error**: Run `gh auth login`

**Import error**: Activate venv and run `pip install -r requirements.txt`