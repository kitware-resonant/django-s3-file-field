import logging
from typing import Iterable, List, Optional

from django.apps import AppConfig
from django.core import checks

from ._multipart import MultipartManager
from ._registry import iter_storages

logger = logging.getLogger(__name__)


@checks.register()
def test_bucket_access(
    app_configs: Optional[Iterable[AppConfig]], **kwargs
) -> List[checks.CheckMessage]:
    for storage in iter_storages():
        if not MultipartManager.supported_storage(storage):
            continue
        multipart = MultipartManager.from_storage(storage)
        try:
            multipart.test_upload()
        except Exception:
            msg = 'Unable to fully access the storage bucket.'
            logger.exception(msg)
            return [checks.Error(msg, obj=storage, id='s3_file_field.E002')]
    return []
