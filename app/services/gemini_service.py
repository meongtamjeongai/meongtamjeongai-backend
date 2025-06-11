# app/services/gemini_service.py
import os
import logging
from typing import List, Tuple

from google import genai
from google.genai import types

from app.models.message import Message as MessageModel, SenderType

# 로거 설정
logger = logging.getLogger(__name__)

class GeminiService:
    """
    Google Gemini AI와의 통신을 담당하는 서비스.
    """
    def __init__(self):
        self.client = None
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                # API 키를 사용하여 클라이언트 설정
                self.client = genai.Client(api_key=api_key)
                logger.info("✅ GeminiService: Google Gen AI Client initialized successfully.")
            except Exception as e:
                logger.error(f"❌ GeminiService: Failed to initialize Google Gen AI Client: {e}")
        else:
            logger.warning("⚠️ GeminiService: GEMINI_API_KEY environment variable not found.")

    def is_available(self) -> bool:
        """
        서비스가 사용 가능한지 (클라이언트가 초기화되었는지) 확인합니다.
        """
        return self.client is not None

    async def get_chat_response(
        self,
        system_prompt: str,
        history: List[MessageModel],
        user_message: str
    ) -> Tuple[str, int]:
        """
        채팅 기록과 새 메시지를 기반으로 Gemini 모델의 응답을 받아옵니다.
        
        Returns:
            Tuple[str, int]: (AI 응답 텍스트, 사용된 총 토큰 수)
        """
        if not self.is_available():
            logger.error("❌ GeminiService: Cannot get chat response, service is not available.")
            # 서비스 사용 불가 시 기본 응답 반환
            return "죄송합니다, 현재 AI 서비스를 사용할 수 없습니다. 관리자에게 문의해주세요.", 0

        try:
            # 1. Gen AI 형식으로 대화 기록 재구성
            # system_prompt는 첫 번째 'model' 역할의 content로 포함될 수 있음
            # 또는 모델의 system_instruction 파라미터를 지원하는 경우 사용
            reconstructed_history = []
            for msg in history:
                role = 'user' if msg.sender_type == SenderType.USER else 'model'
                reconstructed_history.append(
                    types.Content(role=role, parts=[types.Part.from_text(msg.content)])
                )
            
            # 2. 모델 및 설정 정의
            # gemini-1.5-flash는 빠르고 비용 효율적
            model = self.client.models.get('gemini-1.5-flash')
            
            # 3. 채팅 세션 시작 (기록 포함)
            # system_prompt는 첫 번째 user 메시지 앞에 model의 생각으로 넣어줄 수 있음
            # 또는 model.start_chat의 system_instruction 파라미터 활용 (SDK 버전 확인 필요)
            chat = model.start_chat(history=reconstructed_history)

            # 4. 새로운 프롬프트로 응답 요청
            # send_message_async를 사용하면 비동기적으로 호출 가능
            response = await chat.send_message_async(
                [system_prompt, user_message] # 시스템 프롬프트와 사용자 메시지를 함께 전달
            )

            # 5. 토큰 사용량 계산 (응답 객체에서 확인 필요, API 문서 참조)
            # 예시: response.usage_metadata.total_token_count
            # google-genai SDK는 토큰 수를 직접 반환하지 않을 수 있으므로,
            # model.count_tokens를 사용하여 직접 계산해야 할 수 있습니다.
            token_count_response = await model.count_tokens_async([system_prompt, user_message] + reconstructed_history)
            total_tokens = token_count_response.total_tokens
            
            logger.info(f"✅ Gemini API call successful. Tokens used: {total_tokens}")
            
            return response.text, total_tokens

        except Exception as e:
            logger.error(f"❌ GeminiService: Error during chat API call: {e}")
            return f"죄송합니다, AI 응답 생성 중 오류가 발생했습니다: {e}", 0