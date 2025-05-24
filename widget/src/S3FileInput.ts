import S3FileFieldClient, {} from 'django-s3-file-field';

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
      <div class="${cssClass('spinner')}"><div></div><div></div><div></div><div></div>
    </div>
  </div>`;
    this.input.parentElement?.replaceChild(this.node, this.input);
    // biome-ignore lint/style/noNonNullAssertion: the element is known to exist
    this.clearButton = this.node.querySelector<HTMLButtonElement>(`.${cssClass('clear')}`)!;
    // biome-ignore lint/style/noNonNullAssertion: the element is known to exist
    this.info = this.node.querySelector<HTMLElement>(`.${cssClass('info')}`)!;
    this.clearButton.insertAdjacentElement('beforebegin', this.input);
    // biome-ignore lint/style/noNonNullAssertion: the element is known to exist
    this.spinnerWrapper = this.node.querySelector<HTMLElement>(`.${cssClass('spinner-wrapper')}`)!;

    this.input.onchange = async (evt): Promise<void> => {
      evt.preventDefault();
      if (this.input.type === 'file') {
        await this.uploadFiles();
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
      this.node.classList.remove(cssClass('set'), cssClass('error'));
    };
  }

  private async uploadFile(file: File): Promise<string> {
    const startedEvent = new CustomEvent(EVENT_UPLOAD_STARTED, {
      detail: file,
    });
    this.input.dispatchEvent(startedEvent);

    const client = new S3FileFieldClient({
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
    });
    const fieldValue = client.uploadFile(file, this.fieldId);

    const completedEvent = new CustomEvent(EVENT_UPLOAD_COMPLETE, {
      detail: fieldValue,
    });
    this.input.dispatchEvent(completedEvent);

    return fieldValue;
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

    let fieldValue: string;
    try {
      fieldValue = await this.uploadFile(file);
    } catch (error) {
      this.node.classList.add(cssClass('set'), cssClass('error'));
      this.input.setCustomValidity('Error uploading file, see console for details.');
      this.input.type = 'hidden';
      this.info.innerText = 'Error uploading file, see console for details.';
      throw error;
    } finally {
      this.node.classList.remove(cssClass('uploading'));
    }
    this.node.classList.add(cssClass('set'));
    this.input.setCustomValidity(''); // no error
    this.input.type = 'hidden';
    this.input.value = fieldValue;
    this.info.innerText = file.name;
  }
}
