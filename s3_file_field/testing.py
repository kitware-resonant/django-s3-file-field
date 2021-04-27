from __future__ import annotations

from dataclasses import dataclass
import io
from typing import BinaryIO, Dict, List

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


class S3FileFieldTestClient:
    def __init__(self, api_client, base_url: str):
        """
        Initialize a S3FileField test client.

        Args:
            api_client: An instance of `rest_framework.test.APIClient`.
            base_url: The relative path that s3_file_field.urls is mounted at.
        """
        self.api_client = api_client
        self.base_url = base_url.rstrip('/')

    def _initialize_upload(self, file: _File, field_id: str) -> Dict:
        resp = self.api_client.post(
            f'{self.base_url}/upload-initialize/',
            {
                'field_id': field_id,
                'file_name': file.name,
                'file_size': file.size,
            },
            format='json',
        )

        assert resp.status_code < 400
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
        resp = self.api_client.post(
            f'{self.base_url}/upload-complete/',
            {
                'upload_id': multipart_info['upload_id'],
                'parts': upload_infos,
                'upload_signature': multipart_info['upload_signature'],
            },
            format='json',
        )

        assert resp.status_code < 400
        completion_data = resp.json()

        complete_resp = requests.post(completion_data['complete_url'], data=completion_data['body'])
        complete_resp.raise_for_status()

    def _finalize(self, multipart_info: Dict) -> str:
        resp = self.api_client.post(
            f'{self.base_url}/finalize/',
            {
                'upload_signature': multipart_info['upload_signature'],
            },
            format='json',
        )
        assert resp.status_code < 400
        return resp.json()

    def upload_file(self, file_stream: BinaryIO, file_name: str, field_id: str) -> str:
        file = _File.from_stream(file_stream, file_name)
        multipart_info = self._initialize_upload(file, field_id)
        upload_infos = self._upload_parts(file, multipart_info['parts'])
        self._complete_upload(multipart_info, upload_infos)
        field_value = self._finalize(multipart_info)
        return field_value
