import S3 from 'aws-sdk/clients/s3';
import { FETCH_OPTIONS } from './constants';

interface IPrepareResponse {
  accessKeyId: string;
  secretAccessKey: string;
  sessionToken: string;
  bucketName: string;
  objectKey: string;
}

interface IFinalizeResponse {
  name: string;
}

// the percent reserved for upload initiate and finalize operations
const OVERHEAD_PERCENT = 0.05;

export async function uploadFile(baseUrl: string, file: File, onProgress: (p: number) => void = () => undefined) {

  onProgress(0);
  const initUpload = await fetch(`${baseUrl}/prepare-upload`, {
    ...FETCH_OPTIONS,
    method: 'POST',
    body: JSON.stringify({
      name: file.name,
    }),
  }).then((r) => r.json()) as IPrepareResponse;

  onProgress(OVERHEAD_PERCENT / 2);

  const s3 = new S3({
    apiVersion: '2006-03-01',
    accessKeyId: initUpload.accessKeyId,
    secretAccessKey: initUpload.secretAccessKey,
    sessionToken: initUpload.sessionToken,
  });

  await s3
    .upload({
      Bucket: initUpload.bucketName,
      Key: initUpload.objectKey,
      Body: file,
    })
    .on('httpUploadProgress', (evt) => {
      const s3Progress = evt.loaded / evt.total;
      // s3Progress only spans the total fileProgress range [0.05, 0.9)
      onProgress(OVERHEAD_PERCENT / 2 + s3Progress * (1 - OVERHEAD_PERCENT));
    })
    .promise();

  const finalized = await fetch(`${baseUrl}/finalize-upload`, {
    ...FETCH_OPTIONS,
    method: 'POST',
    body: JSON.stringify({
      name: file.name,
    }),
  }).then((r) => r.json()) as IFinalizeResponse;

  onProgress(1);

  return finalized.name;
}
