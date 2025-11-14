import './style.scss';
import S3FileInput from './S3FileInput.js';

function getAllUninitializedFileInputs(): HTMLInputElement[] {
  // Find all uninitialized s3 file inputs in the document.
  const selector = 'input[data-s3fileinput]:not([data-s3fileinput-initialized])';
  return (
    Array.from(document.querySelectorAll(selector))
      .filter((node) => node instanceof HTMLInputElement)
      // Exclude Django formset template fields
      .filter((el) => el?.name?.indexOf('__prefix__') === -1)
  );
}

function attachToFileInputs(): void {
  // Only attach once per input. Mark as initialized BEFORE constructing to avoid
  // mutation-observer feedback loops when the constructor modifies the DOM.
  const uninitializedFileInputs = getAllUninitializedFileInputs();
  for (const element of uninitializedFileInputs) {
    element.setAttribute('data-s3fileinput-initialized', 'true');
    new S3FileInput(element);
  }
}

if (document.readyState !== 'loading') {
  attachToFileInputs();
} else {
  document.addEventListener('DOMContentLoaded', () => {
    // Initial attach when DOM is ready
    attachToFileInputs();
    const observer = new MutationObserver((mutationList) => {
      // If nodes were added, check if there are any uninitialized inputs in the document.
      if (mutationList.some((m) => m.type === 'childList' && m.addedNodes.length > 0)) {
        const hasUninitialized = getAllUninitializedFileInputs().length > 0;
        if (hasUninitialized) {
          attachToFileInputs();
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  });
}
