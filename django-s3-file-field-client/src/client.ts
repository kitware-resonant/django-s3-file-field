import axios from 'axios';

export interface Progress {
  readonly percentage: number;
}

type ProgressCallback = (progress: Progress) => void;

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
// Return value from uploadFile()
export interface UploadResult {
  value: string;
  state: 'aborted' | 'successful' | 'error';
}

class Progressable {
  private overheadPercentage = 0.0;
  private mainPercentageSegments: number[] = [];
  // This value was picked arbitrarily
  private readonly overheadProportion = 0.20;

  constructor(
    private readonly onProgress?: ProgressCallback,
  ) {}

  private updateProgress(): void {
    const mainPercentage = this.mainPercentageSegments
      .reduce((total, value) => total + value, 0.0);
    const percentage = (this.overheadPercentage * this.overheadProportion) + (mainPercentage * (1 - this.overheadProportion));

    if (this.onProgress) {
      // Don't leak the "this" context out to the callback
      this.onProgress.call(undefined, {
        percentage,
      });
    }
  }

  protected updateOverheadProgress(percentage: number) {
    this.overheadPercentage = percentage;
    this.updateProgress();
  }

  protected initializeMainProgress(segments: number) {
    this.mainPercentageSegments = new Array(segments).fill(0);
  }

  protected updateMainProgress(segment: number, current: number, total: number) {
    // This weights each segment equally, which is not as accurate, but easier to initialize
    this.mainPercentageSegments[segment] = current / total;
    this.updateProgress();
  }
}

export default class S3FFClient extends Progressable{
  constructor(
    protected readonly baseUrl: string,
    onProgress?: ProgressCallback
  ) {
    super(onProgress)
  }

  /**
   * Initializes an upload.
   *
   * @param file The file to upload.
   * @param fieldId The Django field identifier.
   */
  protected async initializeUpload(file: File, fieldId: string): Promise<MultipartInfo> {
    const response = await axios.post(`${this.baseUrl}/upload-initialize/`, { 'field_id': fieldId, 'file_name': file.name, 'file_size': file.size });
    this.updateOverheadProgress(0.25);
    return response.data;
  }

  /**
   * Uploads a part directly to an object store.
   *
   * @param chunk The data to upload to this part.
   * @param part Details of this part.
   */
  protected async uploadPart(chunk: ArrayBuffer, part: PartInfo): Promise<UploadedPart> {
    const response = await axios.put(
      part.upload_url,
      chunk,
      {
        onUploadProgress: (progressEvent) => {
          this.updateMainProgress(progressEvent.loaded, progressEvent.total, part.part_number);
        },
      });
    // Ensure the progress is complete
    this.updateMainProgress(part.size, part.size, part.part_number);
    const etag = response.headers['etag'];
    return {
      part_number: part.part_number,
      size: part.size,
      etag,
    }
  }

  /**
   * Uploads all the parts in a file directly to an object store in parallel.
   *
   * @param file The file to upload.
   * @param parts The list of parts describing how to break up the file.
   */
  protected async uploadParts(file: File, parts: PartInfo[]): Promise<UploadedPart[]> {
    const buffer = await file.arrayBuffer();

    // indices track where in the buffer each part begins
    let index = 0;
    const indices: number[] = [];
    for (const part of parts) {
      indices.push(index);
      index += part.size;
    }

    this.initializeMainProgress(parts.length);
    // upload each part of the buffer in parallel using the calculated indices
    return await Promise.all(parts.map(async (part, i) => {
      const chunk = buffer.slice(indices[i], indices[i] + part.size);
      return await this.uploadPart(chunk, part);
    }));
  }

  /**
   * Completes an upload.
   *
   * The object will exist in the object store after completion.
   *
   * @param multipartInfo The information describing the multipart upload.
   * @param parts The parts that were uploaded.
   */
  protected async completeUpload(multipartInfo: MultipartInfo, parts: UploadedPart[]): Promise<void> {
    const response = await axios.post(`${this.baseUrl}/upload-complete/`, {
      upload_signature: multipartInfo.upload_signature,
      upload_id: multipartInfo.upload_id,
      parts: parts,
    });
    this.updateOverheadProgress(0.5);
    const { complete_url, body } = response.data;

    // Send the CompleteMultipartUpload operation to S3
    await axios.post(complete_url, body, {
      headers: {
        // By default, Axios sets "Content-Type: application/x-www-form-urlencoded" on POST
        // requests. This causes AWS's API to interpret the request body as additional parameters
        // to include in the signature validation, causing it to fail.
        // So, do not send this request with any Content-Type, as that is what's specified by the
        // CompleteMultipartUpload docs.
        'Content-Type': null,
      },
    });
    this.updateOverheadProgress(0.75);
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
    this.updateOverheadProgress(1.0);
    const { field_value } = response.data;
    return field_value;
  }

  /**
   * Uploads a file using multipart upload.
   *
   * @param file The file to upload.
   * @param fieldId The Django field identifier.
   */
  public async uploadFile(file: File, fieldId: string): Promise<UploadResult> {
    const multipartInfo = await this.initializeUpload(file, fieldId);
    const parts = await this.uploadParts(file, multipartInfo.parts);
    await this.completeUpload(multipartInfo, parts);
    const field_value = await this.finalize(multipartInfo);
    return {
      value: field_value,
      state: 'successful',
    }
  }
}
