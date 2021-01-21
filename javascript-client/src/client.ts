import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

// Description of a part from initializeUpload()
interface PartInfo {
  part_number: number;
  size: number;
  upload_url: string;
}
// Description of the upload from initializeUpload()
interface MultipartInfo {
  upload_signature: string;
  object_key: string;
  upload_id: string;
  parts: PartInfo[];
}
// Description of a part which has been uploaded by uploadPart()
interface UploadedPart {
  part_number: number;
  size: number;
  etag: string;
}

export enum S3FileFieldResultState {
  Aborted,
  Successful,
  Error,
}
// Return value from uploadFile()
export interface S3FileFieldResult {
  value: string;
  state: S3FileFieldResultState;
}

export enum S3FileFieldProgressState {
  Initializing,
  Sending,
  Finalizing,
  Done,
}

export interface S3FileFieldProgress {
  readonly uploaded?: number;
  readonly total?: number;
  readonly state: S3FileFieldProgressState;
}

export type S3FileFieldProgressCallback = (progress: S3FileFieldProgress) => void;

export interface S3FileFieldClientOptions {
  readonly baseUrl: string;
  readonly onProgress?: S3FileFieldProgressCallback;
  readonly apiConfig?: AxiosRequestConfig
}

export default class S3FileFieldClient {
  protected readonly api: AxiosInstance;

  protected readonly onProgress: S3FileFieldProgressCallback;

  /**
   * Create an S3FileFieldClient instance.
   *
   * @param options {S3FileFieldClientOptions} - A Object with all arguments.
   * @param options.baseUrl - The absolute URL to the Django server.
   * @param [options.onProgress] - A callback for upload progress.
   * @param [options.apiConfig] - An axios configuration to use for Django API requests.
   *                              Can be extracted from an existing axios instance via `.defaults`.
   */
  constructor(
    {
      baseUrl,
      onProgress = () => { /* no-op */ },
      apiConfig = {},
    }: S3FileFieldClientOptions,
  ) {
    this.onProgress = onProgress;

    this.api = axios.create({
      ...apiConfig,
      // Add a trailing slash
      baseURL: baseUrl.replace(/\/?$/, '/'),
    });
  }

  /**
   * Initializes an upload.
   *
   * @param file The file to upload.
   * @param fieldId The Django field identifier.
   */
  protected async initializeUpload(file: File, fieldId: string): Promise<MultipartInfo> {
    const response = await this.api.post('upload-initialize/', {
      field_id: fieldId,
      file_name: file.name,
      file_size: file.size,
    });
    return response.data;
  }

  /**
   * Uploads all the parts in a file directly to an object store in serial.
   *
   * @param file The file to upload.
   * @param parts The list of parts describing how to break up the file.
   */
  protected async uploadParts(file: File, parts: PartInfo[]): Promise<UploadedPart[]> {
    const uploadedParts: UploadedPart[] = [];
    let fileOffset = 0;
    for (const part of parts) {
      const chunk = file.slice(fileOffset, fileOffset + part.size);
      // eslint-disable-next-line no-await-in-loop
      const response = await axios.put(part.upload_url, chunk, {
        // eslint-disable-next-line @typescript-eslint/no-loop-func
        onUploadProgress: (e) => {
          this.onProgress({
            uploaded: fileOffset + e.loaded,
            total: file.size,
            state: S3FileFieldProgressState.Sending,
          });
        },
      });
      uploadedParts.push({
        part_number: part.part_number,
        size: part.size,
        etag: response.headers.etag,
      });
      fileOffset += part.size;
    }
    return uploadedParts;
  }

  /**
   * Completes an upload.
   *
   * The object will exist in the object store after completion.
   *
   * @param multipartInfo The information describing the multipart upload.
   * @param parts The parts that were uploaded.
   */
  protected async completeUpload(
    multipartInfo: MultipartInfo, parts: UploadedPart[],
  ): Promise<void> {
    const response = await this.api.post('upload-complete/', {
      upload_signature: multipartInfo.upload_signature,
      upload_id: multipartInfo.upload_id,
      parts,
    });
    const { complete_url: completeUrl, body } = response.data;

    // Send the CompleteMultipartUpload operation to S3
    await axios.post(completeUrl, body, {
      headers: {
        // By default, Axios sets "Content-Type: application/x-www-form-urlencoded" on POST
        // requests. This causes AWS's API to interpret the request body as additional parameters
        // to include in the signature validation, causing it to fail.
        // So, do not send this request with any Content-Type, as that is what's specified by the
        // CompleteMultipartUpload docs.
        'Content-Type': null,
      },
    });
  }

  /**
   * Finalizes an upload.
   *
   * This will only succeed if the object is already present in the object store.
   *
   * @param multipartInfo Signed information returned from /upload-complete/.
   */
  protected async finalize(multipartInfo: MultipartInfo): Promise<string> {
    const response = await this.api.post('finalize/', {
      upload_signature: multipartInfo.upload_signature,
    });
    return response.data.field_value;
  }

  /**
   * Uploads a file using multipart upload.
   *
   * @param file The file to upload.
   * @param fieldId The Django field identifier.
   */
  public async uploadFile(file: File, fieldId: string): Promise<S3FileFieldResult> {
    this.onProgress({ state: S3FileFieldProgressState.Initializing });
    const multipartInfo = await this.initializeUpload(file, fieldId);
    this.onProgress({ state: S3FileFieldProgressState.Sending, uploaded: 0, total: file.size });
    const parts = await this.uploadParts(file, multipartInfo.parts);
    this.onProgress({ state: S3FileFieldProgressState.Finalizing });
    await this.completeUpload(multipartInfo, parts);
    const value = await this.finalize(multipartInfo);
    this.onProgress({ state: S3FileFieldProgressState.Done });
    return {
      value,
      state: S3FileFieldResultState.Successful,
    };
  }
}
