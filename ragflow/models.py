from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from email.utils import parsedate_to_datetime  # 新增：用于解析RFC 1123时间格式


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: bool = False


class CompletionTokensDetails(BaseModel):
    accepted_prediction_tokens: int
    reasoning_tokens: int
    rejected_prediction_tokens: int


class ChatCompletionUsage(BaseModel):
    completion_tokens: int
    completion_tokens_details: CompletionTokensDetails


class ChatCompletionResponse(BaseModel):
    id: str
    choices: List[Any]
    created: int
    model: str
    object: str
    usage: ChatCompletionUsage


class Dataset(BaseModel):
    id: str
    name: str
    avatar: Optional[str] = None
    description: Optional[str] = None
    embedding_model: str
    chunk_method: str
    parser_config: Dict[str, Any]
    permission: str = "me"
    # 新增：自定义时间解析器
    create_date: datetime = Field(
        validation_alias="create_date",
        json_schema_extra={"example": "Wed, 28 May 2025 14:30:33 GMT"},
    )
    update_date: datetime = Field(
        validation_alias="update_date",
        json_schema_extra={"example": "Wed, 28 May 2025 14:30:33 GMT"},
    )
    chunk_count: int
    document_count: int
    token_num: int
    status: str

    # 自定义验证器：解析RFC 1123时间格式
    @field_validator("create_date", "update_date", mode="before")
    def parse_rfc1123_date(cls, value):
        if isinstance(value, str):
            # 使用email.utils.parsedate_to_datetime解析RFC 1123格式
            dt = parsedate_to_datetime(value)
            if dt:
                return dt
        return value  # 保留其他类型（如已解析的datetime对象）


class Document(BaseModel):
    id: str
    name: str
    dataset_id: str
    location: str
    size: int
    type: str
    chunk_method: str
    parser_config: Dict[str, Any]
    run: str
    created_by: str


class Chunk(BaseModel):
    id: str
    dataset_id: str
    document_id: str
    content: str
    chunk_token_count: int
    delimiter: str
    create_time: int
    update_time: int
    # 其他分块相关字段（根据API实际返回补充）
