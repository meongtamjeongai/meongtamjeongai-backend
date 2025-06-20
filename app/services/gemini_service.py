# app/services/gemini_service.py

import base64
import json
import logging
import os
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from google import genai
from google.api_core import exceptions as google_api_exceptions
from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.message import Message as MessageModel
from app.models.message import SenderType
from app.models.phishing_case import PhishingCase
from app.models.phishing_category import PhishingCategory
from app.schemas.gemini import GeminiChatResponse
from app.schemas.phishing import PhishingImageAnalysisResponse

# 로거 설정
logger = logging.getLogger(__name__)


# AI가 생성할 피싱 사례의 형식을 정의하는 내부용 Pydantic 모델
class GeneratedPhishingCase(BaseModel):
    title: str = Field(..., description="AI가 생성한 피싱 시나리오의 제목")
    content: str = Field(
        ...,
        description="AI가 생성한 피싱 시나리오의 구체적인 내용 (문자 메시지, 이메일 등)",
    )


class GeminiService:
    """Google Gemini AI와의 통신을 담당하는 서비스."""

    def __init__(self):
        """
        GeminiService를 초기화하고, 환경 변수에서 API 키를 읽어
        Google Gen AI 클라이언트를 설정합니다.
        """
        self.client = None
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                # 최신 SDK 문서에 명시된 Client 생성 방식으로 초기화합니다.
                # 이 객체는 동기 및 비동기 메서드를 모두 포함하고 있습니다.
                self.client = genai.Client(api_key=api_key)
                logger.info(
                    "✅ GeminiService: Google Gen AI Client initialized successfully."
                )
            except Exception as e:
                logger.error(
                    f"❌ GeminiService: Failed to initialize Google Gen AI Client: {e}",
                    exc_info=True,
                )
        else:
            logger.warning(
                "⚠️ GeminiService: GEMINI_API_KEY environment variable not found."
            )

    def is_available(self) -> bool:
        """서비스가 사용 가능한지 (클라이언트가 초기화되었는지) 확인합니다."""
        return self.client is not None

    async def get_chat_response(
        self,
        system_prompt: str,
        history: List[MessageModel],
        user_message: str,
        image_base64: Optional[str] = None,
        phishing_case: Optional[PhishingCase] = None,
        starting_message: Optional[str] = None,
    ) -> Tuple[GeminiChatResponse, List[Dict[str, Any]]]:
        """
        주어진 대화 내용과 이미지를 바탕으로 Gemini AI의 응답을 받아옵니다.
        """
        if not self.is_available():
            logger.error(
                "❌ GeminiService: Cannot get chat response, service is not available (Client not initialized)."
            )
            raise ConnectionError(
                "AI 서비스를 사용할 수 없습니다. 관리자에게 문의해주세요."
            )

        try:
            # 1. 최종 시스템 프롬프트 구성 (피싱 시나리오 포함)
            final_system_prompt = system_prompt
            if phishing_case:
                phishing_info = f"""
---
[오늘의 피싱 학습 시나리오]
너는 지금부터 아래 정보를 바탕으로 사용자에게 피싱 공격을 시도하는 역할을 맡아야 해. 자연스러운 대화를 통해 아래 시나리오의 목적을 달성해줘.

- 유형: {phishing_case.category.description if phishing_case.category else "일반 사기"}
- 제목: {phishing_case.title}
- 핵심 내용: {phishing_case.content}
---
"""
                final_system_prompt += phishing_info

            # 2. 대화 기록(history)을 Gemini가 이해하는 형식으로 변환
            reconstructed_history = []
            for msg in history:
                role = "user" if msg.sender_type == SenderType.USER else "model"
                msg_parts = [types.Part.from_text(text=msg.content)]
                reconstructed_history.append(types.Content(role=role, parts=msg_parts))

            # 3. 최종적으로 API에 보낼 contents 리스트 구성
            contents_for_generation = []
            if starting_message and not history:
                contents_for_generation.append(
                    types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=starting_message)],
                    )
                )
            contents_for_generation.extend(reconstructed_history)

            # 4. 현재 사용자 입력(텍스트 + 이미지)을 Content 객체로 구성
            user_parts = [types.Part.from_text(text=user_message)]
            if image_base64:
                try:
                    image_data = base64.b64decode(image_base64)
                    img = Image.open(BytesIO(image_data))
                    mime_type = Image.MIME.get(img.format)
                    if not mime_type:
                        raise ValueError("Could not determine image MIME type.")
                    user_parts.append(
                        types.Part(
                            inline_data=types.Blob(mime_type=mime_type, data=image_data)
                        )
                    )
                except Exception as e:
                    logger.error(f"🔥 Base64 이미지 데이터 처리 중 오류 발생: {e}")
                    pass
            contents_for_generation.append(types.Content(role="user", parts=user_parts))

            # 5. 토큰 사용량 계산 (동기 메서드 사용)
            token_count_response = self.client.models.count_tokens(
                model=settings.GEMINI_MODEL_NAME, contents=contents_for_generation
            )
            total_tokens = token_count_response.total_tokens

            # 6. API 응답 형식(JSON) 설정
            response_schema = GeminiChatResponse.model_json_schema()
            if (
                "properties" in response_schema
                and "token_usage" in response_schema["properties"]
            ):
                del response_schema["properties"]["token_usage"]
                if (
                    "required" in response_schema
                    and "token_usage" in response_schema["required"]
                ):
                    response_schema["required"].remove("token_usage")

            # 7. API 호출을 위한 설정값 준비
            generation_config = types.GenerateContentConfig(
                system_instruction=final_system_prompt,
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.7,
            )

            # 8. [디버깅 로그] API 호출 직전 데이터 확인
            logger.info("--- 🚀 최종 Gemini 요청 Contents ---")
            for content in contents_for_generation:
                part_details = []
                for part in content.parts:
                    if hasattr(part, "text") and part.text:
                        part_details.append(f"Text(len={len(part.text)})")
                    elif hasattr(part, "inline_data"):
                        part_details.append(
                            f"Image(mime={part.inline_data.mime_type}, len={len(part.inline_data.data)})"
                        )
                if part_details:
                    logger.info(f"Role: {content.role}, Parts: {part_details}")
            logger.info("------------------------------------")

            # 9. Gemini API 비동기 호출 (Client의 aio 속성 사용)
            response = await self.client.aio.models.generate_content(
                model=settings.GEMINI_MODEL_NAME,
                contents=contents_for_generation,
                config=generation_config,
            )

            # 10. 결과 파싱 및 반환
            json_response = json.loads(response.text)
            json_response["token_usage"] = total_tokens

            logger.info(f"✅ Gemini API call successful. Tokens used: {total_tokens}")

            # 디버깅용으로, 토큰 계산에 사용된 원본 텍스트를 반환
            debug_contents = [
                {
                    "role": content.role,
                    "parts": [
                        part.text for part in content.parts if hasattr(part, "text")
                    ],
                }
                for content in contents_for_generation
            ]

            return GeminiChatResponse(**json_response), debug_contents

        except (
            google_api_exceptions.GoogleAPICallError,
            google_api_exceptions.RetryError,
        ) as e:
            logger.error(f"🔥 Gemini API 오류 발생: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Google API 오류: {e}",
            )
        except json.JSONDecodeError:
            # 오류 발생 시 응답 내용을 로그에 남깁니다.
            response_text = "N/A"
            if "response" in locals():
                response_text = response.text
            logger.error(
                f"🔥 JSON 파싱 오류: 모델이 유효한 JSON을 반환하지 않았습니다. 응답: {response_text}"
            )
            raise HTTPException(
                status_code=500, detail="모델로부터 유효한 JSON 응답을 받지 못했습니다."
            )
        except Exception as e:
            logger.error(f"🔥 예상치 못한 오류 발생: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"서버 내부 오류가 발생했습니다: {str(e)}"
            )

    # --- 이미지 피싱 분석을 위한 새 메서드 ---
    async def analyze_image_for_phishing(
        self, image_base64: str
    ) -> PhishingImageAnalysisResponse:
        """
        주어진 이미지를 분석하여 피싱 점수와 이유를 반환합니다.
        """
        if not self.is_available():
            raise ConnectionError("AI 서비스를 사용할 수 없습니다.")

        # 1. 이 기능을 위한 전용 시스템 프롬프트 정의
        system_prompt = """
        당신은 최첨단 사이버 보안 분석가입니다. 당신의 임무는 주어진 이미지를 분석하여 스미싱이나 피싱 시도의 징후가 있는지 판단하는 것입니다.
        분석 후, 반드시 지정된 JSON 형식에 맞춰 응답해야 합니다.

        [분석 기준]
        - 텍스트 내용: 긴급성, 위협, 비정상적인 할인 등 심리적 압박을 주는 문구가 있는가?
        - 발신자 정보: 공공기관, 금융기관, 유명 기업을 사칭하고 있는가?
        - 링크/URL: 의심스러운 단축 URL, 오타가 있는 도메인, 또는 공식적이지 않은 링크가 포함되어 있는가?
        - 디자인 및 문법: 조악한 디자인, 어색한 문법, 오탈자가 있는가?
        - 요청 사항: 개인정보(주민번호, 비밀번호, 카드번호)나 금전적 이체를 직접적으로 요구하는가?

        [출력 형식]
        - phishing_score: 이미지가 피싱일 확률을 0에서 100 사이의 정수 점수로 표현합니다. 100에 가까울수록 피싱일 확률이 높습니다.
        - reason: 왜 해당 점수로 판단했는지, 위 분석 기준에 근거하여 2~3문장으로 명확하고 간결하게 설명합니다.
        """

        # 2. 사용자 입력 구성 (텍스트 + 이미지)
        user_prompt_text = "이 이미지를 분석하고 피싱 위험도를 평가해줘."
        try:
            image_data = base64.b64decode(image_base64)
            img = Image.open(BytesIO(image_data))
            mime_type = Image.MIME.get(img.format)
            if not mime_type:
                raise ValueError("Could not determine image MIME type.")

            image_part = types.Part(
                inline_data=types.Blob(mime_type=mime_type, data=image_data)
            )
        except Exception as e:
            logger.error(f"🔥 이미지 분석을 위한 데이터 처리 중 오류: {e}")
            raise HTTPException(status_code=400, detail="잘못된 이미지 데이터입니다.")

        # 3. API 호출 준비
        generation_config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            # --- model_json_schema() 호출 대신, 클래스 자체를 전달 ---
            response_schema=PhishingImageAnalysisResponse,
            temperature=0.2,
        )

        contents = [user_prompt_text, image_part]

        # 4. API 호출
        try:
            response = await self.client.aio.models.generate_content(
                model=settings.GEMINI_MODEL_NAME,
                contents=contents,
                config=generation_config,
            )

            # 5. 결과 파싱 및 반환
            json_response = json.loads(response.text)
            return PhishingImageAnalysisResponse(**json_response)
        except Exception as e:
            logger.error(f"🔥 이미지 분석 API 호출 중 오류: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail="이미지 분석 중 오류가 발생했습니다."
            )

    # 피싱 사례를 즉석에서 생성하는 새로운 메서드
    async def generate_phishing_case_on_the_fly(
        self, category: PhishingCategory
    ) -> GeneratedPhishingCase:
        """
        주어진 피싱 카테고리 정보를 바탕으로 새로운 피싱 사례를 AI가 생성합니다.
        """
        if not self.is_available():
            raise ConnectionError("AI 서비스를 사용할 수 없습니다.")

        # 1. 이 기능을 위한 전용 시스템 프롬프트 정의
        system_prompt = f"""
        당신은 창의적인 시나리오 작가입니다. 당신의 임무는 주어진 피싱 유형에 대한 현실감 넘치는 예시 시나리오를 만드는 것입니다.
        사용자가 피싱 공격을 학습하고 대비할 수 있도록, 실제 상황처럼 보이는 제목과 내용을 생성해야 합니다.
        반드시 지정된 JSON 형식(`title`, `content`)에 맞춰 응답해야 합니다.

        [생성할 피싱 유형 정보]
        - 코드: {category.code}
        - 설명: {category.description}
        """

        # 2. 사용자 입력 구성
        user_prompt_text = (
            f"'{category.code}' 유형에 맞는 피싱 시나리오를 하나 만들어줘."
        )

        # 3. API 호출 준비
        generation_config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=GeneratedPhishingCase,  # 내부용 스키마 사용
            temperature=0.8,  # 창의성을 위해 온도를 약간 높임
        )

        # 4. API 호출
        try:
            response = await self.client.aio.models.generate_content(
                model=settings.GEMINI_MODEL_NAME,
                contents=[user_prompt_text],
                config=generation_config,
            )

            # 5. 결과 파싱 및 반환
            json_response = json.loads(response.text)
            logger.info(
                f"✅ AI-Generated Phishing Case for '{category.code}': {json_response}"
            )
            return GeneratedPhishingCase(**json_response)
        except Exception as e:
            logger.error(f"🔥 AI 피싱 사례 생성 중 오류 발생: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail="AI 시나리오 생성 중 오류가 발생했습니다."
            )
