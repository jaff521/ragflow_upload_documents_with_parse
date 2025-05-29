import os
import argparse
from ragflow.client import RagFlowClient
from ragflow.exceptions import APIError, ResourceNotFoundError

# 支持的文件类型（扩展名映射）
SUPPORTED_FILE_TYPES = {
    "word": [".doc", ".docx"],
    "pdf": [".pdf"],
    "excel": [".xls", ".xlsx"],
    "markdown": [".md"],
    "txt": [".txt"],
}


def upload_and_parse_documents(dataset_name: str, doc_dir: str) -> None:
    """
    批量上传指定目录下的支持类型文件到数据集，并触发文档解析
    :param dataset_name: 目标数据集名称（不存在时自动创建）
    :param doc_dir: 需要上传的文档目录路径
    """
    try:
        # 初始化客户端
        client = RagFlowClient()
        print("[INFO] 客户端初始化成功")

        # 步骤1：查找或创建数据集（支持自动创建）
        print(f"[INFO] 查找/创建数据集: {dataset_name}")
        datasets = client.list_datasets(name=dataset_name)
        if not datasets:
            # 若未找到数据集，打印提示信息并抛出异常
            print(f"[INFO] 未找到数据集: {dataset_name}")
            raise ResourceNotFoundError(f"数据集 {dataset_name} 不存在")
        else:
            dataset = datasets[0]
            print(f"[INFO] 找到现有数据集，ID: {dataset.id}")
            dataset_id = dataset.id

        # 步骤2：扫描指定目录并过滤支持的文件
        print(f"[INFO] 扫描目录: {doc_dir}")
        if not os.path.exists(doc_dir):
            raise FileNotFoundError(f"文档目录不存在: {doc_dir}")
        if not os.path.isdir(doc_dir):
            raise NotADirectoryError(f"路径不是目录: {doc_dir}")

        file_paths = []
        for filename in os.listdir(doc_dir):
            file_path = os.path.join(doc_dir, filename)
            if os.path.isfile(file_path):
                # 检查文件类型是否支持
                ext = os.path.splitext(filename)[1].lower()
                if any(ext in exts for exts in SUPPORTED_FILE_TYPES.values()):
                    file_paths.append(file_path)
                else:
                    print(f"[WARN] 跳过不支持的文件类型: {filename}")

        if not file_paths:
            print("[INFO] 未找到需要上传的支持类型文件")
            return

        # 步骤3：批量上传文件
        print(f"[INFO] 准备上传文件: {[os.path.basename(p) for p in file_paths]}")
        uploaded_doc_ids = []

        # 逐文件上传避免同时打开过多文件句柄
        for file_path in file_paths:
            with open(file_path, "rb") as f:
                print(f"[INFO] 开始上传文件: {os.path.basename(file_path)}")
                docs = client.upload_documents(dataset_id, [f])
                if docs:
                    doc_id = docs[0].get("id")  # 根据client.py的返回结构调整
                    uploaded_doc_ids.append(doc_id)
                    print(f"[INFO] 文件上传成功，文档ID: {doc_id}")
                else:
                    print(f"[WARN] 文件上传未返回有效文档信息: {file_path}")

        if not uploaded_doc_ids:
            print("[INFO] 无文件上传成功，跳过解析步骤")
            return

        # 步骤4：触发文档解析
        print(f"[INFO] 开始触发解析，文档数量: {len(uploaded_doc_ids)}")
        parse_result = client.parse_documents(
            dataset_id=dataset_id, document_ids=uploaded_doc_ids
        )

        if parse_result.get("code") == 0:
            print(f"[INFO] 解析请求提交成功，服务端响应: {parse_result}")
        else:
            print(f"[WARN] 解析请求提交失败，错误信息: {parse_result.get('message')}")

    except (APIError, ResourceNotFoundError, FileNotFoundError, NotADirectoryError) as e:
        print(f"[ERROR] 执行过程中发生异常: {str(e)}")
        raise  # 保持异常传播以便上层处理
    except Exception as e:
        print(f"[ERROR] 发生未知异常: {str(e)}")
        raise


if __name__ == "__main__":
    # 配置命令行参数解析
    parser = argparse.ArgumentParser(description="批量上传文档目录到RagFlow数据集并触发解析")
    parser.add_argument("dataset_name", type=str, help="目标数据集名称（不存在时自动创建）")
    parser.add_argument("doc_dir", type=str, help="需要上传的文档目录绝对路径或相对路径")
    
    args = parser.parse_args()
    
    # 调用核心函数
    upload_and_parse_documents(args.dataset_name, args.doc_dir)
