<script lang="ts">
import {
  Component, Emit, Prop, Ref, Vue,
} from 'vue-property-decorator';
import uploadFile from 'joist';


interface IFileInfo {
  file: File;
  progress: number;
}

interface IFinalizeResponse {
  name: string;
}

declare const process: any;

interface IBlob {
  id: string;
  created: string;
  creator: number;
  resource: string;
}

@Component
export default class JoistUpload extends Vue {
  @Prop(String)
  private readonly accept: string | undefined;

  @Ref()
  private readonly fileInput!: HTMLInputElement;

  private files: IFileInfo[] = [];

  private submitting = false;

  private status = '';

  private blobs: IBlob[] = [];

  public reset() {
    this.fileInput.value = '';
    this.submitting = false;
  }

  @Emit('complete')
  public async submit(evt: Event) {
    const form = new FormData(evt.currentTarget as HTMLFormElement);
    this.submitting = true;
    this.files = form.getAll('resource').map(d => ({ file: d as File, progress: 0 }));

    form.delete('resource');

    const results = await Promise.all(this.files.map(f => uploadFile(f.file, {
      baseUrl: `${process.env.VUE_APP_API_ROOT}/joist`,
      onProgress({ percentage }) {
        f.progress = percentage; // eslint-disable-line no-param-reassign
      },
    })));

    try {
      const out = await fetch(`${process.env.VUE_APP_API_ROOT}/save-blob/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          names: results.map(r => r.id!),
        }),
      }).then(r => r.json());

      this.blobs = out;
      this.status = 'Saved';
    } catch {
      this.status = 'Failed';
    }
  }
}
</script>
<template>
  <form @submit.prevent="submit">
    <label for="id_resource">Resource:</label>
    <input
      id="id_resource"
      ref="fileInput"
      type="file"
      name="resource"
      required
    >
    <input
      type="submit"
      value="Create"
    >
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
    {{ status }}

    <div
      v-for="blob in blobs"
      :key="blob.id"
    >
      <a :href="blob.resource">{{ blob.id }}</a>
    </div>
  </form>
</template>

<style scoped>
  form {
    max-width: 25vw;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
  }
</style>
