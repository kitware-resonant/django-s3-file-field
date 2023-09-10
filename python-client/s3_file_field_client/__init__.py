from __future__ import annotations

from dataclasses import dataclass
import io
from typing import BinaryIO, Dict, List, Optional

import requests


@dataclass
class _File:
    name: str
    size: int
    stream: BinaryIO

    @classmethod
    def from_stream(cls, stream: BinaryIO, name: str) -> _File:
        if not stream.seekable():
            raise Exception('File stream is not seekable.')

        stream.seek(0, io.SEEK_END)
        size = stream.tell()
        stream.seek(0, io.SEEK_SET)

        return cls(name=name, size=size, stream=stream)


class S3FileFieldClient:
    def __init__(self, base_url: str, api_session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip('/')
        self.api_session = requests.Session() if api_session is None else api_session

    def _initialize_upload(self, file: _File, field_id: str) -> Dict:
        resp = self.api_session.post(
            f'{self.base_url}/upload-initialize/',
            json={
                'field_id': field_id,
                'file_name': file.name,
                'file_size': file.size,
                'content_type': file.type,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def _upload_part(self, part_bytes: bytes, part_initialization: Dict):
        resp = requests.put(part_initialization['upload_url'], data=part_bytes)
        resp.raise_for_status()

        etag = resp.headers['ETag']

        return {
            'part_number': part_initialization['part_number'],
            'size': part_initialization['size'],
            'etag': etag,
        }

    def _upload_parts(self, file: _File, part_initializations: List[Dict]) -> List[Dict]:
        return [
            self._upload_part(file.stream.read(part_initialization['size']), part_initialization)
            for part_initialization in part_initializations
        ]

    def _complete_upload(self, multipart_info: Dict, upload_infos: List[Dict]) -> None:
        resp = self.api_session.post(
            f'{self.base_url}/upload-complete/',
            json={
                'upload_id': multipart_info['upload_id'],
                'parts': upload_infos,
                'upload_signature': multipart_info['upload_signature'],
            },
        )
        resp.raise_for_status()
        completion_data = resp.json()

        complete_resp = requests.post(completion_data['complete_url'], data=completion_data['body'])
        complete_resp.raise_for_status()

    def _finalize(self, multipart_info: Dict) -> str:
        resp = self.api_session.post(
            f'{self.base_url}/finalize/',
            json={
                'upload_signature': multipart_info['upload_signature'],
            },
        )
        resp.raise_for_status()
        return resp.json()['field_value']

    def upload_file(self, file_stream: BinaryIO, file_name: str, field_id: str) -> str:
        file = _File.from_stream(file_stream, file_name)
        multipart_info = self._initialize_upload(file, field_id)
        upload_infos = self._upload_parts(file, multipart_info['parts'])
        self._complete_upload(multipart_info, upload_infos)
        field_value = self._finalize(multipart_info)
        return field_value
