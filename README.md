# RagFlow Python SDK

这是 RagFlow API 的 Python SDK，提供了简单易用的接口来访问 RagFlow 的所有功能。

## 安装

### 1. 安装依赖

项目依赖通过 `requirements.txt` 管理，执行以下命令安装：

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量（.env 文件）

在项目根目录创建 `.env` 文件，用于配置 RagFlow API 密钥：

```env
# .env 文件内容示例
RAGFLOW_API_KEY=your_actual_api_key_here
RAGFLOW_API_URL=your_actual_api_url_here
```

> 注意：API 密钥需从 RagFlow 平台获取，请勿将 `.env` 文件提交到代码仓库，避免密钥泄露。

## 核心功能 - 文档上传与解析

### 功能说明

`upload_documents_with_parse` 函数用于批量上传指定目录下的支持类型文件到 RagFlow 数据集，并自动触发文档解析（生成/更新分块）。支持的文件类型包括：Word（.doc/.docx）、PDF（.pdf）、Excel（.xls/.xlsx）、Markdown（.md）、纯文本（.txt）。

### 参数说明

- `dataset_name`: 目标数据集名称（需提前在 RagFlow 平台创建）
- `doc_dir`: 需要上传的文档目录绝对路径或相对路径（支持 macOS/Unix 风格路径，如 `/Users/user/documents` 或 `./local_docs`）

### 使用示例

#### 命令行调用（推荐）

```bash
# 上传当前目录下的 "local_docs" 目录到名为 "industrial_docs" 的数据集
python upload_documents_with_parse.py "industrial_docs" "./local_docs"
```

#### 脚本内调用

```python
from upload_documents_with_parse import upload_and_parse_documents

# 上传绝对路径目录 "/data/project_docs" 到 "project_dataset" 数据集
upload_and_parse_documents("project_dataset", "/data/project_docs")
```

### 执行流程说明

1. **客户端初始化**：通过 `.env` 文件中的 `RAGFLOW_API_KEY` 初始化 RagFlow 客户端。
2. **数据集验证**：检查指定名称的数据集是否存在（不存在时抛出 `ResourceNotFoundError`）。
3. **目录扫描与过滤**：扫描指定目录，自动跳过不支持的文件类型（如图片、视频等）。
4. **逐文件上传**：逐个打开支持类型的文件并上传到目标数据集，记录上传成功的文档 ID。
5. **触发解析**：使用所有上传成功的文档 ID 调用解析接口，生成文档分块。
