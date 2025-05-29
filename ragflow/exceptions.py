class RagFlowError(Exception):
    """基础异常类"""
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code
        self.message = message

class AuthenticationError(RagFlowError):
    """认证错误"""
    pass

class APIError(RagFlowError):
    """API调用错误"""
    pass

class ValidationError(RagFlowError):
    """数据验证错误"""
    pass

class ResourceNotFoundError(RagFlowError):
    """资源未找到错误"""
    pass