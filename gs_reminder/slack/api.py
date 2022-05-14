import json
import os
from typing import Any, Dict, List

import requests

from ..bridge import BridgeUsername
from ..github.models.pull_request import PullRequest
from ..github.models.user import User


class Client:
    _usernames: List[BridgeUsername]
    _webhook_url: str

    def __init__(self, usernames: List[BridgeUsername]) -> None:
        self._usernames = usernames
        self._webhook_url = os.environ["SLACK_URL"]

    def _convert_github_to_slack(self, user: User) -> str:
        for username in self._usernames:
            if username.github == user.login:
                return username.slack
        else:
            return user.login

    def _get_section(self, pull: PullRequest) -> List[Dict[str, Any]]:
        # title section
        title_section: Dict[str, Any] = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"[#{pull.number}] <{pull.html_url}|{pull.title}> (_{pull.user.login}_)",
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Check",
                },
                "url": pull.html_url,
            },
        }

        # reviewer section
        reviewer_section: Dict[str, Any] = {"type": "context", "elements": []}
        if pull.requested_reviewers:
            reviewer_section["elements"] += [
                {
                    "type": "plain_text",
                    "text": "Waiting on",
                },
            ]
            for reviewer in pull.requested_reviewers:
                reviewer_section["elements"] += [
                    {
                        "type": "image",
                        "image_url": reviewer.avatar_url,
                        "alt_text": reviewer.login,
                    },
                    {"type": "mrkdwn", "text": self._convert_github_to_slack(user=reviewer)},
                ]
        else:
            reviewer_section["elements"] += [{"type": "plain_text", "text": "Waiting review by anyone."}]

        return [
            title_section,
            reviewer_section,
        ]

    def _build_block(self, repo: str, pulls: List[PullRequest]) -> List[Dict[str, Any]]:
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Pending review on _<https://github.com/{repo}|{repo}>_*"},
            },
        ]

        for section in map(lambda pull: self._get_section(pull=pull), pulls):
            blocks += section
        else:
            blocks += [
                {
                    "type": "divider",
                },
            ]

        return blocks

    def post(self, repo: str, pulls: List[PullRequest]) -> None:
        if not pulls:
            return

        payload: Dict[str, Any] = {
            "text": f"Waiting your review on {repo}.",
            "blocks": self._build_block(repo=repo, pulls=pulls),
        }

        requests.post(url=self._webhook_url, data=json.dumps(payload))
