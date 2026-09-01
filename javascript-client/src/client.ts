import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios';

import type {
  CompletedPart,
  CompletionResponse,
  FinalizationResponse,
  InitiationResponse,
  PresignedPart,
} from './types.js';

export type * from './types.js';

export enum S3FileFieldProgressState {
  Initiating = 0,
  Uploading = 1,
  Completing = 2,
  Finalizing = 3,
  Done = 4,
}

export interface S3FileFieldProgress {
  readonly uploaded?: number;
  readonly total?: number;
  readonly state: S3FileFieldProgressState;
}

export type S3FileFieldProgressCallback = (progress: S3FileFieldProgress) => void;

export interface S3FileFieldClientOptions {
  readonly baseUrl: string;
  readonly apiConfig?: AxiosRequestConfig;
}

export default class S3FileFieldClient {
  protected readonly api: AxiosInstance;

  /**
   * Create an S3FileFieldClient instance.
   *
   * @param options {S3FileFieldClientOptions} - A Object with all arguments.
   * @param options.baseUrl - The absolute URL to the Django server.
   * @param [options.apiConfig] - An axios configuration to use for Django API requests.
   *                              Can be extracted from an existing axios instance via `.defaults`.
   */
  constructor({ baseUrl, apiConfig = {} }: S3FileFieldClientOptions) {
    this.api = axios.create({
      ...apiConfig,
      // Add a trailing slash
      // biome-ignore lint/performance/useTopLevelRegex: constructor is called infrequently
      baseURL: baseUrl.replace(/\/?$/, '/'),
    });
  }

  /**
   * Initiates an upload.
   *
   * @param file - The file to upload.
   * @param fieldId - The Django field identifier.
   */
  protected async initiateUpload(file: File, fieldId: string): Promise<InitiationResponse> {
    const response = await this.api.post<InitiationResponse>('initiate/', {
      // biome-ignore-start lint/style/useNamingConvention: API interface names
      field: fieldId,
      file_name: file.name,
      file_size: file.size,
      // An unknown type is ''
      content_type: file.type || 'application/octet-stream',
      // biome-ignore-end lint/style/useNamingConvention: API interface names
    });
    return response.data;
  }

  /**
   * Uploads all the parts in a file directly to an object store in serial.
   *
   * @param file - The file to upload.
   * @param parts - The list of parts describing how to break up the file.
   * @param onProgress - A callback for upload progress.
   */
  protected async uploadParts(
    file: File,
    parts: PresignedPart[],
    onProgress: S3FileFieldProgressCallback,
  ): Promise<CompletedPart[]> {
    const completedParts: CompletedPart[] = [];
    let fileOffset = 0;
    for (const part of parts) {
      const chunk = file.slice(fileOffset, fileOffset + part.size);
      // biome-ignore lint/performance/noAwaitInLoops: parts are uploaded serially by design
      const response = await axios.put(part.url, chunk, {
        onUploadProgress: (e) => {
          onProgress({
            uploaded: fileOffset + e.loaded,
            total: file.size,
            state: S3FileFieldProgressState.Uploading,
          });
        },
      });
      const { etag } = response.headers;
      // ETag might be absent due to CORS misconfiguration, but dumb typings from Axios also make it
      // structurally possible to be many other types
      if (typeof etag !== 'string') {
        throw new Error('ETag header missing from response.');
      }
      completedParts.push({
        // biome-ignore-start lint/style/useNamingConvention: API interface names
        part_number: part.part_number,
        etag,
        // biome-ignore-end lint/style/useNamingConvention: API interface names
      });
      fileOffset += part.size;
    }
    return completedParts;
  }

  /**
   * Completes an upload.
   *
   * The object will exist in the object store after completion.
   *
   * @param initiation - The initiation response describing the upload.
   * @param parts - The parts that were uploaded.
   */
  protected async completeUpload(
    initiation: InitiationResponse,
    parts: CompletedPart[],
  ): Promise<void> {
    const response = await this.api.post<CompletionResponse>('complete/', {
      // biome-ignore-start lint/style/useNamingConvention: API interface names
      upload_token: initiation.upload_token,
      parts,
      // biome-ignore-end lint/style/useNamingConvention: API interface names
    });
    const { url, body } = response.data;

    // Send the CompleteMultipartUpload operation to S3
    await axios.post(url, body, {
      headers: {
        // By default, Axios sets "Content-Type: application/x-www-form-urlencoded" on POST
        // requests. This causes AWS's API to interpret the request body as additional parameters
        // to include in the signature validation, causing it to fail.
        // So, do not send this request with any Content-Type, as that is what's specified by the
        // CompleteMultipartUpload docs.
        // Unsetting default headers via "transformRequest" is awkward (since the headers aren't
        // flattened), so this is actually; the most straightforward way; the null value is passed
        // through to XMLHttpRequest, then ignored.
        'Content-Type': null,
      },
    });
  }

  /**
   * Finalizes an upload.
   *
   * This will only succeed if the object is already present in the object store.
   *
   * @param uploadToken - The signed token identifying the upload.
   */
  protected async finalize(uploadToken: string): Promise<string> {
    const response = await this.api.post<FinalizationResponse>('finalize/', {
      // biome-ignore-start lint/style/useNamingConvention: API interface names
      upload_token: uploadToken,
      // biome-ignore-end lint/style/useNamingConvention: API interface names
    });
    return response.data.field_value;
  }

  /**
   * Uploads a file using multipart upload.
   *
   * @param file - The file to upload.
   * @param fieldId - The Django field identifier.
   * @param [onProgress] - A callback for upload progress.
   */
  public async uploadFile(
    file: File,
    fieldId: string,
    onProgress: S3FileFieldProgressCallback = () => {
      /* no-op */
    },
  ): Promise<string> {
    onProgress({ state: S3FileFieldProgressState.Initiating });
    const initiation = await this.initiateUpload(file, fieldId);
    onProgress({ state: S3FileFieldProgressState.Uploading, uploaded: 0, total: file.size });
    const completedParts = await this.uploadParts(file, initiation.parts, onProgress);
    onProgress({ state: S3FileFieldProgressState.Completing });
    await this.completeUpload(initiation, completedParts);
    onProgress({ state: S3FileFieldProgressState.Finalizing });
    const fieldValue = await this.finalize(initiation.upload_token);
    onProgress({ state: S3FileFieldProgressState.Done });
    return fieldValue;
  }
}
