import "./style.scss";
import S3FileInput from "./S3FileInput";

/**
 * @internal
 */
export function autoInit(): void {
  // auto init
  const wrappers = Array.from(
    document.querySelectorAll<HTMLInputElement>("input[data-s3fileinput]")
  );
  wrappers.forEach(w => new S3FileInput(w));
}

if (document.readyState != "loading") {
  autoInit();
} else {
  document.addEventListener("DOMContentLoaded", autoInit);
}
