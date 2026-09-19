// biome-ignore-all lint/suspicious/noUnnecessaryConditions: reactive properties are externally assigned by Lit, invisibly to type inference
import { css, html, LitElement, nothing, type TemplateResult } from 'lit';
import { customElement, property, query, state } from 'lit/decorators.js';
import prettyBytes from 'pretty-bytes';
import { deriveFileState, type FileState, formValueFor, hasExistingFile } from './state.js';
import { uploadFile } from './upload.js';

/**
 * The state which determines the submission, as changed by the user.
 *
 * This is restored on form reset, and by the browser (as on navigating back to the page).
 */
interface RestorableState {
  value: string;
  cleared: boolean;
  uploadedFileName: string;
}

/** The final component of a (slash-delimited) file name, for display. */
function basename(fileName: string): string {
  return fileName.split('/').pop() ?? '';
}

/**
 * A form-associated custom element, uploading a file directly to S3 for an S3FileField.
 *
 * The API is expressed as properties, which may also be set as HTML attributes, so the element
 * can be server-rendered by Django or driven by a frontend framework. Form submission is
 * determined by the state: after an upload, "value" is submitted; when "cleared", an empty string
 * is submitted; otherwise, nothing is submitted, which keeps any existing file.
 */
@customElement('s3-file-input')
export class S3FileInputElement extends LitElement {
  // Participate in form submission directly, via ElementInternals
  static readonly formAssociated = true;

  static override readonly shadowRootOptions = {
    ...LitElement.shadowRootOptions,
    delegatesFocus: true,
  };

  static override readonly styles = css`
    :host {
      /* Custom elements are inline by default, which doesn't give a border a proper box; an
         inline-level flex box keeps the element in flow beside a form label, like a native file
         input */
      display: inline-flex;
      flex-direction: column;
      box-sizing: border-box;
      max-width: 100%;
      padding: 0.5em 0.75em;
      border: 1px solid var(--s3-file-input-border-color, currentColor);
      border-radius: 0.25em;
    }

    :host(:disabled) {
      /* The system color for disabled text, which the border follows via currentColor; this
         matches whether disabling is by the element's own attribute or an ancestor fieldset */
      color: GrayText;
    }

    :host(:disabled) a {
      /* The file remains viewable, so keep the system link color, but muted like the rest */
      color: LinkText;
      opacity: 0.4;
    }

    .status {
      /* Break an unbroken file name or link only as a last resort, rather than widening the box */
      overflow-wrap: anywhere;
    }

    .status:not(:empty) + .controls {
      /* The status is always present (as a live region), but only takes space when populated */
      margin-top: 0.375em;
    }

    .file-name {
      font-family: monospace;
    }

    .controls {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 0.5em;
    }

    .picker {
      /* The native picker has a wide intrinsic size; let it shrink in narrow containers */
      max-width: 100%;
    }

    .action {
      min-width: 4em;
    }
  `;

  /** The base URL of the upload API. */
  @property({ attribute: 'base-url' })
  accessor baseUrl = '';

  /** The identifier of the S3FileField to upload to. */
  @property({ attribute: 'field-id' })
  accessor fieldId = '';

  /** The maximum file size. */
  @property({ attribute: 'max-size', type: Number })
  accessor maxSize: number | undefined;

  /**
   * A pending signed FieldValue, server-rendered (on form redisplay) or set after an upload.
   *
   * Along with "cleared", this determines what is submitted; "fileName" and "fileUrl"
   * describe the represented file, for display.
   */
  @property()
  accessor value = '';

  /**
   * Whether the existing file is to be cleared.
   *
   * This may be server-rendered (on form redisplay), in which case "fileName" and "fileUrl"
   * are absent, or set by the user.
   */
  @property({ type: Boolean })
  accessor cleared = false;

  /**
   * Whether the field is disabled, so no controls are rendered.
   *
   * This reflects to the "disabled" attribute, which the browser honors for form submission.
   * A disabled ancestor fieldset also disables the field, but without setting this (see
   * "formDisabled").
   */
  @property({ type: Boolean, reflect: true })
  accessor disabled = false;

  /**
   * Whether a file is required, so the element is invalid without one.
   *
   * Django omits this when an existing file already satisfies it.
   */
  @property({ type: Boolean })
  accessor required = false;

  /**
   * The full name of the represented file; best-effort, display-only.
   *
   * This is the existing file's name, or on a redisplay of a pending upload, that upload's.
   */
  @property({ attribute: 'file-name' })
  accessor fileName = '';

  /** A download URL for the represented file; best-effort, display-only, and never for a pending upload. */
  @property({ attribute: 'file-url' })
  accessor fileUrl = '';

  /**
   * Whether the browser considers the field disabled, for any reason (including an ancestor
   * fieldset), as reported by "formDisabledCallback".
   *
   * This is deliberately kept apart from "disabled": reflecting it there would pin a "disabled"
   * attribute onto the element, which would then outlast the fieldset's own disabling.
   */
  @state()
  accessor formDisabled = false;

  @state()
  accessor uploading = false;

  /** The local name of an uploaded file; empty for a server-rendered pending value. */
  @state()
  accessor uploadedFileName = '';

  @state()
  accessor errorMessage = '';

  /** The file picker, which is only rendered when no file is represented; assigned by the decorator. */
  @query('#picker')
  accessor picker!: HTMLInputElement | null;

  /** The first control (rather than a link in the status), to receive restored focus. */
  @query('.controls :is(input, button):not(:disabled)')
  accessor firstControl!: HTMLElement | null;

  /** The status line, which is always rendered; assigned by the decorator. */
  @query('.status')
  accessor status!: HTMLElement | null;

  private readonly internals = this.attachInternals();

  /** The server-rendered state, captured on connection, to which a form reset returns. */
  private initial: RestorableState = { value: '', cleared: false, uploadedFileName: '' };

  /** Whether an existing (already saved) file is represented, kept or cleared. */
  private hasExistingFile = false;

  /** The associated form, whose submission is guarded while uploading. */
  private form: HTMLFormElement | null = null;

  /** Whether focus was within the element before an update, and is to be restored after it. */
  private restoreFocus = false;

  constructor() {
    super();
    // The host is what the form's label names, so expose it as a named group of its controls
    this.internals.role = 'group';
  }

  override connectedCallback(): void {
    super.connectedCallback();
    if (!this.hasUpdated) {
      // Capture the state as server-rendered, before the user can change it; a later
      // reconnection (as when the element is moved) must not recapture it
      this.initial = this.restorableState;
      this.hasExistingFile = hasExistingFile({ ...this.initial, fileName: this.fileName ?? '' });
    }
  }

  override willUpdate(): void {
    this.restoreFocus ||= this.matches(':focus-within');
  }

  override updated(): void {
    // The form value and validity derive from several properties, so they are synced after every
    // update, rather than in setters
    const fileState = this.fileState;
    this.internals.setFormValue(formValueFor(fileState), JSON.stringify(this.restorableState));
    this.syncValidity(fileState);
    this.syncFocus();
  }

  private syncValidity(fileState: FileState): void {
    // The browser shows a validity message only on a focusable anchor
    if (this.uploading) {
      // The picker is disabled while uploading, so the status (which is focusable by script for
      // this alone) anchors the message instead
      const anchor = this.status ?? undefined;
      this.internals.setValidity({ customError: true }, 'Upload in progress.', anchor);
    } else if (this.required && (fileState.kind === 'none' || fileState.kind === 'cleared')) {
      const anchor = this.picker ?? undefined;
      this.internals.setValidity({ valueMissing: true }, 'Please select a file.', anchor);
    } else {
      this.internals.setValidity({});
    }
  }

  /**
   * Restore focus to the first control, if an update removed the focused control.
   *
   * As when an upload replaces the picker with "Clear"; focus would otherwise drop to the
   * document.
   */
  private syncFocus(): void {
    if (this.restoreFocus && this.focusDropped) {
      // If there is no control (as while uploading, when the picker is disabled), this remains
      // to be restored by a later update
      this.firstControl?.focus();
    }
    // Focus on a disabled control (as the picker, while uploading) doesn't count, as the browser
    // is about to drop it
    this.restoreFocus &&= !this.renderRoot.querySelector(':focus:not(:disabled)');
  }

  formAssociatedCallback(form: HTMLFormElement | null): void {
    this.form?.removeEventListener('submit', this.handleFormSubmit);
    this.form = form;
    this.form?.addEventListener('submit', this.handleFormSubmit);
  }

  async formDisabledCallback(disabled: boolean): Promise<void> {
    // When this is caused by reflecting "disabled" to the attribute, it fires within an update,
    // after rendering, where a property change would be lost; so apply it after the update
    await this.updateComplete;
    this.formDisabled = disabled;
  }

  formStateRestoreCallback(formState: File | string | FormData | null, mode: string): void {
    // Only the state given to "setFormValue" is restored; autocompletion is meaningless for a file
    if (mode !== 'restore' || typeof formState !== 'string') {
      return;
    }
    this.restorableState = JSON.parse(formState) as RestorableState;
  }

  formResetCallback(): void {
    if (this.uploading) {
      // The upload would otherwise land after the reset, resurrecting a value the user believed
      // to be discarded; instead, it is kept, and may be cleared once it completes
      return;
    }
    this.resetPicker();
    this.restorableState = this.initial;
    this.errorMessage = '';
  }

  private get restorableState(): RestorableState {
    // The string properties may be set to null or undefined (e.g. by removing an attribute, or
    // by a framework binding), which is equivalent to empty
    return {
      value: this.value ?? '',
      cleared: this.cleared,
      uploadedFileName: this.uploadedFileName,
    };
  }

  private set restorableState(restorableState: RestorableState) {
    this.value = restorableState.value;
    this.cleared = restorableState.cleared;
    this.uploadedFileName = restorableState.uploadedFileName;
  }

  /** Whether the field is disabled, by its own property or by the browser. */
  private get isDisabled(): boolean {
    return this.disabled || this.formDisabled;
  }

  /** Whether nothing is focused, in the element's own tree; as after a focused node is removed. */
  private get focusDropped(): boolean {
    const active = (this.getRootNode() as Document | ShadowRoot).activeElement;
    return active === null || active === document.body;
  }

  private get fileState(): FileState {
    return deriveFileState({
      ...this.restorableState,
      hasExistingFile: this.hasExistingFile,
      fileName: this.fileName ?? '',
      fileUrl: this.fileUrl ?? '',
    });
  }

  override render() {
    const fileState = this.fileState;
    // The status is always present, so its changes are announced
    return html`
      <div class="status" role="status" tabindex="-1">${this.renderStatus(fileState)}</div>
      ${this.isDisabled ? null : this.renderControls(fileState)}
    `;
  }

  private renderStatus(fileState: FileState): string | TemplateResult | null {
    if (this.errorMessage) {
      return this.errorMessage;
    }
    if (this.uploading) {
      return 'Uploading…';
    }
    switch (fileState.kind) {
      case 'pending': {
        const name = basename(fileState.fileName) || '(unknown file)';
        return html`Uploaded:
          <span class="file-name" title=${fileState.fileName || nothing}>${name}</span>`;
      }
      case 'cleared':
        return 'The existing file will be discarded.';
      case 'kept': {
        if (!fileState.fileName) {
          // The info was omitted by the server, after a prior clear was undone
          return 'The existing file will be kept.';
        }
        const name = basename(fileState.fileName);
        const link = fileState.fileUrl
          ? html`<a href=${fileState.fileUrl} title=${fileState.fileName}>${name}</a>`
          : html`<span title=${fileState.fileName}>${name}</span>`;
        return html`Current: ${link}`;
      }
      default:
        // Without controls, there is nothing to indicate the absence of a file
        return this.isDisabled ? 'No file.' : null;
    }
  }

  private renderControls(fileState: FileState): TemplateResult {
    const picker = html`<input id="picker" class="picker" type="file" @change=${this.handlePickerChange} ?disabled=${this.uploading} />`;
    const clear = html`<button type="button" class="action" @click=${this.handleClear}>Clear</button>`;
    const keep = html`<button type="button" class="action" @click=${this.handleKeep}>Keep</button>`;
    switch (fileState.kind) {
      case 'none':
        return html`<div class="controls">${picker}</div>`;
      case 'cleared':
        return html`<div class="controls">${picker}${this.uploading ? null : keep}</div>`;
      default:
        // A pending or kept file can be cleared
        return html`<div class="controls">${clear}</div>`;
    }
  }

  private async handlePickerChange(): Promise<void> {
    const file = this.picker?.files?.[0];
    if (file === undefined) {
      return;
    }

    // The server enforces this too, but rejecting here avoids a needless attempt; a garbage
    // (NaN) or negative limit is ignored, leaving it to the server
    const maxSize = this.maxSize ?? Number.POSITIVE_INFINITY;
    if (maxSize >= 0 && file.size > maxSize) {
      this.resetPicker();
      this.errorMessage =
        `File is too large (${prettyBytes(file.size, { binary: true })}), ` +
        `maximum is ${prettyBytes(maxSize, { binary: true })}.`;
      return;
    }

    await this.upload(file);
  }

  private handleClear(): void {
    this.errorMessage = '';
    if (this.fileState.kind === 'pending') {
      // Discard the pending upload, reverting to the existing file, if any. On a redisplay, the
      // server renders only the pending file's info, so an existing file then goes unmentioned,
      // although it is kept.
      // TODO: Render the existing file's info alongside a pending value; currently,
      // "S3FormFileField.bound_data" returns only the pending data.
      this.value = '';
      this.uploadedFileName = '';
    } else {
      // Clear the kept file
      this.cleared = true;
    }
  }

  private handleKeep(): void {
    this.cleared = false;
  }

  private readonly handleFormSubmit = (event: SubmitEvent): void => {
    // The element's validity blocks submission of most forms, but a "novalidate" form (as in
    // the Django admin) ignores validity, so block that here too
    if (this.uploading) {
      event.preventDefault();
      this.internals.reportValidity();
    }
  };

  private async upload(file: File): Promise<void> {
    this.uploading = true;
    this.errorMessage = '';

    let fieldValue: string;
    try {
      fieldValue = await uploadFile(this.baseUrl, this.fieldId, file);
    } catch {
      this.resetPicker();
      this.errorMessage = 'Error uploading file.';
      return;
    } finally {
      this.uploading = false;
    }

    this.value = fieldValue;
    this.uploadedFileName = file.name;
    this.cleared = false;
  }

  /**
   * Discard any selected file, if the picker is present.
   *
   * This allows the same file to be reselected ("change" fires only on a change), and avoids
   * showing a rejected file as selected.
   */
  private resetPicker(): void {
    if (this.picker) {
      this.picker.value = '';
    }
  }
}

declare global {
  interface HTMLElementTagNameMap {
    's3-file-input': S3FileInputElement;
  }
}
