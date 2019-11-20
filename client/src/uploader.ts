import S3 from 'aws-sdk/clients/s3';
import { DEFAULT_BASE_URL, fetchOptions } from './constants';

interface PrepareResponse {
  accessKeyId: string;
  secretAccessKey: string;
  sessionToken: string;
  bucketName: string;
  objectKey: string;
}

interface FinalizeResponse {
  id?: string;
  name: string;
}

export interface UploadResult extends FinalizeResponse {
  state: 'aborted' | 'successful' | 'error';
  msg: string;
  error?: Error;
}

export declare type EProgressState = 'initial' | 'uploading' | 'preparing' | 'finishing' | 'done' | 'aborted';

export interface UploadOptions {
  baseUrl: string;
  onProgress(progress: { percentage: number; loaded: number; total: number; state: EProgressState }): void;
  abortSignal(onAbort: () => void): void;
}

// the percent reserved for upload initiate and finalize operations
const OVERHEAD_PERCENT = 0.05;


export async function uploadFile(file: File, options: Partial<UploadOptions> = {}): Promise<UploadResult> {
  const { onProgress, baseUrl, abortSignal } = Object.assign({
    onProgress: () => undefined,
    baseUrl: DEFAULT_BASE_URL,
    abortSignal: () => undefined
  } as UploadOptions, options);

  const size = file.size;
  const progress = (state: EProgressState, percentage: number, loaded = 0, total = size): void => {
    onProgress({
      percentage,
      loaded,
      total,
      state
    });
  }

  progress('preparing', 0);

  let initUpload: PrepareResponse;
  try {
    initUpload = await fetch(`${baseUrl}/prepare-upload/`, {
      ...fetchOptions(),
      method: 'POST',
      body: JSON.stringify({
        name: file.name,
      }),
    }).then((r) => r.json()) as PrepareResponse;

    progress('uploading', OVERHEAD_PERCENT / 2);
  } catch (err) {
    return {
      id: undefined,
      name: file.name,
      state: 'error',
      msg: 'Failed to prepare upload token',
      error: err
    }
  }

  const s3 = new S3({
    apiVersion: '2006-03-01',
    accessKeyId: initUpload.accessKeyId,
    secretAccessKey: initUpload.secretAccessKey,
    sessionToken: initUpload.sessionToken,
  });

  const task = s3.upload({
    Bucket: initUpload.bucketName,
    Key: initUpload.objectKey,
    Body: file,
  });

  task.on('httpUploadProgress', (evt): void => {
    const s3Progress = evt.loaded / evt.total;
    // s3Progress only spans the total fileProgress range [0.05, 0.9)
    progress('uploading', OVERHEAD_PERCENT / 2 + s3Progress * (1 - OVERHEAD_PERCENT), evt.loaded, evt.total);
  });

  function finalizeUpload(status: 'uploaded' | 'aborted' = 'uploaded'): Promise<FinalizeResponse> {
    return fetch(`${baseUrl}/finalize-upload/`, {
      ...fetchOptions(),
      method: 'POST',
      body: JSON.stringify({
        name: file.name,
        id: initUpload.objectKey,
        status,
        upload: initUpload,
      }),
    }).then((r) => r.json());
  }

  return new Promise<UploadResult>((resolve) => {
    abortSignal(() => {
      task.abort();
      progress('finishing', 1);
      finalizeUpload('aborted').then((r) => {
        progress('aborted', 1);
        return {
          ...r,
          state: 'aborted',
          msg: 'Upload aborted',
        } as UploadResult;
      }).then(resolve).catch((error) => {
        resolve({
          name: file.name,
          state: 'error',
          msg: 'Error occurred while aborting the upload',
          error
        });
      });
    });

    task.promise().then(() => {
      progress('finishing', 1, size);
      finalizeUpload().then((r) => {
        progress('done', 1, size);
        return {
          ...r,
          state: 'successful'
        } as UploadResult;
      }).then(resolve).catch((error) => {
        resolve({
          name: file.name,
          state: 'error',
          msg: 'Error occurred while finishing the upload',
          error
        });
      }).catch((error) => {
        resolve({
          name: file.name,
          state: 'error',
          msg: 'Error occurred while uploading',
          error
        });
      });
    });
  });
}
