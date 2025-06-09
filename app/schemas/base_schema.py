# fastapi_backend/app/schemas/base_schema.py
# 모든 Pydantic 스키마의 기반이 되는 BaseModel 정의

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict


class BaseModel(PydanticBaseModel):
    # Pydantic V2 스타일 설정
    # from_attributes = True는 이전 orm_mode = True와 동일한 기능
    model_config = ConfigDict(from_attributes=True)

    # Pydantic V1 스타일 설정 (만약 Pydantic V1을 사용한다면)
    # class Config:
    #     orm_mode = True
