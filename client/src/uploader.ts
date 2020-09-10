import S3 from 'aws-sdk/clients/s3';

import {DjangoApi} from "./api";

export enum ProgressState {
  Initializing,
  Preparing,
  Uploading,
  Finishing,
  Done,
  Aborting,
  Aborted,
}

export interface Progress {
  readonly state: ProgressState;
  readonly percentage: number;
}

type ProgressCallback = (this: void, progress: Progress) => void;

interface PrepareResponse {
  s3Options: S3.Types.ClientConfiguration;
  bucketName: string;
  objectKey: string;
  fieldValue: string;
  fieldSignature: string;
}

interface FinalizeResponse {
  id?: string;
  name: string;
  signature?: string;
  value: string;
}

export class FileUploader {
  // The percent reserved for each of the prepare and finalize operations
  private static readonly OVERHEAD_PERCENT = 0.05;

  private readonly djangoApi: DjangoApi;
  private prepareResponse?: PrepareResponse;
  private s3Upload?: S3.ManagedUpload;
  private finalizeResponse?: FinalizeResponse;

  constructor(
      public readonly file: File,
      baseUrl?: string,
      private readonly onProgress?: ProgressCallback,
  ) {
    this.djangoApi = new DjangoApi(baseUrl);
    this.updateProgress(ProgressState.Initializing, 0);
  }

  private updateProgress(
      state: ProgressState,
      percentage: number,
  ): void {
    if (this.onProgress) {
      // TODO: which one?
      // Don't leak the "this" context out to the callback
      this.onProgress({state, percentage});
      this.onProgress.call(undefined, {
        state,
        percentage,
      });
    }
  }

  public async upload(): Promise<FinalizeResponse> {
    // Prepare upload
    this.updateProgress(ProgressState.Preparing, 0);
    try {
      this.prepareResponse = await this.djangoApi.fetchJson(`upload-prepare/`, {
        method: 'POST',
        body: JSON.stringify({
          filename: this.file.name,
        }),
      });
    } catch (e) {
      if (e.name === 'AbortError') {
        throw e;
      }
      throw new Error(`Error preparing the upload: ${e}`);
    }
    if(!this.prepareResponse){
      // This is just to keep TypeScript happy
      throw new Error();
    }

    // Do upload to S3
    this.updateProgress(ProgressState.Uploading, FileUploader.OVERHEAD_PERCENT);
    const s3 = new S3({
      ...this.prepareResponse.s3Options
    });
    // TODO: Content-Type
    this.s3Upload = s3.upload({
      Bucket: this.prepareResponse.bucketName,
      Key: this.prepareResponse.objectKey,
      Body: this.file,
    });

    this.s3Upload.on('httpUploadProgress', (evt): void => {
      const uploadFraction = evt.loaded / evt.total;
      // The scaled upload portion of the total progress
      const uploadProgressPercentage = (1 - (2* FileUploader.OVERHEAD_PERCENT)) * uploadFraction;
      const progressPercentage = FileUploader.OVERHEAD_PERCENT + uploadProgressPercentage;

      this.updateProgress(
        ProgressState.Uploading,
        progressPercentage
      );
    });

    try {
      await this.s3Upload.promise();
    } catch (e) {
      throw new Error(`Error uploading': ${e}`);
    }

    // Finalize upload
    this.updateProgress(ProgressState.Finishing, 1);
    try {
      this.finalizeResponse = await this.djangoApi.fetchJson(`upload-finalize/`, {
        method: 'POST',
        body: JSON.stringify({
          id: this.prepareResponse.objectKey,
          status: 'uploaded',
          fieldValue: this.prepareResponse.fieldValue,
          fieldSignature: this.prepareResponse.fieldSignature
        }),
      });
    } catch (e) {
      if (e.name === 'AbortError') {
        throw e;
      }
      throw new Error(`Error finishing the upload': ${e}`);
    }
    if(!this.finalizeResponse){
      // This is just to keep TypeScript happy
      throw new Error();
    }
    this.updateProgress(ProgressState.Done, 1);

    return {
      ...this.finalizeResponse,
      value: JSON.stringify({
        name: this.finalizeResponse.name,
        size: this.file.size,
        id: this.finalizeResponse.id,
        signature: this.finalizeResponse.signature
      }),
    };
  }

  public async abort(): Promise<void> {
    this.updateProgress(ProgressState.Aborting, 0);

    if (this.s3Upload) {
      try {
        this.s3Upload.abort();
      } catch (e) {
        throw new Error(`Error aborting the upload': ${e}`);
      }
    }

    this.djangoApi.abort();

    if (this.prepareResponse) {
      await this.djangoApi.fetchJson(`upload-finalize/`, {
        method: 'POST',
        body: JSON.stringify({
          id: this.prepareResponse.objectKey,
          status: 'aborted',
          fieldValue: this.prepareResponse.fieldValue,
          fieldSignature: this.prepareResponse.fieldSignature
        }),
      });
    }

    this.updateProgress(ProgressState.Aborted, 1);
  }
}
