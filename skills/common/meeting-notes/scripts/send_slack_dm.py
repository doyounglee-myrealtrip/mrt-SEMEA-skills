#!/usr/bin/env python3
"""Slack DM으로 회의록 요약을 전송하는 스크립트"""

import argparse
import json
import sys
from pathlib import Path
import requests

def load_config():
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        print("❌ config.json이 없어요. config.example.json을 복사해서 config.json을 만들고 값을 채워주세요.")
        sys.exit(1)
    with open(config_path) as f:
        return json.load(f)

def send_dm(title: str, url: str, summary: str, actions: str) -> dict:
    config = load_config()
    slack = config["slack"]

    # 메시지 블록 구성
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📋 회의록이 작성되었습니다"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{title}*"}
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*핵심 내용*\n{summary}"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*액션 아이템*\n{actions}"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"🔗 <{url}|Confluence에서 전체 회의록 보기>"}
        }
    ]

    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {slack['bot_token']}"},
        json={
            "channel": slack["my_user_id"],
            "blocks": blocks,
            "text": f"회의록 작성 완료: {title}"
        }
    )

    result = response.json()
    if result.get("ok"):
        print(f"✅ Slack DM 전송 완료")
        return {"success": True}
    else:
        print(f"❌ Slack 오류: {result.get('error')}")
        return {"success": False, "error": result.get("error")}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--actions", required=True)
    args = parser.parse_args()

    result = send_dm(args.title, args.url, args.summary, args.actions)
    print(json.dumps(result, ensure_ascii=False))
