import _, {MultipartInfo} from 'django-s3-file-field';
import S3FileInput, {EVENT_UPLOAD_COMPLETE, EVENT_UPLOAD_CLEARED} from './S3FileInput.js';

function parseUploadCompleteData (token: string): MultipartInfo {
  return JSON.parse(
    decodeURIComponent(
      window.atob(
        // Convert base64 to URL-safe base64 and parse it into bytes and then JSON
        token.split(':')[0].replace(/-/g, '+').replace(/_/g, '/')).split('').map((c) => {
          return `%${('00' + c.charCodeAt(0).toString(16)).slice(-2)}`;
        }
      ).join('')
    )
  );
}

export default class s3ImageFileInput extends S3FileInput {
  private readonly draggedBackgroundClass: string;

  private readonly container: HTMLInputElement;

  private readonly defaultImage: HTMLInputElement;

  private readonly initialContainer: HTMLInputElement;

  private readonly initialImage: HTMLImageElement;

  private readonly clearCheckbox: HTMLInputElement;

  constructor(input: HTMLInputElement) {
    super(input);

    this.container = this.input.closest(`.${this.imageCssClass("")}`);
    this.draggedBackgroundClass = this.container.dataset['draggedBackgroundClass'];
    this.defaultImage = this.container.querySelector(`.${this.imageCssClass("default")}`);
    this.initialContainer = this.container.querySelector(`.${this.imageCssClass("initial")}`);
    this.initialImage = this.initialContainer.querySelector("img");
    this.clearCheckbox = this.container.querySelector(`.${this.imageCssClass("clear-checkbox")}`);

    this.input.addEventListener(EVENT_UPLOAD_COMPLETE, (e: CustomEvent) => {
      e.detail.then((value) => {
        const domain = this.initialImage.dataset["s3image"],
          multipartInfoData: MultipartInfo = parseUploadCompleteData(value);
        this.initialImage.src = `https://${domain}/${multipartInfoData.object_key}`;
        this.container.classList.add(this.imageCssClass('set'));
        this.clearCheckbox.checked = false;
      });
    });

    this.input.addEventListener(EVENT_UPLOAD_CLEARED, (e) => {
      this.container.classList.remove(this.imageCssClass('set'));
      this.clearCheckbox.checked = true;
    });

    this.container.addEventListener("dragover", (e) => {
      e.preventDefault();
      this.container.classList.add(this.draggedBackgroundClass);
    }, false);

    this.container.addEventListener("dragenter", () => {
      this.container.classList.add(this.draggedBackgroundClass);
    });

    this.container.addEventListener("dragleave", () => {
      this.container.classList.remove(this.draggedBackgroundClass);
    });

    this.input.addEventListener("drop", (e) => {
      e.preventDefault();
      this.container.classList.remove(this.draggedBackgroundClass);
      this.input.files = e.dataTransfer.files;
      this.clearCheckbox.checked = false;
      this.input.dispatchEvent(new Event("change"));
    });

    this.container.addEventListener("drop", (e) => {
      e.preventDefault();
      this.container.classList.remove(this.draggedBackgroundClass);
      this.input.files = e.dataTransfer.files;
      this.clearCheckbox.checked = false;
      this.input.dispatchEvent(new Event("change"));
    });
  }

  private imageCssClass(clazz: string): string {
    return clazz ? `s3imageinput-${clazz}` : "s3imageinput";
  }
}
