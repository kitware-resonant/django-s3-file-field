import axios from 'axios';

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

export enum UploadResultState {
  Aborted,
  Successful,
  Error,
}
// Return value from uploadFile()
export interface UploadResult {
  value: string;
  state: UploadResultState;
}

export enum ProgressState {
  Initializing,
  Sending,
  Finalizing,
  Done,
}

export interface ProgressEvent {
  readonly uploaded?: number;
  readonly total?: number;
  readonly state: ProgressState;
}

type ProgressCallback = (progress: ProgressEvent) => void;

export default class S3FFClient {
  constructor(
    protected readonly baseUrl: string,
    private readonly onProgress: ProgressCallback = () => { /* no-op */ },
  ) {
    // Strip any trailing slash
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  /**
   * Initializes an upload.
   *
   * @param file The file to upload.
   * @param fieldId The Django field identifier.
   */
  protected async initializeUpload(file: File, fieldId: string): Promise<MultipartInfo> {
    const response = await axios.post(`${this.baseUrl}/upload-initialize/`, {
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
            state: ProgressState.Sending,
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
    const response = await axios.post(`${this.baseUrl}/upload-complete/`, {
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
    const response = await axios.post(`${this.baseUrl}/finalize/`, {
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
  public async uploadFile(file: File, fieldId: string): Promise<UploadResult> {
    this.onProgress({ state: ProgressState.Initializing });
    const multipartInfo = await this.initializeUpload(file, fieldId);
    this.onProgress({ state: ProgressState.Sending, uploaded: 0, total: file.size });
    const parts = await this.uploadParts(file, multipartInfo.parts);
    this.onProgress({ state: ProgressState.Finalizing });
    await this.completeUpload(multipartInfo, parts);
    const value = await this.finalize(multipartInfo);
    this.onProgress({ state: ProgressState.Done });
    return {
      value,
      state: UploadResultState.Successful,
    };
  }
}
