import S3 from 'aws-sdk/clients/s3';
import { FETCH_OPTIONS, DEFAULT_BASE_URL } from './constants';

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

export interface IUploadResult extends IFinalizeResponse {
  state: 'aborted' | 'successful' | 'error';
  msg: string;
  error?: any;
}

export declare type EProgressState = 'initial' | 'uploading' | 'preparing' | 'finishing' | 'done' | 'aborted';

export interface IUploadOptions {
  baseUrl: string;
  onProgress(progress: { percentage: number, loaded: number, total: number, state: EProgressState }): void;
  abortSignal(onAbort: () => void): void;
}

// the percent reserved for upload initiate and finalize operations
const OVERHEAD_PERCENT = 0.05;


export async function uploadFile(file: File, options: Partial<IUploadOptions> = {}) {
  const { onProgress, baseUrl, abortSignal } = Object.assign({
    onProgress: () => undefined,
    baseUrl: DEFAULT_BASE_URL,
    abortSignal: () => undefined
  } as IUploadOptions, options);

  const size = file.size;
  onProgress({
    percentage: 0,
    loaded: 0,
    total: size,
    state: 'preparing'
  });

  let initUpload: IPrepareResponse;
  try {
    initUpload = await fetch(`${baseUrl}/prepare-upload`, {
      ...FETCH_OPTIONS,
      method: 'POST',
      body: JSON.stringify({
        name: file.name,
      }),
    }).then((r) => r.json()) as IPrepareResponse;


    onProgress({
      percentage: OVERHEAD_PERCENT / 2,
      loaded: 0,
      total: size,
      state: 'uploading'
    });
  } catch (err) {
    return {
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

  task.on('httpUploadProgress', (evt) => {
    const s3Progress = evt.loaded / evt.total;
    // s3Progress only spans the total fileProgress range [0.05, 0.9)
    onProgress({
      percentage: OVERHEAD_PERCENT / 2 + s3Progress * (1 - OVERHEAD_PERCENT),
      loaded: evt.loaded,
      total: evt.total,
      state: 'uploading'
    });
  });

  function finalizeUpload(status: 'uploaded' | 'aborted' = 'uploaded') {
    return fetch(`${baseUrl}/finalize-upload`, {
      ...FETCH_OPTIONS,
      method: 'POST',
      body: JSON.stringify({
        name: file.name,
        status,
      }),
    }).then((r) => r.json() as Promise<IFinalizeResponse>);
  }

  return new Promise<IUploadResult>(async (resolve) => {
    abortSignal(() => {
      task.abort();
      onProgress({
        percentage: 1,
        loaded: 0,
        total: size,
        state: 'finishing'
      });
      finalizeUpload('aborted').then((r) => {
        onProgress({
          percentage: 1,
          loaded: 0,
          total: size,
          state: 'aborted'
        });
        return {
          ...r,
          state: 'aborted',
          msg: 'Upload aborted',
        } as IUploadResult;
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
      onProgress({
        percentage: 1,
        loaded: 0,
        total: size,
        state: 'finishing'
      });
      finalizeUpload().then((r) => {
        onProgress({
          percentage: 1,
          loaded: size,
          total: size,
          state: 'done'
        });
        return {
          ...r,
          state: 'successful'
        } as IUploadResult;
      }).then(resolve).catch((error) => {
        resolve({
          name: file.name,
          state: 'error',
          msg: 'Error occurred while finishing the upload',
          error
        });;
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
