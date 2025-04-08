import os
import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, PostgresDsn, field_validator, ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    
    # 调试模式
    DEBUG: bool = False
    
    # 配置文件路径
    FORMAT_JSON_PATH: str = "config/format.json"
    TERMINOLOGY_FILE_PATH: str = "config/terminology.txt"
    
    # CORS配置
    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # 项目名称
    PROJECT_NAME: str = "KeyInfoExtraction"
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI: Optional[str] = "mysql+pymysql://root:201982@localhost:3306/key_info_extraction"
    
    # 文件上传配置
    UPLOAD_DIR: str = "./uploads"
    ALLOWED_EXTENSIONS: List[str] = ["doc", "docx"]
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB
    
    # 输出目录
    OUTPUT_DIR: str = "./output"
    
    # LLM API配置
    LLM_MODE: str = "api"  # 可选值: "api" 或 "server"，分别表示使用API密钥或本地服务器
    LLM_API_KEY: str = "api-key"
    LLM_MODEL: str = "api-model-name"
    LLM_SERVER_IP: str = "ip"
    LLM_SERVER_PORT: str = "port"
    LLM_SERVER_MODEL: str = "deepseek-r1:32b"
    
    model_config = ConfigDict(case_sensitive=True, env_file=".env")

# 创建设置实例
settings = Settings()

# 确保上传和输出目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True) 