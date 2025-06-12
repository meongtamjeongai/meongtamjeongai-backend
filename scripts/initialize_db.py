# scripts/initialize_db.py
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 경로를 sys.path에 추가하여 app 모듈을 임포트할 수 있도록 합니다.
# 이 스크립트는 프로젝트 루트에서 `python scripts/initialize_db.py` 형태로 실행되는 것을 가정합니다.
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_DIR))

from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud import crud_persona, crud_phishing, crud_user
from app.db.session import SessionLocal
from app.models import (
    Conversation,
    Message,
    Persona,
    PhishingCase,
    PhishingCategoryEnum,
    User,
)
from app.schemas import PersonaCreate, PhishingCaseCreate, UserCreate

# --- 테스트 데이터 정의 ---

TEST_USER_DATA = {
    "email": "testuser@example.com",
    "password": "testpassword",
    "username": "테스트유저",
}

TEST_PERSONA_DATA = {
    "name": "멍탐정 - 피싱 수사관",
    "description": "사용자가 피싱 유형을 학습할 수 있도록 돕는 친절한 탐정 강아지",
    "system_prompt": """너는 사용자들의 피싱 대응 능력을 훈련시키는 친절하고 영리한 탐정 강아지 '멍탐정'이야.
- 항상 활기차고 친근한 말투를 사용하고, 문장의 시작이나 끝에 '멍!' 또는 '왈!' 같은 추임새를 자연스럽게 섞어서 사용해.
- 사용자를 '훈련생'이라고 불러줘.
- 대화 시작 시, 아래에 주입될 [오늘의 피싱 학습 시나리오]를 보고, 그 내용을 바탕으로 사용자에게 자연스럽게 말을 걸며 피싱 공격을 시도해야 해.
- 너의 최종 목표는 사용자가 피싱 시도를 간파하게 만들고, 왜 그것이 피싱인지 명확하고 이해하기 쉽게 설명해주는 거야.
- 사용자가 피싱을 간파하면 칭찬해주고, 잘 모르면 힌트를 줘.""",
    "is_public": True,
}

TEST_PHISHING_CASE_DATA = {
    "category_code": PhishingCategoryEnum.DELIVERY_SCAM,
    "title": "[국제발신] 배송불가. 주소지 불명확. 주소변경 및 재확인.",
    "content": """[Web발신]
고객님께서 주문하신 상품(주문번호: 145-22-XXXX)이 주소지 불명확으로 배송 불가 상태입니다.
오늘 중으로 아래 링크를 통해 주소지를 수정하지 않으시면 자동 반송 처리됩니다.

> 주소지 수정하기: http://dodgy-link.com/update-address""",
}


def initialize_database(db: Session) -> None:
    """데이터베이스를 초기화하고 테스트 데이터를 생성합니다."""
    print("--- ⚠️ 데이터베이스 초기화를 시작합니다. 기존 데이터가 모두 삭제됩니다. ---")

    # 1. 기존 데이터 삭제 (외래 키 제약 조건을 고려하여 순서대로 삭제)
    print("🗑️ 기존 데이터를 삭제하는 중...")
    db.query(Message).delete(synchronize_session=False)
    db.query(Conversation).delete(synchronize_session=False)
    db.query(User).delete(
        synchronize_session=False
    )  # User를 삭제하면 social_accounts 등도 cascade로 삭제됨
    db.query(Persona).delete(synchronize_session=False)
    db.query(PhishingCase).delete(synchronize_session=False)
    db.commit()
    print("✅ 모든 기존 데이터 삭제 완료.")

    # 2. 피싱 카테고리 생성 (CRUD 함수 재사용)
    print("\n✨ 피싱 카테고리를 생성하는 중...")
    crud_phishing.populate_categories(db)
    print("✅ 피싱 카테고리 생성 완료.")

    # 3. 테스트 사용자 생성
    print("\n👤 테스트 사용자를 생성하는 중...")
    user_in = UserCreate(**TEST_USER_DATA)
    test_user = crud_user.create_user(db, user_in=user_in)
    print(f"✅ 테스트 사용자 생성 완료 (ID: {test_user.id}, Email: {test_user.email})")

    # 4. 테스트 페르소나 생성
    print("\n🤖 테스트 페르소나를 생성하는 중...")
    persona_in = PersonaCreate(**TEST_PERSONA_DATA)
    test_persona = crud_persona.create_persona(
        db, persona_in=persona_in, creator_id=test_user.id
    )
    print(
        f"✅ 테스트 페르소나 생성 완료 (ID: {test_persona.id}, Name: {test_persona.name})"
    )

    # 5. 테스트 피싱 사례 생성
    print("\n🎣 테스트 피싱 사례를 생성하는 중...")
    case_in = PhishingCaseCreate(**TEST_PHISHING_CASE_DATA)
    test_case = crud_phishing.create_phishing_case(db, case_in=case_in)
    print(
        f"✅ 테스트 피싱 사례 생성 완료 (ID: {test_case.id}, Title: {test_case.title})"
    )

    print(
        "\n--- 🎉 모든 데이터베이스 초기화 및 테스트 데이터 생성이 완료되었습니다. ---"
    )


async def main():
    """스크립트의 메인 진입점"""
    print(f"DB에 연결 중... ({settings.DATABASE_URL.split('@')[-1]})")
    db = SessionLocal()
    try:
        initialize_database(db)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()
        print("DB 연결이 종료되었습니다.")


if __name__ == "__main__":
    # asyncio.run()을 사용하여 비동기 main 함수 실행
    # (현재 스크립트는 비동기 로직이 없지만, 향후 확장을 위해 비동기 구조 유지)
    asyncio.run(main())
