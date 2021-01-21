import S3FFClient, { UploadResult, UploadResultState } from 'django-s3-file-field';

export const EVENT_UPLOAD_STARTED = 's3UploadStarted';
export const EVENT_UPLOAD_COMPLETE = 's3UploadComplete';

function cssClass(clazz: string): string {
  return `s3fileinput-${clazz}`;
}

function i18n(text: string): string {
  return text;
}

export default class S3FileInput {
  private readonly node: HTMLElement;

  private readonly input: HTMLInputElement;

  private readonly info: HTMLElement;

  private readonly clearButton: HTMLButtonElement;

  private readonly spinnerWrapper: HTMLElement;

  private readonly baseUrl: string;

  private readonly fieldId: string;

  constructor(input: HTMLInputElement) {
    this.input = input;

    const baseUrl = this.input.dataset?.s3fileinput;
    if (!baseUrl) {
      throw new Error('Missing "data-s3fileinput" attribute on input element.');
    }
    this.baseUrl = baseUrl;

    const fieldId = this.input.dataset?.fieldId;
    if (!fieldId) {
      throw new Error('Missing "data-field-id" attribute on input element.');
    }
    this.fieldId = fieldId;

    this.node = input.ownerDocument.createElement('div');
    this.node.classList.add(cssClass('wrapper'));
    this.node.innerHTML = `<div class="${cssClass('inner')}">
    <div class="${cssClass('info')}"></div>
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
    this.clearButton = this.node.querySelector<HTMLButtonElement>(
      `.${cssClass('clear')}`,
    )!;
    this.info = this.node.querySelector<HTMLElement>(
      `.${cssClass('info')}`,
    )!;
    this.clearButton.insertAdjacentElement('beforebegin', this.input);
    this.spinnerWrapper = this.node.querySelector<HTMLElement>(
      `.${cssClass('spinner-wrapper')}`,
    )!;
    /* eslint-enable @typescript-eslint/no-non-null-assertion */

    this.input.onchange = (evt): void => {
      evt.preventDefault();
      if (this.input.type === 'file') {
        this.uploadFiles();
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
  }

  private async uploadFile(file: File): Promise<UploadResult> {
    const startedEvent = new CustomEvent(EVENT_UPLOAD_STARTED, {
      detail: file,
    });
    this.input.dispatchEvent(startedEvent);

    const result = await new S3FFClient({
      baseUrl: this.baseUrl,
      apiConfig: {
        // This will cause session and CSRF cookies to be sent for same-site requests.
        // Cross-site requests with the server-rendered widget are not supported.
        // If the server does not enable SessionAuthentication, requests will be unauthenticated,
        // but still allowed.
        xsrfCookieName: 'csrftoken',
        xsrfHeaderName: 'X-CSRFToken',
        // Explicitly disable this, to ensure that cross-site requests fail cleanly.
        withCredentials: false,
      },
    }).uploadFile(file, this.fieldId);
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
