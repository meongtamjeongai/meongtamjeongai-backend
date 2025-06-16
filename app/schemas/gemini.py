# app/schemas/gemini.py

from typing import List, Optional
from pydantic import Field
from app.schemas.base_schema import BaseModel

class GeminiProgressCheck(BaseModel):
    """대화 진행 상태를 점검하기 위한 모델"""
    status_summary: str = Field(..., description="현재 대화 상태에 대한 요약")
    is_ready_to_move_on: bool = Field(..., description="현재 주제에 대한 이야기가 충분하여 다음 주제로 넘어갈 준비가 되었는지 여부")

class GeminiChatResponse(BaseModel):
    """Gemini 모델로부터 받을 구조화된 JSON 응답 스키마"""
    response: str = Field(..., description="사용자 질문에 대한 AI의 핵심 답변")
    suggested_user_questions: List[str] = Field(..., description="사용자가 다음에 할 법한 질문 제안 목록(최대 3개)")
    progress_check: GeminiProgressCheck = Field(..., description="대화 진행 상태 점검 결과")
    token_usage: int = Field(..., description="이번 응답 생성에 사용된 총 토큰 수")
    session_end_message: Optional[str] = Field(None, description="대화가 끝날 때 표시할 최종 메시지")
    next_topic_suggestions: List[str] = Field(default_factory=list, description="현재 주제가 끝났을 때 제안할 다음 주제 목록")