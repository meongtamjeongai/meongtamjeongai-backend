# test_api.py
import json

import requests

# --- 설정 (본인의 환경에 맞게 수정) ---
BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@example.com"  # 관리자 계정 이메일
ADMIN_PASSWORD = "my-super-secret-password-123"  # 관리자 계정 비밀번호


def pretty_print(data):
    """JSON 데이터를 예쁘게 출력하는 함수"""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    access_token = None
    persona_id = None
    conversation_id = None

    # --- 1. 관리자 로그인하여 JWT 토큰 얻기 ---
    print("🚀 1. 관리자 계정으로 로그인 시도...")
    try:
        login_data = {"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        response = requests.post(f"{BASE_URL}/auth/token", data=login_data, timeout=5)
        response.raise_for_status()
        access_token = response.json().get("access_token")
        if not access_token:
            raise ValueError("응답에서 access_token을 찾을 수 없습니다.")
        print(f"✅ 로그인 성공! (토큰 일부: {access_token[:20]}...)")
    except Exception as e:
        print(f"💥 로그인 실패: {e}")
        if hasattr(e, "response"):
            pretty_print(e.response.json())
        return

    headers = {"Authorization": f"Bearer {access_token}"}

    # --- 2. 테스트용 페르소나 생성 ---
    print("\n🚀 2. 테스트용 페르소나 생성 시도...")
    try:
        persona_data = {
            "name": "API 테스터 냥이",
            "system_prompt": "너는 모든 답변을 '~다냥'으로 끝내는 고양이 AI다냥. 사용자의 질문에 항상 친절하게 대답해줘야 한다냥.",
            "description": "API 테스트를 위해 생성된 페르소나",
            "is_public": True,
        }
        response = requests.post(
            f"{BASE_URL}/personas/", headers=headers, json=persona_data, timeout=5
        )
        response.raise_for_status()
        persona_id = response.json().get("id")
        print(f"✅ 페르소나 생성 성공! (ID: {persona_id})")
    except Exception as e:
        print(f"💥 페르소나 생성 실패: {e}")
        if hasattr(e, "response"):
            pretty_print(e.response.json())
        return

    # --- 3. 생성된 페르소나와 대화방 생성 ---
    print("\n🚀 3. 테스트용 대화방 생성 시도...")
    try:
        convo_data = {"persona_id": persona_id, "title": "API 테스트 대화방"}
        response = requests.post(
            f"{BASE_URL}/conversations/", headers=headers, json=convo_data, timeout=5
        )
        response.raise_for_status()
        conversation_id = response.json().get("id")
        print(f"✅ 대화방 생성 성공! (ID: {conversation_id})")
    except Exception as e:
        print(f"💥 대화방 생성 실패: {e}")
        if hasattr(e, "response"):
            pretty_print(e.response.json())
        return

    # --- 4. 메시지 전송 및 구조화된 응답 확인 (핵심 테스트) ---
    print("\n🚀 4. 메시지 전송 및 AI 응답 테스트...")
    try:
        message_data = {"content": "안녕! 자기소개 좀 해줄래?"}
        response = requests.post(
            f"{BASE_URL}/conversations/{conversation_id}/messages/",
            headers=headers,
            json=message_data,
            timeout=30,
        )
        response.raise_for_status()
        print("✅ 메시지 전송 및 AI 응답 수신 성공!")

        # ⭐️⭐️⭐️ 변경된 부분: 새로운 응답 구조 검증 ⭐️⭐️⭐️
        chat_response = response.json()
        print("🔬 응답 구조 검증 시작...")

        required_keys = [
            "user_message",
            "ai_message",
            "suggested_user_questions",
            "is_ready_to_move_on",
        ]
        if all(key in chat_response for key in required_keys):
            print("  - ✅ 필수 키 4개가 모두 존재합니다.")
        else:
            raise ValueError(
                f"응답에 필수 키가 누락되었습니다. 누락된 키: {[k for k in required_keys if k not in chat_response]}"
            )

        if isinstance(chat_response.get("suggested_user_questions"), list):
            print(
                f"  - ✅ 'suggested_user_questions'가 리스트 형태입니다. (개수: {len(chat_response['suggested_user_questions'])})"
            )
        else:
            raise ValueError("'suggested_user_questions'가 리스트가 아닙니다.")

        print("🔬 응답 구조 검증 완료!")
        print("\n--- 최종 응답 (ChatMessageResponse) ---")
        pretty_print(chat_response)

    except Exception as e:
        print(f"💥 메시지 전송/응답 실패: {e}")
        if hasattr(e, "response") and e.response:
            try:
                pretty_print(e.response.json())
            except json.JSONDecodeError:
                print(f"Raw response: {e.response.text}")
        return


if __name__ == "__main__":
    main()
