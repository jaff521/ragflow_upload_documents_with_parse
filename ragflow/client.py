import os
import json
from typing import Optional, Dict, Any, List, Union, BinaryIO
import requests
from . import models  # 替换原有的 `import models`
from .utils import get_base_url, join_url, handle_response  # 改为相对导入
from .exceptions import (
    AuthenticationError,
    APIError,
    ValidationError,
    ResourceNotFoundError,
)
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


class RagFlowClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("RAGFLOW_API_KEY")
        if not self.api_key:
            raise AuthenticationError("API key is required")

        self.base_url = base_url or get_base_url()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, BinaryIO]] = None,
        stream: bool = False,  # 新增流式标志
    ) -> Union[Dict[str, Any], requests.Response]:  # 支持返回原始响应对象
        url = join_url(self.base_url, path)

        if files:
            headers = self.session.headers.copy()
            headers.pop("Content-Type", None)
            response = self.session.request(
                method, url, params=params, files=files, headers=headers, stream=stream
            )
        else:
            response = self.session.request(
                method, url, params=params, json=json_data, stream=stream
            )  # 传递stream参数

        if stream:
            return response  # 流式响应直接返回原始response对象

        try:
            data = response.json()
        except json.JSONDecodeError:
            raise APIError(f"Invalid JSON response: {response.text}")

        if response.status_code >= 400:
            if response.status_code == 401:
                raise AuthenticationError(data.get("message", "Authentication failed"))
            elif response.status_code == 404:
                raise ResourceNotFoundError(data.get("message", "Resource not found"))
            else:
                raise APIError(
                    f"API request failed: {data.get('message', 'Unknown error')}"
                )

        return data

    # OpenAI兼容API
    def create_chat_completion(
        self,
        chat_id: str,
        messages: List[Dict[str, str]],
        model: str = "model",
        stream: bool = False,
    ) -> Union[models.ChatCompletionResponse, Any]:
        path = f"/api/v1/chats_openai/{chat_id}/chat/completions"
        data = {"model": model, "messages": messages, "stream": stream}

        if stream:
            # 流式模式：获取原始响应并逐行解析分块
            response = self._request("POST", path, json_data=data, stream=True)
            chunks = []
            for line in response.iter_lines():
                if line:  # 跳过空行
                    # 去除'data: '前缀并解析JSON
                    json_line = line.decode("utf-8").lstrip("data: ").strip()
                    if json_line:
                        try:
                            chunks.append(json.loads(json_line))
                        except json.JSONDecodeError:
                            continue
            return chunks
        else:
            # 非流式模式：原有逻辑
            response = self._request("POST", path, json_data=data)
            try:
                parsed_data = handle_response(response)
            except APIError as e:
                print(f"API请求失败: {e}")
                return None  # 或根据需求抛出异常
            return models.ChatCompletionResponse(**parsed_data)

    # 数据集管理API
    def create_dataset(
        self,
        name: str,
        embedding_model: Optional[str] = None,
        description: Optional[str] = None,
        chunk_method: str = "naive",
        parser_config: Optional[Dict[str, Any]] = None,
        permission: str = "me",
    ) -> models.Dataset:
        path = "/api/v1/datasets"
        data = {
            "name": name,
            "embedding_model": embedding_model,
            "description": description,
            "chunk_method": chunk_method,
            "parser_config": parser_config or {},
            "permission": permission,
        }

        response = self._request("POST", path, json_data=data)
        return models.Dataset(**handle_response(response))

    def list_datasets(
        self,
        page: int = 1,
        page_size: int = 30,
        orderby: str = "create_time",
        desc: bool = True,
        name: Optional[str] = None,
        dataset_id: Optional[str] = None,
    ) -> List[models.Dataset]:
        path = "/api/v1/datasets"
        params = {
            "page": page,
            "page_size": page_size,
            "orderby": orderby,
            "desc": desc,
        }
        if name:
            params["name"] = name
        if dataset_id:
            params["id"] = dataset_id

        response = self._request("GET", path, params=params)
        return [models.Dataset(**item) for item in handle_response(response)]

    def delete_datasets(self, dataset_ids: List[str]) -> None:
        path = "/api/v1/datasets"
        data = {"ids": dataset_ids}
        self._request("DELETE", path, json_data=data)

    def update_dataset(
        self,
        dataset_id: str,
        name: Optional[str] = None,
        embedding_model: Optional[str] = None,
        chunk_method: Optional[str] = None,
    ) -> None:
        path = f"/api/v1/datasets/{dataset_id}"
        data = {}
        if name:
            data["name"] = name
        if embedding_model:
            data["embedding_model"] = embedding_model
        if chunk_method:
            data["chunk_method"] = chunk_method

        self._request("PUT", path, json_data=data)

    def upload_documents(
        self, dataset_id: str, files: List[BinaryIO]
    ) -> List[models.Document]:
        # 构造完整URL
        path = f"/api/v1/datasets/{dataset_id}/documents"
        url = join_url(self.base_url, path)

        # 构造请求头（保留Authorization，Content-Type由requests自动处理为multipart/form-data）
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        # 构造文件参数（格式参考示例中的files=[('file', (...))]）
        files_dict = [
            (
                "file",
                (
                    os.path.basename(file.name),  # 文件名
                    file,  # 文件对象
                ),
            )
            for file in files
        ]

        # 打印上传前的关键信息（日志）
        print(f"[UPLOAD DEBUG] 上传文档到URL: {url}")
        print(
            f"[UPLOAD DEBUG] 文件参数: {[f[1][0] for f in files_dict]}"
        )  # 打印文件名列表

        # 直接使用requests发送POST请求（不调用self._request）
        response = requests.request(
            method="POST", url=url, headers=headers, files=files_dict
        )

        # 打印响应关键信息（日志）
        print(f"[UPLOAD DEBUG] 响应状态码: {response.status_code}")
        print(f"[UPLOAD DEBUG] 响应内容: {response.text}")  # 注意：敏感信息需过滤

        # 处理响应
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise APIError(f"Invalid JSON response: {response.text}")

        if response.status_code >= 400:
            message = data.get("message", "Unknown error")
            raise APIError(f"API request failed: {message}")

        # 修正：返回服务端响应中的 data 字段（文档列表）
        return data.get("data", [])  # 从完整响应中提取文档列表

    def update_document(
        self,
        dataset_id: str,
        document_id: str,
        name: Optional[str] = None,
        meta_fields: Optional[Dict[str, Any]] = None,
        chunk_method: Optional[str] = None,
        parser_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        path = f"/api/v1/datasets/{dataset_id}/documents/{document_id}"
        data = {}
        if name:
            data["name"] = name
        if meta_fields:
            data["meta_fields"] = meta_fields
        if chunk_method:
            data["chunk_method"] = chunk_method
        if parser_config:
            data["parser_config"] = parser_config

        self._request("PUT", path, json_data=data)

    def download_document(
        self, dataset_id: str, document_id: str, output_file: BinaryIO
    ) -> None:
        path = f"/api/v1/datasets/{dataset_id}/documents/{document_id}"
        response = self.session.get(join_url(self.base_url, path), stream=True)

        if response.status_code >= 400:
            try:
                data = response.json()
                message = data.get("message", "Unknown error")
            except json.JSONDecodeError:
                message = response.text
            raise APIError(f"Failed to download document: {message}")

        for chunk in response.iter_content(chunk_size=8192):
            output_file.write(chunk)

    def list_chunks(
        self,
        dataset_id: str,
        document_id: str,
        page: int = 1,
        page_size: int = 30,
        orderby: str = "create_time",
        desc: bool = True,
    ) -> List[models.Chunk]:
        """
        列出数据集中的所有分块（Chunk）
        :param dataset_id: 数据集ID
        :param document_id: 文档ID
        :param page: 页码，默认1
        :param page_size: 每页数量，默认30
        :param orderby: 排序字段（create_time/update_time），默认create_time
        :param desc: 是否降序排列，默认True
        :return: 分块列表
        """
        path = f"/api/v1/datasets/{dataset_id}/documents/{document_id}/chunks"
        params = {
            "page": page,
            "page_size": page_size,
            "orderby": orderby,
            "desc": desc,
        }
        response = self._request("GET", path, params=params)
        return response

    # 新增：检索分块的方法
    def retrieve_chunks(
        self,
        question: str,
        dataset_ids: Optional[List[str]] = None,
        document_ids: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 30,
        similarity_threshold: float = 0.2,
        vector_similarity_weight: float = 0.3,
        top_k: int = 1024,
        rerank_id: Optional[str] = None,
        keyword: bool = False,
        highlight: bool = False,
    ) -> Dict[str, Any]:
        """
        从指定数据集中检索分块
        :param question: 用户查询或关键词（必填）
        :param dataset_ids: 要搜索的数据集ID列表
        :param document_ids: 要搜索的文档ID列表（需同嵌入模型）
        :param page: 页码，默认1
        :param page_size: 每页最大分块数，默认30
        :param similarity_threshold: 最小相似度分数，默认0.2
        :param vector_similarity_weight: 向量余弦相似度权重，默认0.3
        :param top_k: 参与向量计算的分块数，默认1024
        :param rerank_id: 重排序模型ID
        :param keyword: 是否启用关键词匹配，默认False
        :param highlight: 是否高亮匹配词，默认False
        :return: 包含分块列表、文档聚合信息和总数的字典
        """
        path = "/api/v1/retrieval"
        data = {
            "question": question,
            "dataset_ids": dataset_ids,
            "document_ids": document_ids,
            "page": page,
            "page_size": page_size,
            "similarity_threshold": similarity_threshold,
            "vector_similarity_weight": vector_similarity_weight,
            "top_k": top_k,
            "rerank_id": rerank_id,
            "keyword": keyword,
            "highlight": highlight,
        }
        # 移除值为None的键（API可能不接受null值）
        data = {k: v for k, v in data.items() if v is not None}
        response = self._request("POST", path, json_data=data)
        return handle_response(response)

    def get_chunk(self, dataset_id: str, chunk_id: str) -> models.Chunk:
        """
        获取特定分块的详细信息
        :param dataset_id: 数据集ID
        :param chunk_id: 分块ID
        :return: 分块详情
        """
        path = f"/api/v1/datasets/{dataset_id}/chunks/{chunk_id}"
        response = self._request("GET", path)
        return models.Chunk(**handle_response(response))

    def update_chunk(
        self,
        dataset_id: str,
        chunk_id: str,
        chunk_token_count: Optional[int] = None,
        delimiter: Optional[str] = None,
    ) -> None:
        """
        更新分块配置（示例：以知识图谱分块的常见配置为例）
        :param dataset_id: 数据集ID
        :param chunk_id: 分块ID
        :param chunk_token_count: 分块token数
        :param delimiter: 分隔符
        """
        path = f"/api/v1/datasets/{dataset_id}/chunks/{chunk_id}"
        data = {}
        if chunk_token_count is not None:
            data["chunk_token_count"] = chunk_token_count
        if delimiter is not None:
            data["delimiter"] = delimiter

        self._request("PUT", path, json_data=data)

    def delete_chunk(self, dataset_id: str, chunk_id: str) -> None:
        """
        删除特定分块
        :param dataset_id: 数据集ID
        :param chunk_id: 分块ID
        """
        path = f"/api/v1/datasets/{dataset_id}/chunks/{chunk_id}"
        self._request("DELETE", path)

    def parse_documents(
        self,
        dataset_id: str,
        document_ids: List[str],
    ) -> Dict[str, Any]:
        """
        触发指定数据集中的文档解析（生成/更新分块）
        :param dataset_id: 数据集ID（路径参数）
        :param document_ids: 需要解析的文档ID列表（请求体参数）
        :return: 服务端响应结果（包含操作状态等信息）
        """
        path = f"/api/v1/datasets/{dataset_id}/chunks"
        data = {"document_ids": document_ids}
        response = self._request("POST", path, json_data=data)
        return handle_response(response)
