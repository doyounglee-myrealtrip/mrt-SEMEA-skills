#!/usr/bin/env python3
"""
Caret 녹취록 완료 웹훅 수신 서버

Caret에서 녹취록이 완료되면 이 서버로 POST 요청이 옵니다.
그러면 Claude API를 호출해 자동으로 회의록을 작성하고 Confluence + Slack으로 전송합니다.

실행 방법:
  pip install flask anthropic requests
  python3 caret_webhook.py

Caret 웹훅 URL 설정:
  http://your-server-ip:5001/webhook/caret
"""

import json
import hmac
import hashlib
from pathlib import Path
from flask import Flask, request, jsonify
import anthropic

app = Flask(__name__)

def load_config():
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path) as f:
        return json.load(f)

def verify_caret_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Caret 웹훅 서명 검증"""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

def process_with_claude(transcription: str, meeting_title: str) -> str:
    """Claude API로 녹취록 요약 + Confluence/Slack 처리"""
    config = load_config()

    skill_path = Path(__file__).parent.parent / "SKILL.md"
    skill_content = skill_path.read_text(encoding="utf-8")

    client = anthropic.Anthropic(api_key=config.get("anthropic_api_key", ""))

    prompt = f"""
{skill_content}

---

아래 회의 녹취록을 위의 스킬 지시에 따라 처리해주세요.
스크립트 실행은 실제로 하지 말고, 요약 결과와 Confluence에 올릴 내용, Slack 메시지 내용을 JSON으로 반환해주세요.

출력 형식:
{{
  "title": "회의 제목",
  "confluence_content": "Confluence 위키 마크업",
  "slack_summary": "핵심 내용 bullet 3줄",
  "slack_actions": "액션 아이템 목록"
}}

녹취록:
{transcription}
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text

@app.route("/webhook/caret", methods=["POST"])
def caret_webhook():
    config = load_config()

    # 서명 검증
    signature = request.headers.get("X-Caret-Signature", "")
    if not verify_caret_signature(request.data, signature, config["caret"]["webhook_secret"]):
        return jsonify({"error": "Invalid signature"}), 401

    data = request.json
    transcription = data.get("transcript", "")
    meeting_title = data.get("title", "회의")

    if not transcription:
        return jsonify({"error": "No transcription"}), 400

    print(f"📥 녹취록 수신: {meeting_title}")

    # Claude로 처리
    result_text = process_with_claude(transcription, meeting_title)

    try:
        result = json.loads(result_text)
    except json.JSONDecodeError:
        return jsonify({"error": "Claude 응답 파싱 실패"}), 500

    # Confluence 페이지 생성
    import subprocess
    confluence_result = subprocess.run(
        ["python3", "post_confluence.py",
         "--title", result["title"],
         "--content", result["confluence_content"]],
        capture_output=True, text=True,
        cwd=Path(__file__).parent
    )
    confluence_data = json.loads(confluence_result.stdout.strip().split("\n")[-1])

    if not confluence_data.get("success"):
        return jsonify({"error": "Confluence 생성 실패"}), 500

    # Slack DM 전송
    slack_result = subprocess.run(
        ["python3", "send_slack_dm.py",
         "--title", result["title"],
         "--url", confluence_data["url"],
         "--summary", result["slack_summary"],
         "--actions", result["slack_actions"]],
        capture_output=True, text=True,
        cwd=Path(__file__).parent
    )

    print(f"✅ 처리 완료: {result['title']}")
    return jsonify({"success": True, "confluence_url": confluence_data["url"]})

if __name__ == "__main__":
    print("🚀 Caret 웹훅 서버 시작 (포트 5001)")
    app.run(host="0.0.0.0", port=5001)
