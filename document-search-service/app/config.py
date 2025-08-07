
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    embedding_model_name: str = 'all-MiniLM-L6-v2'
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "384"))
    use_gpu: bool = os.getenv("USE_GPU", "false").lower() == "true"
    # Fixed index path - use explicit path or indexes relative to service root
    index_path: str = os.getenv("INDEX_PATH", "./indexes")
    data_path: str = os.getenv("UPLOAD_PATH", "./data")

    class Config:
        env_file = ".env"

settings = Settings()
