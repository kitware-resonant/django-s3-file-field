from .api import Minio
from .error import S3Error

__version__: str

__all__ = [
    "Minio",
    "S3Error",
]
