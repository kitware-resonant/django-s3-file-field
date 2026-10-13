import ky, { type KyInstance } from 'ky';

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

/**
 * The progress of an upload.
 *
 * While uploading, the byte counts are reported as each part completes, so they advance in
 * steps of the server's part size; a file no larger than one part reports only its completion.
 */
export interface S3FileFieldProgress {
  readonly uploaded?: number;
  readonly total?: number;
  readonly state: S3FileFieldProgressState;
}

export type S3FileFieldProgressCallback = (progress: S3FileFieldProgress) => void;

export interface S3FileFieldClientOptions {
  readonly baseUrl: string;
  readonly apiConfig?: RequestInit;
}

export default class S3FileFieldClient {
  protected readonly api: KyInstance;

  /**
   * Create an S3FileFieldClient instance.
   *
   * @param options {S3FileFieldClientOptions} - A Object with all arguments.
   * @param options.baseUrl - The URL of the upload API, where "s3_file_field.urls" is mounted.
   * @param [options.apiConfig] - Options for the `fetch` requests to the Django API, such as
   *                              `headers` for authentication, or `credentials`.
   */
  constructor({ baseUrl, apiConfig = {} }: S3FileFieldClientOptions) {
    this.api = ky.create({
      ...apiConfig,
      // Add a trailing slash, so that endpoint paths extend the base URL's path
      // biome-ignore lint/performance/useTopLevelRegex: constructor is called infrequently
      baseUrl: baseUrl.replace(/\/?$/, '/'),
      // These requests are safe to repeat after a transient failure
      retry: { methods: ['post'], retryOnTimeout: true },
    });
  }

  /**
   * Initiates an upload.
   *
   * @param file - The file to upload.
   * @param fieldId - The Django field identifier.
   */
  protected initiateUpload(file: File, fieldId: string): Promise<InitiationResponse> {
    return this.api
      .post('initiate/', {
        json: {
          // biome-ignore-start lint/style/useNamingConvention: API interface names
          field: fieldId,
          file_name: file.name,
          file_size: file.size,
          // An unknown type is ''
          content_type: file.type || 'application/octet-stream',
          // biome-ignore-end lint/style/useNamingConvention: API interface names
        },
      })
      .json<InitiationResponse>();
  }

  /**
   * Uploads all the parts in a file directly to an object store in serial.
   *
   * @param file - The file to upload.
   * @param parts - The list of parts describing how to break up the file.
   * @param onProgress - A callback for upload progress, called as each part completes.
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
      const etag = await this.uploadPart(part, chunk);
      completedParts.push({
        // biome-ignore-start lint/style/useNamingConvention: API interface names
        part_number: part.part_number,
        etag,
        // biome-ignore-end lint/style/useNamingConvention: API interface names
      });
      fileOffset += part.size;
      onProgress({
        uploaded: fileOffset,
        total: file.size,
        state: S3FileFieldProgressState.Uploading,
      });
    }
    return completedParts;
  }

  /**
   * Uploads the content of one part directly to an object store, returning its ETag.
   *
   * @param part - The presigned part to upload.
   * @param chunk - The content of the part.
   */
  protected async uploadPart(part: PresignedPart, chunk: Blob): Promise<string> {
    // A PUT which fails transiently is retried by ky's default policy
    const response = await ky.put(part.url, {
      body: chunk,
      // A large part may legitimately take minutes to upload
      timeout: false,
    });
    const etag = response.headers.get('ETag');
    if (etag === null) {
      // The object store's CORS configuration must expose this header
      throw new Error('ETag header missing from response.', { cause: response });
    }
    return etag;
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
    const completion = await this.api
      .post('complete/', {
        json: {
          // biome-ignore-start lint/style/useNamingConvention: API interface names
          upload_token: initiation.upload_token,
          parts,
          // biome-ignore-end lint/style/useNamingConvention: API interface names
        },
      })
      .json<CompletionResponse>();

    // Send the CompleteMultipartUpload operation to S3
    const result = await ky
      .post(completion.url, {
        // The AWS CompleteMultipartUpload docs specify no Content-Type, and S3 misinterprets the
        // body under some types. A string body would be sent as "text/plain", but a Blob without a
        // type is sent with no header.
        body: new Blob([completion.body]),
        // Completing is safe to repeat, so retry it as ky would a PUT
        retry: { methods: ['post'] },
        // S3 responds with 200 as soon as it begins assembling the object, which may take
        // minutes, during which it sends whitespace; the result arrives only at the end
        timeout: false,
      })
      .text();
    // The result can be an error, despite the 200
    if (result.includes('<Error>')) {
      throw new Error('CompleteMultipartUpload failed.', { cause: result });
    }
  }

  /**
   * Finalizes an upload.
   *
   * This will only succeed if the object is already present in the object store.
   *
   * @param uploadToken - The signed token identifying the upload.
   */
  protected async finalize(uploadToken: string): Promise<string> {
    const finalization = await this.api
      .post('finalize/', {
        json: {
          // biome-ignore-start lint/style/useNamingConvention: API interface names
          upload_token: uploadToken,
          // biome-ignore-end lint/style/useNamingConvention: API interface names
        },
      })
      .json<FinalizationResponse>();
    return finalization.field_value;
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
