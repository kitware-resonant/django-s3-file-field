import S3FFClient, { UploadResult, UploadResultState } from 'django-s3-file-field';

import { DEFAULT_BASE_URL, EVENT_UPLOAD_COMPLETE, EVENT_UPLOAD_STARTED } from './constants';

function cssClass(clazz: string): string {
  return `s3fileinput-${clazz}`;
}

export interface S3FileInputOptions {
  /**
   * @default /api/joist
   */
  baseUrl: string;
  /**
   * @default false
   */
  autoUpload: boolean;
}

function i18n(text: string): string {
  return text;
}

export default class S3FileInput {
  private readonly node: HTMLElement;

  private readonly input: HTMLInputElement;

  private readonly info: HTMLElement;

  private readonly uploadButton: HTMLButtonElement;

  private readonly clearButton: HTMLButtonElement;

  private readonly spinnerWrapper: HTMLElement;

  private readonly baseUrl: string;

  private readonly autoUpload: boolean;

  private readonly fieldId: string;

  constructor(input: HTMLInputElement, options: Partial<S3FileInputOptions> = {}) {
    this.input = input;

    this.baseUrl = options.baseUrl || this.input.dataset.s3fileinput || DEFAULT_BASE_URL;
    this.autoUpload = options.autoUpload != null
      ? options.autoUpload
      : this.input.dataset.autoUpload != null;
    this.fieldId = this.input.dataset?.fieldId || ''; // TODO this should error out

    this.node = input.ownerDocument.createElement('div');
    this.node.classList.add(cssClass('wrapper'));
    this.node.innerHTML = `<div class="${cssClass('inner')}">
    <div class="${cssClass('info')}"></div>
    <button type="button" class="${cssClass('upload')}" disabled>
      ${i18n('Upload to S3')}
    </button>
    <button type="button" class="${cssClass('clear')}" title="${i18n('Clear (file was already uploaded tho)')}">
      ${i18n('x')}
    </button>
    <div class="${cssClass('spinner-wrapper')}">
      <div class="${cssClass(
    'spinner',
  )}"><div></div><div></div><div></div><div></div>
    </div>
  </div>`;
    /* eslint-disable @typescript-eslint/no-non-null-assertion */
    this.input.parentElement!.replaceChild(this.node, this.input);
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    this.uploadButton = this.node.querySelector<HTMLButtonElement>(
      `.${cssClass('upload')}`,
    )!;
    this.clearButton = this.node.querySelector<HTMLButtonElement>(
      `.${cssClass('clear')}`,
    )!;
    this.info = this.node.querySelector<HTMLElement>(
      `.${cssClass('info')}`,
    )!;
    if (this.autoUpload) {
      this.uploadButton.classList.add(cssClass('autoupload'));
    }
    this.uploadButton.insertAdjacentElement('beforebegin', this.input);
    this.spinnerWrapper = this.node.querySelector<HTMLElement>(
      `.${cssClass('spinner-wrapper')}`,
    )!;
    /* eslint-enable @typescript-eslint/no-non-null-assertion */

    this.input.onchange = (evt): void => {
      evt.preventDefault();
      if (this.input.type === 'file') {
        const files = Array.from(this.input.files || []);
        this.handleFiles(files);
      } else if (this.input.value === '') {
        // already processed but user resetted it -> convert bak
        this.input.type = 'file';
        this.info.innerText = '';
        this.node.classList.remove(cssClass('set'));
      }
    };

    this.clearButton.onclick = (evt): void => {
      evt.preventDefault();
      evt.stopPropagation();
      this.input.type = 'file';
      this.input.value = '';
      this.info.innerText = '';
      this.node.classList.remove(cssClass('set'));
    };

    this.uploadButton.onclick = (evt): void => {
      evt.preventDefault();
      evt.stopPropagation();
      this.uploadFiles();
    };
  }

  private async handleFiles(files: File[]): Promise<void> {
    if (this.autoUpload) {
      await this.uploadFiles();
      return;
    }
    this.uploadButton.disabled = files.length === 0;

    this.input.setCustomValidity(
      files.length > 0 ? i18n('Press Upload Button to upload directly') : '',
    );
  }

  private async uploadFile(file: File): Promise<UploadResult> {
    const startedEvent = new CustomEvent(EVENT_UPLOAD_STARTED, {
      detail: file,
    });
    this.input.dispatchEvent(startedEvent);

    const result = await new S3FFClient(this.baseUrl).uploadFile(file, this.fieldId);
    const completedEvent = new CustomEvent(EVENT_UPLOAD_COMPLETE, {
      detail: result,
    });
    this.input.dispatchEvent(completedEvent);
    return result;
  }

  private async uploadFiles(): Promise<void> {
    const files = Array.from(this.input.files || []);
    if (files.length === 0) {
      return;
    }

    const bb = this.input.getBoundingClientRect();
    this.spinnerWrapper.style.width = `${bb.width}px`;
    this.spinnerWrapper.style.height = `${bb.height}px`;

    this.node.classList.add(cssClass('uploading'));
    this.uploadButton.disabled = true;
    this.input.setCustomValidity(i18n('Uploading files, wait till finished'));
    this.input.value = ''; // reset file selection

    const file = files[0];

    const result = await this.uploadFile(file);
    this.node.classList.remove(cssClass('uploading'));
    if (result.state === UploadResultState.Successful) {
      this.node.classList.add(cssClass('set'));
      this.input.setCustomValidity(''); // no error
      this.input.type = 'hidden';
      this.input.value = result.value;
      this.info.innerText = file.name;
    }
  }
}
