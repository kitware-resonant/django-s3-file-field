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

@Component
export default class JoistUpload extends Vue {
  @Prop(String)
  private readonly accept: string | undefined;

  @Ref()
  private readonly fileInput!: HTMLInputElement;

  private files: IFileInfo[] = [];

  private submitting = false;

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

    results.forEach((r) => {
      if (r.state === 'successful') {
        form.append('ressource', r.value);
      }
    });

    await fetch('/new', {
      method: 'POST',
      body: form,
    });
  }
}
</script>
<template>
  <form @submit.prevent="submit">
    <label for="id_created">Created:</label>
    <input
      id="id_created"
      type="text"
      name="created"
      value="2019-11-21 15:33:54"
      required
    >
    <label for="id_creator">Creator:</label>
    <select
      id="id_creator"
      name="creator"
      required
    >
      <option value="">
        ---------
      </option>
      <option
        value="1"
        selected
      >
        admin
      </option>
    </select>
    <label for="id_resource">Resource:</label>
    <input
      id="id_resource"
      ref="fileInput"
      type="file"
      name="resource"
      required
    >
    <label for="id_r2">R2:</label>
    <input
      id="id_r2"
      type="file"
      name="r2"
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
