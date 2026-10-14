import ky, { isKyError, type KyInstance } from 'ky';
import pMap from 'p-map';

import { S3FileFieldError, s3ErrorCode } from './error.js';

import type {
  CompletedPart,
  CompletionResponse,
  FinalizationResponse,
  InitiationResponse,
  PresignedPart,
} from './types.js';

export { S3FileFieldError } from './error.js';
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

  // The number of parts uploaded at once: enough to hide each part's fixed latency, while leaving
  // room under a browser's limit of 6 connections per host; also what AWS's browser SDK uses
  protected readonly concurrency: number = 4;

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
   * @param signal - A signal to cancel the upload.
   */
  protected initiateUpload(
    file: File,
    fieldId: string,
    signal: AbortSignal | undefined,
  ): Promise<InitiationResponse> {
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
        signal,
      })
      .json<InitiationResponse>();
  }

  /**
   * Uploads all the parts in a file directly to an object store, several at once.
   *
   * @param file - The file to upload.
   * @param parts - The list of parts describing how to break up the file.
   * @param onProgress - A callback for upload progress, called as each part completes.
   * @param signal - A signal to cancel the upload.
   */
  protected async uploadParts(
    file: File,
    parts: PresignedPart[],
    onProgress: S3FileFieldProgressCallback,
    signal: AbortSignal | undefined,
  ): Promise<CompletedPart[]> {
    // Each part is the next of the file's content; slicing is lazy, so this reads nothing yet
    let remaining: Blob = file;
    const chunks = parts.map((part) => {
      const chunk = remaining.slice(0, part.size);
      remaining = remaining.slice(part.size);
      return { part, chunk };
    });

    let uploaded = 0;
    // When one part fails (or the upload is canceled), the others in progress are abandoned
    const controller = new AbortController();
    const partSignal =
      signal === undefined ? controller.signal : AbortSignal.any([signal, controller.signal]);
    try {
      return await pMap(
        chunks,
        async ({ part, chunk }) => {
          const etag = await this.uploadPart(part, chunk, partSignal);
          uploaded += part.size;
          onProgress({ uploaded, total: file.size, state: S3FileFieldProgressState.Uploading });
          return {
            // biome-ignore-start lint/style/useNamingConvention: API interface names
            part_number: part.part_number,
            etag,
            // biome-ignore-end lint/style/useNamingConvention: API interface names
          };
        },
        { concurrency: this.concurrency, signal: partSignal },
      );
    } catch (error) {
      controller.abort();
      throw error;
    }
  }

  /**
   * Uploads the content of one part directly to an object store, returning its ETag.
   *
   * @param part - The presigned part to upload.
   * @param chunk - The content of the part.
   * @param signal - A signal to abandon the upload.
   */
  protected async uploadPart(
    part: PresignedPart,
    chunk: Blob,
    signal: AbortSignal,
  ): Promise<string> {
    // A PUT which fails transiently is retried by ky's default policy
    const response = await ky.put(part.url, {
      body: chunk,
      // A large part may legitimately take minutes to upload
      timeout: false,
      signal,
    });
    const etag = response.headers.get('ETag');
    if (etag === null) {
      // The object store's CORS configuration must expose this header
      throw new S3FileFieldError(
        S3FileFieldProgressState.Uploading,
        'ETag header missing from response.',
        { status: response.status, cause: response },
      );
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
   * @param signal - A signal to cancel the upload.
   */
  protected async completeUpload(
    initiation: InitiationResponse,
    parts: CompletedPart[],
    signal: AbortSignal | undefined,
  ): Promise<void> {
    const completion = await this.api
      .post('complete/', {
        json: {
          // biome-ignore-start lint/style/useNamingConvention: API interface names
          upload_token: initiation.upload_token,
          parts,
          // biome-ignore-end lint/style/useNamingConvention: API interface names
        },
        signal,
      })
      .json<CompletionResponse>();

    // Send the CompleteMultipartUpload operation to S3
    await ky.post(completion.url, {
      // The AWS CompleteMultipartUpload docs specify no Content-Type, and S3 misinterprets the
      // body under some types. A string body would be sent as "text/plain", but a Blob without a
      // type is sent with no header.
      body: new Blob([completion.body]),
      // Retry completing as ky would a PUT; the hook below handles the one way a repeat can differ
      retry: { methods: ['post'] },
      // S3 responds with 200 as soon as it begins assembling the object, which may take
      // minutes, during which it sends whitespace; the result arrives only at the end
      timeout: false,
      signal,
      hooks: {
        afterResponse: [
          // The result can be an error, despite the 200
          async ({ response, retryCount }) => {
            const body = await response.text();
            const code = s3ErrorCode(body);
            if (code === undefined) {
              // Normal success
              return undefined;
            }
            if (code === 'NoSuchUpload' && retryCount > 0) {
              // Completing is not repeatable: when an attempt succeeds but its response is lost,
              // the retry finds the upload gone. Finalization checks that the object exists, so
              // let it decide, by treating this as success.
              return new Response(body, { status: 200, headers: response.headers });
            }
            // Give the error the status it would have had if reported in the header (500 for an
            // internal error, which S3 asks to be retried; 400 for the rest, which are permanent),
            // so ky potentially retries it.
            return new Response(body, {
              status: code === 'InternalError' ? 500 : 400,
              statusText: code,
              headers: response.headers,
            });
          },
        ],
      },
    });
  }

  /**
   * Finalizes an upload.
   *
   * This will only succeed if the object is already present in the object store.
   *
   * @param uploadToken - The signed token identifying the upload.
   * @param signal - A signal to cancel the upload.
   */
  protected async finalize(uploadToken: string, signal: AbortSignal | undefined): Promise<string> {
    const finalization = await this.api
      .post('finalize/', {
        json: {
          // biome-ignore-start lint/style/useNamingConvention: API interface names
          upload_token: uploadToken,
          // biome-ignore-end lint/style/useNamingConvention: API interface names
        },
        signal,
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
   * @param [signal] - A signal to cancel the upload, which then rejects with the signal's reason
   *                   (an "AbortError", by default) rather than an `S3FileFieldError`.
   */
  public async uploadFile(
    file: File,
    fieldId: string,
    onProgress: S3FileFieldProgressCallback = () => {
      /* no-op */
    },
    signal?: AbortSignal,
  ): Promise<string> {
    // The last reported stage is the one which fails
    let stage = S3FileFieldProgressState.Initiating;
    const reportProgress: S3FileFieldProgressCallback = (progress) => {
      stage = progress.state;
      onProgress(progress);
    };
    try {
      reportProgress({ state: S3FileFieldProgressState.Initiating });
      const initiation = await this.initiateUpload(file, fieldId, signal);
      reportProgress({ state: S3FileFieldProgressState.Uploading, uploaded: 0, total: file.size });
      const completedParts = await this.uploadParts(file, initiation.parts, reportProgress, signal);
      reportProgress({ state: S3FileFieldProgressState.Completing });
      await this.completeUpload(initiation, completedParts, signal);
      reportProgress({ state: S3FileFieldProgressState.Finalizing });
      const fieldValue = await this.finalize(initiation.upload_token, signal);
      reportProgress({ state: S3FileFieldProgressState.Done });
      return fieldValue;
    } catch (error) {
      // Other errors (as from a bug, or an abort) are not failures of the upload itself
      if (isKyError(error)) {
        throw S3FileFieldError.fromKyError(error, stage);
      }
      throw error;
    }
  }
}
