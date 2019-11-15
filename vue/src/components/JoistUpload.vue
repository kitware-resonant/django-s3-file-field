<template>
  <form @submit.prevent="submit">
    <input
      ref="fileInput"
      type="file"
      :accept="accept"
      @change="setFiles"
    >

    <div>
      <input
        type="button"
        value="Reset"
        @click="reset"
      >
      <input
        :disabled="!filesSelected"
        type="submit"
      >
    </div>

    <div v-if="submitting">
      Progress: {{ totalProgress * 100 }}%
    </div>
  </form>
</template>

<script lang="ts">
import S3 from 'aws-sdk/clients/s3';
import {
  Component, Emit, Prop, Ref, Vue,
} from 'vue-property-decorator';

import http from '@/http';

interface FileUploadUrl {
  accessKeyId: string;
  secretAccessKey: string;
  sessionToken: string;
  bucketName: string;
  objectKey: string;
}

@Component
export default class JoistUpload extends Vue {
  @Prop(String) private readonly accept: string | undefined;

  @Ref() private readonly fileInput!: HTMLInputElement;

  private files: File[] = [];

  private submitting: boolean = false;

  private currentUploadNum: number = 0;

  private fileProgress: number = 0;

  private get filesSelected() {
    return this.files.length > 0;
  }

  private get totalProgress() {
    // fileProgress is an additional fractional amount in [0, 1]
    return (this.currentUploadNum + this.fileProgress) / this.files.length;
  }

  private get currentUploadName() {
    const currentFile = this.files[this.currentUploadNum];
    return currentFile ? currentFile.name : '';
  }

  private setFiles() {
    this.files = Array.from(this.fileInput.files || []);
  }

  private async uploadFile(file: File) {
    // the percent reserved for upload initiate and finalize operations
    const OVERHEAD_PERCENT = 0.05;

    this.fileProgress = 0;
    const initUploadResp = await http.request({
      method: 'get',
      url: 'file-upload-url/',
      params: {
        name: file.name,
      },
    });
    const initUpload: FileUploadUrl = initUploadResp!.data;

    this.fileProgress = OVERHEAD_PERCENT / 2;

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
        // s3Progress only spans the total fileProgress range [0.1, 0.9)
        this.fileProgress = OVERHEAD_PERCENT / 2 + s3Progress * (1 - OVERHEAD_PERCENT);
      })
      .promise();

    await http.request({
      method: 'post',
      url: 'finalize-upload/',
      data: {
        name: initUpload.objectKey,
      },
    });
    this.fileProgress = 1;
  }

  public reset() {
    this.fileInput.value = '';
    this.submitting = false;
    this.currentUploadNum = 0;
    this.fileProgress = 0;
  }

  @Emit('complete')
  public async submit() {
    this.submitting = true;

    this.currentUploadNum = 0;
    for (const file of this.files) { // eslint-disable-line no-restricted-syntax
      await this.uploadFile(file); // eslint-disable-line no-await-in-loop

      this.fileProgress = 0;
      this.currentUploadNum += 1;
    }
  }
}
</script>

<style scoped>
  form input {
    margin-bottom: 10px;
    margin-right: 10px;
  }
</style>
