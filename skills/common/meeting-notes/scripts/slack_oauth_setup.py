#!/usr/bin/env python3
"""
Slack OAuth 설정 스크립트

처음 한 번만 실행하면 돼요.
실행하면 브라우저가 열리고 Slack 로그인 후 자동으로 토큰이 저장됩니다.

실행 방법:
  pip install flask requests
  python3 slack_oauth_setup.py
"""

import json
import secrets
import threading
import webbrowser
from pathlib import Path
from urllib.parse import urlencode
import requests
from flask import Flask, request

CONFIG_PATH = Path(__file__).parent.parent / "config.json"
REDIRECT_URI = "http://localhost:8888/callback"
SCOPES = "chat:write,im:write,users:read"

app = Flask(__name__)
auth_result = {}
state_token = secrets.token_urlsafe(16)


def load_config():
    if not CONFIG_PATH.exists():
        example = CONFIG_PATH.parent / "config.example.json"
        import shutil
        shutil.copy(example, CONFIG_PATH)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


@app.route("/callback")
def callback():
    if request.args.get("state") != state_token:
        return "❌ 보안 오류 (state 불일치)", 400

    code = request.args.get("code")
    if not code:
        return f"❌ 오류: {request.args.get('error', '알 수 없는 오류')}", 400

    config = load_config()
    slack_cfg = config["slack"]

    # 코드를 토큰으로 교환
    response = requests.post("https://slack.com/api/oauth.v2.access", data={
        "client_id": slack_cfg["client_id"],
        "client_secret": slack_cfg["client_secret"],
        "code": code,
        "redirect_uri": REDIRECT_URI,
    })
    data = response.json()

    if not data.get("ok"):
        return f"❌ 토큰 발급 실패: {data.get('error')}", 400

    # 토큰 저장
    bot_token = data["access_token"]
    authed_user_id = data.get("authed_user", {}).get("id", "")

    config["slack"]["bot_token"] = bot_token
    if authed_user_id:
        config["slack"]["my_user_id"] = authed_user_id
    save_config(config)

    auth_result["done"] = True
    print("\n✅ Slack 연동 완료! 토큰이 config.json에 저장되었습니다.")

    shutdown = request.environ.get("werkzeug.server.shutdown")
    if shutdown:
        threading.Thread(target=shutdown).start()

    return """
    <html><body style="font-family:sans-serif;text-align:center;padding:60px">
    <h2>✅ Slack 연동 완료!</h2>
    <p>이 창을 닫아도 됩니다.</p>
    </body></html>
    """


def main():
    config = load_config()
    slack_cfg = config.get("slack", {})

    client_id = slack_cfg.get("client_id", "")
    client_secret = slack_cfg.get("client_secret", "")

    if not client_id or client_id.startswith("여기에"):
        print("❌ config.json의 slack.client_id를 먼저 채워주세요.")
        print("   → api.slack.com/apps에서 앱 만들고 Client ID를 복사해주세요.")
        return

    if not client_secret or client_secret.startswith("여기에"):
        print("❌ config.json의 slack.client_secret을 먼저 채워주세요.")
        return

    auth_url = "https://slack.com/oauth/v2/authorize?" + urlencode({
        "client_id": client_id,
        "scope": SCOPES,
        "redirect_uri": REDIRECT_URI,
        "state": state_token,
    })

    print("🌐 브라우저에서 Slack 로그인 화면이 열립니다...")
    threading.Timer(1.0, lambda: webbrowser.open(auth_url)).start()
    app.run(port=8888, debug=False)


if __name__ == "__main__":
    main()
