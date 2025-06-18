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

from app.core.config import settings
from app.models.message import Message as MessageModel
from app.models.message import SenderType
from app.models.phishing_case import PhishingCase
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
                # 💡 [수정] genai.configure()를 사용하여 API 키를 설정하는 것이 권장 방식입니다.
                genai.configure(api_key=api_key)
                # 💡 [수정] GenerativeModel을 직접 사용하는 것이 더 직관적일 수 있습니다.
                self.model = genai.GenerativeModel(
                    model_name=settings.GEMINI_MODEL_NAME
                )
                logger.info(
                    "✅ GeminiService: Google Gen AI Client initialized successfully."
                )
            except Exception as e:
                logger.error(
                    f"❌ GeminiService: Failed to initialize Google Gen AI Client: {e}",
                    exc_info=True,
                )
                self.model = None
        else:
            logger.warning(
                "⚠️ GeminiService: GEMINI_API_KEY environment variable not found."
            )
            self.model = None

    def is_available(self) -> bool:
        """서비스가 사용 가능한지 (클라이언트가 초기화되었는지) 확인합니다."""
        return self.model is not None

    async def get_chat_response(
        self,
        system_prompt: str,
        history: List[MessageModel],
        user_message: str,
        image_base64: Optional[str] = None,
        phishing_case: Optional[PhishingCase] = None,
        starting_message: Optional[str] = None,
    ) -> Tuple[GeminiChatResponse, List[Dict[str, Any]]]:
        if not self.is_available():
            logger.error(
                "❌ GeminiService: Cannot get chat response, service is not available."
            )
            raise ConnectionError(
                "AI 서비스를 사용할 수 없습니다. 관리자에게 문의해주세요."
            )

        try:
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

            reconstructed_history = []
            for msg in history:
                role = "user" if msg.sender_type == SenderType.USER else "model"
                msg_parts = [types.Part.from_text(text=msg.content)]
                reconstructed_history.append(types.Content(role=role, parts=msg_parts))

            contents_for_generation = []
            if starting_message and not history:
                contents_for_generation.append(
                    types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=starting_message)],
                    )
                )

            contents_for_generation.extend(reconstructed_history)

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
                    logger.info(
                        f"✅ 이미지 데이터를 성공적으로 파싱하여 Gemini 요청에 포함했습니다. (MIME: {mime_type})"
                    )
                except Exception as e:
                    logger.error(f"🔥 Base64 이미지 데이터 처리 중 오류 발생: {e}")
                    pass

            contents_for_generation.append(types.Content(role="user", parts=user_parts))

            contents_for_counting = [
                types.Content(
                    role="user", parts=[types.Part.from_text(text=final_system_prompt)]
                ),
                types.Content(
                    role="model",
                    parts=[
                        types.Part.from_text(
                            text="네, 알겠습니다. 당신의 지시에 따르겠습니다."
                        )
                    ],
                ),
            ] + contents_for_generation

            token_count_response = await genai.caching.get_async_client().count_tokens(
                model=self.model.model_name,
                contents=contents_for_counting,
            )
            total_tokens = token_count_response.total_tokens

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

            generation_config = types.GenerationConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.7,
            )

            # --- ✅ [디버깅 로그 추가] ---
            logger.info("--- 🚀 최종 Gemini 요청 Contents ---")
            for content in contents_for_generation:
                part_details = []
                for part in content.parts:
                    if hasattr(part, "text"):
                        part_details.append(f"Text(len={len(part.text)})")
                    elif hasattr(part, "inline_data"):
                        part_details.append(
                            f"Image(mime={part.inline_data.mime_type}, len={len(part.inline_data.data)})"
                        )
                logger.info(f"Role: {content.role}, Parts: {part_details}")
            logger.info("------------------------------------")

            response = await self.model.generate_content_async(
                contents=contents_for_generation,
                generation_config=generation_config,
                system_instruction=final_system_prompt,
            )

            json_response = json.loads(response.text)
            json_response["token_usage"] = total_tokens

            logger.info(f"✅ Gemini API call successful. Tokens used: {total_tokens}")

            debug_contents = [
                {
                    "role": content.role,
                    "parts": [part.text for part in content.parts],
                }
                for content in contents_for_counting
            ]

            logger.info("=" * 50)
            logger.info(
                f"🚀 최종 시스템 프롬프트 (To Gemini API for Conv ID: {history[0].conversation_id if history else 'N/A'})"
            )
            logger.info(final_system_prompt)
            logger.info("=" * 50)

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
