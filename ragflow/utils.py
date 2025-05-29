import os
from typing import Optional, Dict, Any
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv()


def get_base_url() -> str:
    """获取API基础URL"""
    return os.getenv("RAGFLOW_API_URL", "http://120.224.107.249:22280")


def join_url(base: str, path: str) -> str:
    """连接URL路径"""
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


from .exceptions import APIError  # 新增：导入APIError异常类


def handle_response(response: Dict[str, Any]) -> Dict[str, Any]:
    # print(response)
    # 兼容两种响应结构：包含code字段（如数据集API）和不包含code字段（如聊天API）
    if "code" in response:
        if response.get("code") != 0:
            raise APIError(
                f"API请求失败，错误信息：{response.get('message', '未知错误')}"
            )
        data = response.get("data")
        # 若data存在则返回，否则返回原始响应（兼容data可能为None的情况）
        return data if data is not None else response
    # 无code字段时直接返回原始响应（如聊天接口）
    return response
