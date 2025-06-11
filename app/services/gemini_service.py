# app/services/gemini_service.py

import json
import logging
import os
from typing import List

from fastapi import HTTPException, status
from google import genai
from google.api_core import exceptions as google_api_exceptions
from google.genai import types

from app.models.message import Message as MessageModel
from app.models.message import SenderType
from app.schemas.gemini import GeminiChatResponse

# 로거 설정
logger = logging.getLogger(__name__)


class GeminiService:
    """Google Gemini AI와의 통신을 담당하는 서비스."""

    def __init__(self):
        self.client = None
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
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
        self, system_prompt: str, history: List[MessageModel], user_message: str
    ) -> GeminiChatResponse:
        if not self.is_available():
            logger.error(
                "❌ GeminiService: Cannot get chat response, service is not available."
            )
            raise ConnectionError(
                "AI 서비스를 사용할 수 없습니다. 관리자에게 문의해주세요."
            )

        try:
            # 1. 대화 기록을 genai.types.Content 객체 리스트로 재구성
            reconstructed_history = []
            for msg in history:
                role = "user" if msg.sender_type == SenderType.USER else "model"
                reconstructed_history.append(
                    types.Content(
                        role=role, parts=[types.Part.from_text(text=msg.content)]
                    )
                )

            # 2. 토큰 계산을 위한 contents 리스트 생성
            contents_for_counting = (
                [
                    types.Content(
                        role="user", parts=[types.Part.from_text(text=system_prompt)]
                    ),
                    types.Content(
                        role="model",
                        parts=[
                            types.Part.from_text(
                                text="네, 알겠습니다. 당신의 지시에 따르겠습니다."
                            )
                        ],
                    ),
                ]
                + reconstructed_history
                + [
                    types.Content(
                        role="user", parts=[types.Part.from_text(text=user_message)]
                    )
                ]
            )

            token_count_response = await self.client.aio.models.count_tokens(
                model="models/gemini-1.5-flash-latest", contents=contents_for_counting
            )
            total_tokens = token_count_response.total_tokens

            # 3. JSON 응답 스키마 준비
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

            # 4. ⭐️ 수정: generate_content에 전달할 config 객체를 생성합니다.
            generation_config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.7,
            )

            # 5. generate_content에 전달할 contents는 대화 기록과 새 메시지만 포함
            contents_for_generation = reconstructed_history + [
                types.Content(
                    role="user", parts=[types.Part.from_text(text=user_message)]
                )
            ]

            # 6. ⭐️ 수정: 'config' 파라미터에 위에서 생성한 객체를 전달합니다.
            response = await self.client.aio.models.generate_content(
                model="models/gemini-1.5-flash-latest",
                contents=contents_for_generation,
                config=generation_config,
            )

            # 7. 결과 파싱 및 반환
            json_response = json.loads(response.text)
            json_response["token_usage"] = total_tokens

            logger.info(f"✅ Gemini API call successful. Tokens used: {total_tokens}")
            return GeminiChatResponse(**json_response)

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
            logger.error(
                f"🔥 JSON 파싱 오류: 모델이 유효한 JSON을 반환하지 않았습니다. 응답: {response.text}"
            )
            raise HTTPException(
                status_code=500, detail="모델로부터 유효한 JSON 응답을 받지 못했습니다."
            )
        except Exception as e:
            logger.error(f"🔥 예상치 못한 오류 발생: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"서버 내부 오류가 발생했습니다: {str(e)}"
            )
