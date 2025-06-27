# 🕵️‍♂️ 멍탐정 백엔드 서버

## 멍탐정 의 모든 서버 기능을 담당하는 FastAPI 기반 백엔드 프로젝트입니다.

---
## ✨ 주요 기능 (Key Features)

| 기능 분류 | 설명 | 사용 기술 |
| :--- | :--- | :--- |
| 🚀 **API 서버** | 비동기 처리를 통해 높은 성능을 제공하는 API 서버를 구축했습니다. | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi) ![Gunicorn](https://img.shields.io/badge/Gunicorn-499848?style=for-the-badge&logo=gunicorn) ![Uvicorn](https://img.shields.io/badge/Uvicorn-2d7ff9?style=for-the-badge&logo=uvicorn) |
| 💬 **AI 채팅** | 사용자와의 자연스러운 대화 및 동적 피싱 시나리오 생성을 담당합니다. | ![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8E77F0?style=for-the-badge&logo=google-gemini&logoColor=white) |
| 🔐 **인증** | 다양한 클라이언트와 사용자를 위한 유연하고 안전한 인증 시스템을 구현했습니다. | ![JWT](https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=jsonwebtokens) ![Firebase](https://img.shields.io/badge/Firebase-FFCA28?style=for-the-badge&logo=firebase) ![Naver](https://img.shields.io/badge/Naver-03C75A?style=for-the-badge&logo=naver&logoColor=white) ![Kakao](https://img.shields.io/badge/Kakao-FEE500?style=for-the-badge&logo=kakao&logoColor=black) ![Guest](https://img.shields.io/badge/Guest-90A4AE?style=for-the-badge&logo=ghost) |
| 🗃️ **데이터 관리** | ORM과 마이그레이션 도구를 통해 데이터베이스를 체계적으로 관리합니다. | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white) ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy) ![Alembic](https://img.shields.io/badge/Alembic-4E85A9?style=for-the-badge&logo=alembic) |
| 🐳 **개발/실행 환경** | 개발 및 배포 환경을 컨테이너화하여 일관성을 유지하고 이식성을 높였습니다. | ![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white) ![Docker Compose](https://img.shields.io/badge/Docker%20Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white) ![Dev Containers](https://img.shields.io/badge/Dev%20Containers-007ACC?style=for-the-badge&logo=visualstudiocode) |
| ⚙️ **배포 (CD)** | GitHub Actions를 통해 클라우드 인프라에 애플리케이션을 자동 배포합니다. | ![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-2088FF?style=for-the-badge&logo=githubactions) |
| ☁️ **클라우드 인프라** | 확장 가능하고 안정적인 서비스 운영을 위해 AWS 클라우드를 활용합니다. | ![AWS EC2](https://img.shields.io/badge/AWS%20EC2-FF9900?style=for-the-badge&logo=amazon-ec2&logoColor=white) ![AWS S3](https://img.shields.io/badge/AWS%20S3-FF9900?style=for-the-badge&logo=amazon-s3&logoColor=white) ![AWS ECR](https://img.shields.io/badge/AWS%20ECR-FF9900?style=for-the-badge&logo=amazon-ecr&logoColor=white) ![AWS SSM](https://img.shields.io/badge/AWS%20SSM-FF9900?style=for-the-badge&logo=aws-systems-manager&logoColor=white) |
| 👨‍💻 **관리자 기능** | 서비스의 주요 데이터(사용자, 대화 등)를 관리할 수 있는 API를 제공합니다. | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi) |
---

## 📊 아키텍처 다이어그램 (Architecture Diagram)

```mermaid
graph TD
    %% Tiers & Nodes
    subgraph "📱 Client Tier"
        Client[fa:fa-user Client]
    end

    subgraph "⚙️ Presentation Tier"
        APILayer("<b>API Layer</b><br>/api/v1/endpoints")
    end

    subgraph "🧠 Business Logic Tier"
        ServiceLayer("<b>Service Layer</b><br>/services")
    end

    subgraph "💾 Data Access Tier"
        CRUDLayer("<b>CRUD Layer</b><br>/crud")
    end

    subgraph "☁️ External & Database Tier"
        Database[fa:fa-database PostgreSQL DB]
        GeminiAPI[fa:fa-robot Google Gemini API]
        S3Storage[fa:fa-box-open AWS S3 Storage]
    end

    %% Request Flow (Solid)
    Client -- "Request" --> APILayer
    APILayer --> ServiceLayer
    ServiceLayer --> CRUDLayer
    ServiceLayer -- "Call" --> GeminiAPI
    ServiceLayer -- "Call" --> S3Storage
    CRUDLayer --> Database

    %% Response Flow (Dotted)
    Database -.->|"Data"| CRUDLayer
    CRUDLayer -.->|"Data"| ServiceLayer
    GeminiAPI -.->|"Response"| ServiceLayer
    S3Storage -.->|"Data"| ServiceLayer
    ServiceLayer -.->|"Data"| APILayer
    APILayer -.->|"Response"| Client
```

---

## 🌳 폴더 구조 (Directory Structure)

```
meongtamjeongai-backend/
├── 📂 app/                  #  FastAPI 애플리케이션 핵심 로직
│   ├── 📂 api/               # API 엔드포인트 및 라우팅
│   ├── 📂 core/              # 핵심 설정, 보안, 예외 처리
│   ├── 📂 crud/              # 데이터베이스 CRUD(Create, Read, Update, Delete) 함수
│   ├── 📂 db/                # 데이터베이스 세션 관리
│   ├── 📂 models/            # SQLAlchemy DB 모델(테이블) 정의
│   ├── 📂 schemas/           # Pydantic 데이터 유효성 검사 스키마
│   ├── 📂 services/          # 비즈니스 로직 처리
│   └── 📄 main.py            # FastAPI 앱의 메인 진입점
├── 📂 alembic/               # Alembic 데이터베이스 마이그레이션 관리
│   └── 📂 versions/          # DB 변경 이력 스크립트
├── 📂 .github/               # GitHub Actions CI/CD 워크플로우
├── 🐳 Dockerfile             # 프로덕션용 Docker 이미지 빌드 설계도
├── 🐳 docker-compose.yml     # 로컬 개발 환경 구성 (앱 + DB)
├── 📜 requirements.in        # 프로젝트 주요 파이썬 의존성 목록
└── 📜 requirements.txt       # 버전이 고정된 전체 의존성 목록
```

---

## 🛠️ 주요 라이브러리 및 기술 스택

| 분류 | 라이브러리 / 도구 | 역할 및 사용 이유 |
| :--- | :--- | :--- |
| **웹 프레임워크** | `FastAPI` | 고성능 비동기 웹 프레임워크. API 개발 생산성과 성능을 위해 선택했습니다. |
| **웹 서버** | `Gunicorn`, `Uvicorn` | `Gunicorn`이 `Uvicorn` 워커 프로세스를 관리하는 표준 프로덕션 구성으로, 안정성과 확장성을 확보합니다. |
| **데이터베이스** | `SQLAlchemy` | 파이썬 ORM의 표준. 파이썬 코드로 DB를 객체 지향적으로 다루기 위해 사용합니다. |
| | `Alembic` | `SQLAlchemy` 기반의 데이터베이스 마이그레이션 도구. DB 스키마 변경 이력을 체계적으로 관리합니다. |
| | `asyncpg` | `PostgreSQL`을 위한 고성능 비동기 드라이버. `SQLAlchemy`와 함께 비동기 DB 작업을 위해 사용합니다. |
| **데이터 유효성**| `Pydantic` | API 요청/응답 데이터의 유효성 검사 및 설정 관리를 위해 사용합니다. `FastAPI`의 핵심 요소입니다. |
| **인증/보안** | `python-jose`, `passlib` | `JWT` 토큰 생성 및 검증, 비밀번호 해싱 등 보안 관련 기능을 담당합니다. |
| **외부 연동** | `google-genai` | Google Gemini AI 모델과의 상호작용을 위한 공식 Python SDK입니다. |
| | `firebase-admin` | Firebase 서비스(인증 등)와 서버 간 통신을 위한 Python SDK입니다. |
| | `boto3` | AWS 서비스(S3, SSM 등)를 파이썬 코드로 제어하기 위한 공식 SDK입니다. |
| | `httpx` | 외부 API(소셜 로그인, Gemini 등)와 통신하기 위한 최신 비동기 HTTP 클라이언트입니다. |
| **API 문서** | `scalar-fastapi` | 현대적이고 사용하기 편리한 API 문서를 자동으로 생성하기 위해 사용합니다. |
| **파일 처리** | `python-multipart` | `FastAPI`에서 multipart/form-data 형식의 파일 업로드를 처리하기 위해 필요합니다. |
| | `Pillow` | 이미지의 MIME 타입 확인 등 서버 측에서 간단한 이미지 처리를 위해 사용합니다. |
| **성능 향상** | `uvloop` | `asyncio` 이벤트 루프를 대체하여 더 높은 성능을 내는 라이브러리. (Linux/macOS 환경에서 적용) |

---

## 🔬 주요 핵심 기능 및 코드

### 1. 비동기 AI 채팅 응답 처리 흐름

사용자가 메시지를 보냈을 때, 서버 내부에서 Gemini AI API와 상호작용하여 구조화된 응답을 받아 사용자에게 전달하기까지의 과정은 이 프로젝트의 핵심 기능 중 하나입니다. 전체 과정은 비동기로 처리되어 높은 성능을 보장합니다.

**처리 순서 다이어그램**
```mermaid
sequenceDiagram
    participant U as 📱 User
    participant A as ⚙️ API Layer<br>(messages.py)
    participant S as 🧠 Service Layer<br>(message_service.py)
    participant G as ☁️ Gemini Service<br>(gemini_service.py)
    participant D as 💾 DB (CRUD)

    U->>+A: POST /conversations/{id}/messages (메시지 전송)
    A->>+S: send_new_message(message_in) 호출
    S->>+D: 1. 이전 대화 내역(History) 조회
    D-->>-S: 대화 내역 반환
    S->>+G: 2. get_chat_response() 호출<br>(시스템 프롬프트 + 대화 내역 + 새 메시지)
    G-->>-S: 3. 구조화된 AI 응답 (JSON) 반환
    S->>+D: 4. 사용자 메시지 DB에 저장
    D-->>-S: 저장된 사용자 메시지 객체
    S->>+D: 5. AI 응답 메시지 DB에 저장
    D-->>-S: 저장된 AI 메시지 객체
    S-->>-A: 최종 응답 객체 (ChatMessageResponse) 반환
    A-->>-U: HTTP 201 Created (AI 응답 포함)
```

### 핵심 코드: send_new_message()

```
# app/services/message_service.py

class MessageService:
    # ... (초기화 및 다른 메소드 생략)

    async def send_new_message(
        self, conversation_id: int, message_in: MessageCreate, current_user: User
    ) -> ChatMessageResponse:
        # 1. 대화방 소유권 및 존재 여부 확인
        db_conversation = await self.get_conversation_for_user(conversation_id, current_user)

        # 2. DB에서 이전 대화 내역을 먼저 불러옴
        history = await crud_message.get_messages_by_conversation(
            self.db, conversation_id=conversation_id, limit=None, sort_asc=True
        )

        # 3. Gemini AI에 응답 요청
        try:
            gemini_response, _ = await self.gemini_service.get_chat_response(
                system_prompt=db_conversation.persona.system_prompt,
                history=history,
                user_message=message_in.content or "",
                phishing_case=db_conversation.applied_phishing_case,
                # ... (이미지 처리 등 기타 파라미터)
            )
        except Exception as e:
            # ... (오류 처리)

        # 4. 사용자 메시지를 DB에 저장
        user_db_message = await self.save_user_message(conversation_id, message_in)

        # 5. AI 응답 메시지를 DB에 저장
        ai_db_message = await self.save_ai_message(conversation_id, gemini_response)

        # 6. 최종 응답 객체 구성 및 반환
        return ChatMessageResponse(
            user_message=MessageResponse.from_orm(user_db_message),
            ai_message=MessageResponse.from_orm(ai_db_message),
            suggested_user_questions=gemini_response.suggested_user_questions,
            # ... (기타 응답 필드)
        )
```

### 2. 통합 인증 및 유연한 권한 관리

이 프로젝트는 다양한 인증 방식을 통합적으로 처리하고, API 엔드포인트별로 세밀한 접근 제어를 구현하여 보안성과 유연성을 모두 확보했습니다.

**인증 처리 흐름 다이어그램**

서버는 클라이언트의 요청 종류에 따라 각기 다른 인증 방식을 처리합니다.

1.  **내부 API 인증**: JWT 또는 API 키를 사용하여 서버 내부 자원에 접근합니다.
2.  **소셜 로그인 인증**: 네이버/카카오 등 외부 OAuth 제공자로부터 받은 토큰으로 사용자를 인증하고 서버의 JWT를 발급합니다.

```mermaid
sequenceDiagram
    participant C as 📱 Client
    participant A as ⚙️ API Endpoint
    participant L as 🔐 Auth Logic
    participant DB as 💾 Database
    participant Ext as ☁️ External Auth

    alt 내부 API 인증 (JWT / API Key)
        C->>+A: API 요청 (Header에 JWT/API Key 포함)
        Note over A: Depends(HasScope) 실행
        A->>+L: 사용자 및 권한 정보 요청
        L-->>-A: (User, Scopes) 반환
        Note over A: 권한 확인 후 로직 실행
        A-->>-C: API 응답
    end

    alt 소셜 로그인 (네이버/카카오)
        C->>+A: POST /social/{provider}/token<br>(Header에 Naver/Kakao Access Token 포함)
        A->>+L: 소셜 로그인 요청
        L->>+Ext: 1. 사용자 정보 요청<br>(Naver/Kakao API)
        Ext-->>-L: 2. 사용자 프로필 반환
        L->>+DB: 3. 사용자 조회 또는 생성 (get_or_create_social_user)
        DB-->>-L: 4. 서버 내부 User 객체 반환
        L-->>-A: 5. 서버용 JWT (Access/Refresh) 생성 및 반환
        A-->>-C: 서버 JWT 응답
    end

    alt Firebase 인증
        C->>+A: POST /auth/firebase/token<br>(Firebase ID Token 포함)
        A->>+L: Firebase 로그인 요청
        L->>+Ext: 1. 토큰 검증 (Firebase Admin SDK)
        Ext-->>-L: 2. 검증된 사용자 정보 반환
        L->>+DB: 3. 사용자 조회 또는 생성
        DB-->>-L: 4. 서버 내부 User 객체 반환
        L-->>-A: 5. 서버용 JWT (Access/Refresh) 생성 및 반환
        A-->>-C: 서버 JWT 응답
    end
```

### 핵심 코드: get_or_create_social_user

네이버/카카오 로그인 등 일반적인 소셜 로그인 처리 시, AuthService의 get_or_create_social_user 메소드가 사용됩니다. 이 함수는 소셜 플랫폼에서 얻어온 사용자 정보를 바탕으로 우리 서비스의 사용자를 조회하거나, 없는 경우 새로 생성하는 역할을 합니다.

```
# app/services/auth_service.py

class AuthService:
    # ...

    async def get_or_create_social_user(
        self,
        *,
        provider: SocialProvider,
        provider_user_id: str,
        email: Optional[str],
        username: Optional[str],
    ) -> User:
        """
        소셜 로그인 정보를 받아 사용자를 조회하거나 생성합니다.
        """
        # 1. (제공자, 제공자 ID)로 기존 소셜 계정 조회
        social_account = await crud_social_account.get_social_account_by_provider_and_id(
            self.db, provider=provider, provider_user_id=provider_user_id
        )
        if social_account:
            return social_account.user

        # 2. 소셜 계정이 없으면, 이메일로 기존 사용자 조회
        user = None
        if email:
            user = await crud_user.get_user_by_email(self.db, email=email)

        # 3. 이메일로도 사용자가 없으면, 신규 사용자 생성
        if not user:
            user_in = UserCreate(email=email, username=username)
            user = await crud_user.create_user(self.db, user_in=user_in)

        # 4. 새로 얻은 User 정보에 소셜 계정 정보 연결
        social_account_in = SocialAccountCreate(
            provider=provider, provider_user_id=provider_user_id
        )
        await crud_social_account.create_social_account(
            self.db, social_account_in=social_account_in, user_id=user.id
        )

        return user
```

## 💡 문제 해결 및 기술적 결정

이 프로젝트를 진행하며 마주했던 기술적 고민과 문제 해결 과정을 공유합니다.

### 1. 왜 Spring Boot 대신 FastAPI를 선택했는가?
<details>
Java와 Spring Boot 생태계의 안정성과 풍부한 기능은 큰 장점이지만, 이 프로젝트의 목표와 특성을 고려하여 다음과 같은 FastAPI의 강점을 활용하고자 했습니다.

*   **🚀 생산성과 성능**: Python의 간결한 문법과 FastAPI의 비동기(Async) 네이티브 지원은 적은 코드로도 높은 처리 성능을 낼 수 있게 해줍니다. 특히 I/O 작업이 잦은 AI API 연동 및 채팅 서비스에 매우 적합하다고 판단했습니다.
*   **👨‍💻 직관적인 개발 경험**: 타입 힌트(Type Hint)만으로 데이터 유효성 검사, 직렬화, API 문서 자동 생성이 모두 해결되는 FastAPI의 개발 경험은 Spring Boot의 보일러플레이트 코드(Boilerplate Code)를 줄여 핵심 비지니스 로직에 더 집중할 수 있게 했습니다.
*   **🧠 풍부한 AI/ML 생태계 활용**: **`spaCy`**, **`scikit-learn`**, **`Hugging Face Transformers`** 등 최첨단 자연어 처리 및 머신러닝 라이브러리는 Python을 중심으로 발전하고 있습니다. 향후 사용자의 대화 내용을 분석하여 피싱 의도를 더 정교하게 파악하거나, 감정 분석을 도입하는 등 **AI 기능을 고도화할 때, Python 생태계를 활용하는 것이 압도적으로 유리**하다고 판단했습니다. 이는 Java 생태계에서는 상대적으로 구현하기 어렵거나 더 많은 노력이 필요한 부분입니다.

물론, Spring Security나 Spring Data JPA처럼 강력하고 성숙한 라이브러리의 부재는 아쉬운 점이었습니다. 이를 해결하기 위해 다음과 같이 직접 구현하거나 대체 라이브러리를 적극적으로 활용했습니다.

*   **인증/인가**: `python-jose`와 `passlib`를 조합하고, FastAPI의 의존성 주입 시스템(`Depends`)을 활용하여 유연하고 재사용 가능한 인증/인가 레이어를 직접 설계했습니다.
*   **데이터베이스 관리**: `SQLAlchemy` ORM과 `Alembic` 마이그레이션 도구를 사용하여 Spring Data JPA 못지않은 체계적인 데이터 관리 환경을 구축했습니다.
</details>

### 2. 개발 과정에서의 트러블 슈팅: N+1 쿼리 문제 해결
<details>
사용자의 대화 목록을 조회하는 API에서 성능 저하가 발견되었습니다. 원인 분석 결과, 각 대화(`Conversation`)를 조회한 후, 해당 대화에 연결된 `User`, `Persona` 정보를 얻기 위해 루프를 돌며 추가적인 쿼리가 발생하는 <b>N+1 문제</b>임을 확인했습니다.

**해결 과정:**

SQLAlchemy의 **즉시 로딩(Eager Loading)** 전략을 사용하여 이 문제를 해결했습니다. `selectinload`와 `joinedload` 옵션을 활용하여, 첫 번째 쿼리를 실행할 때 연관된 모든 엔티티를 함께 가져오도록 최적화했습니다.

*   **AS-IS (기존 코드의 문제점)**
    ```python
    # conversation_list = db.query(Conversation).filter(...).all() # 1번의 쿼리 발생
    # for conv in conversation_list:
    #     print(conv.user.username)  # N번의 추가 쿼리 발생
    #     print(conv.persona.name)   # N번의 추가 쿼리 발생
    ```

*   **TO-BE (개선된 코드)**
    ```python
    # app/crud/crud_conversation.py

    # 공통 로딩 옵션을 미리 정의
    _CONVERSATION_EAGER_LOADING_OPTIONS = (
        selectinload(Conversation.persona),
        joinedload(Conversation.user),
        # ... 기타 필요한 관계 로드
    )

    def _get_base_conversation_query() -> Query:
        # 기본 쿼리에 Eager Loading 옵션을 항상 적용
        return select(Conversation).options(*_CONVERSATION_EAGER_LOADING_OPTIONS)

    async def get_conversations_by_user(...):
        # 이 함수는 이제 N+1 문제 없이 단 한 번의 쿼리로 모든 정보를 가져옴
        stmt = _get_base_conversation_query().where(...)
        result = await db.execute(stmt)
        return result.scalars().all()
    ```
이러한 최적화를 통해 API의 응답 시간을 크게 단축하고 데이터베이스 부하를 줄일 수 있었습니다.
</details>

### 3. 아키텍처 결정: 왜 계층형 구조(Layered Architecture)인가?

<details>
    
프로젝트 초기 아키텍처로 <b>계층형 구조</b>를 선택한 것은 <b>팀의 생산성을 극대화</b>하고, <b>초기 개발 단계의 불필요한 복잡성을 피하기 위한</b> 전략적인 결정이었습니다.

*   <b>낮은 학습 곡선과 높은 생산성</b>: 계층형 구조는 대부분의 개발자에게 매우 익숙합니다. 복잡한 헥사고날(Hexagonal)이나 클린 아키텍처(Clean Architecture)와 달리, 팀원 모두가 구조를 빠르게 이해하고 즉시 개발에 집중할 수 있었습니다. 이는 <b>팀의 기술적 성숙도와 프로젝트의 현재 단계를 고려했을 때 가장 합리적인 선택</b>이었습니다.
*   <b>명확한 책임 분리와 단순성</b>: `API`, `Service`, `CRUD`로 이어지는 명확하고 단일한 데이터 흐름은 코드의 위치를 예측하기 쉽게 만듭니다. 이는 초기 기능 구현 단계에서 발생할 수 있는 혼란을 줄이고, <b>"가장 단순한 것이 최고의 해결책(Keep It Simple, Stupid)"</b>이라는 원칙을 지키는 데 도움이 되었습니다.
*   <b>점진적 발전의 기반</b>: 현재의 응집도 높은 `Service` 계층(`conversation_service`, `auth_service` 등)은 향후 서비스가 고도화되고 도메인이 명확해졌을 때, 이를 기준으로 <b>MSA로 점진적으로 전환할 수 있는 견고한 기반</b>이 됩니다. 처음부터 과도한 설계를 적용하기보다, 비즈니스의 성장에 맞춰 아키텍처를 진화시키는 실용적인 접근법을 택했습니다.

결론적으로, 계층형 구조는 <b>"가장 이상적인 아키텍처"</b>라서가 아니라, <b>"현재 우리 팀과 프로젝트 단계에 가장 적합하고 효율적인 아키텍처"</b>였기 때문에 선택되었습니다.

</details>
