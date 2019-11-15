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
      <div
        v-for="file in files"
        :key="file.file.name"
      >
        {{ file.file.name }}
        <progress :value="file.progress">
          {{ Math.round(file.progress * 100) }} %
        </progress>
      </div>
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

interface IFileInfo {
  file: File;
  progress: number;
}

@Component
export default class JoistUpload extends Vue {
  @Prop(String)
  private readonly accept: string | undefined;

  @Ref()
  private readonly fileInput!: HTMLInputElement;

  private files: IFileInfo[] = [];

  private submitting = false;

  private get filesSelected() {
    return this.files.length > 0;
  }

  private setFiles() {
    this.files = Array.from(this.fileInput.files || []).map(file => ({ file, progress: 0 }));
  }

  private static async uploadFile(file: File, onProgress: (progress: number) => void) {
    // the percent reserved for upload initiate and finalize operations
    const OVERHEAD_PERCENT = 0.05;

    onProgress(0);
    const initUploadResp = await http.request({
      method: 'get',
      url: 'joist/file-upload-url/',
      params: {
        name: file.name,
      },
    });
    const initUpload: FileUploadUrl = initUploadResp!.data;

    onProgress(OVERHEAD_PERCENT / 2);

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
        onProgress(OVERHEAD_PERCENT / 2 + s3Progress * (1 - OVERHEAD_PERCENT));
      })
      .promise();

    await http.request({
      method: 'post',
      url: 'joist/finalize-upload/',
      data: {
        name: initUpload.objectKey,
      },
    });

    onProgress(1);

    return initUpload.objectKey;
  }

  public reset() {
    this.fileInput.value = '';
    this.submitting = false;
  }

  @Emit('complete')
  public async submit() {
    this.submitting = true;

    const uploaded = this.files.map(file => JoistUpload.uploadFile(file.file, (p) => {
      file.progress = p; // eslint-disable-line no-param-reassign
    }));
    const names = await Promise.all(uploaded);

    await http.request({
      method: 'post',
      url: 'save-blob/',
      data: {
        names,
      },
    });
  }
}
</script>

<style scoped>
  form input {
    margin-bottom: 10px;
    margin-right: 10px;
  }
</style>
