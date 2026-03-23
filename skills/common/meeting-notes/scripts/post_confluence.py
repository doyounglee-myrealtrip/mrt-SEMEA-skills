#!/usr/bin/env python3
"""Confluence에 회의록 페이지를 생성하는 스크립트"""

import argparse
import json
import sys
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth

def load_config():
    config_path = Path(__file__).parent.parent / "config.json"
    if not config_path.exists():
        print("❌ config.json이 없어요. config.example.json을 복사해서 config.json을 만들고 값을 채워주세요.")
        sys.exit(1)
    with open(config_path) as f:
        return json.load(f)

def create_page(title: str, content: str) -> dict:
    config = load_config()
    cf = config["confluence"]

    url = f"{cf['base_url']}/wiki/rest/api/content"
    auth = HTTPBasicAuth(cf["username"], cf["api_token"])

    payload = {
        "type": "page",
        "title": title,
        "space": {"key": cf["space_key"]},
        "body": {
            "storage": {
                "value": content,
                "representation": "wiki"
            }
        }
    }

    response = requests.post(url, json=payload, auth=auth)

    if response.status_code == 200:
        page = response.json()
        page_url = f"{cf['base_url']}/wiki{page['_links']['webui']}"
        print(f"✅ Confluence 페이지 생성 완료: {page_url}")
        return {"success": True, "url": page_url, "id": page["id"]}
    else:
        print(f"❌ Confluence 오류 ({response.status_code}): {response.text}")
        return {"success": False, "error": response.text}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--content", required=True)
    args = parser.parse_args()

    result = create_page(args.title, args.content)
    print(json.dumps(result, ensure_ascii=False))
