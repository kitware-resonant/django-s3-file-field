import S3 from 'aws-sdk/clients/s3';

const baseUrl = '/joist';

async function uploadFile(file: File, onProgress: (p: number)=>void) {
  // the percent reserved for upload initiate and finalize operations
  const OVERHEAD_PERCENT = 0.05;

  onProgress(0);
  const initUpload = await fetch(`${baseUrl}/file-upload-url`,{
    method: 'GET',
    params: {
      name: file.name,
    },
  }).then((r) => r.json());

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

  const finalized = await fetch(`${baseUrl}/finalize-upload`, {
    method: 'POST',
    params: {
      name: initUpload.objectKey,
    },
  }).then((r) => r.json());

  onProgress(1);

  return finalized.name;
}

export function init(elem: HTMLInputElement) {
  console.log(elem);
}

(function (factory) {
  // in case the document is already rendered
  if (document.readyState != 'loading') {
    factory();
  } else {
    document.addEventListener('DOMContentLoaded', factory);
  }
})(function () {
  // auto init
  const inputs = Array.from(document.querySelectorAll<HTMLInputElement>('input[type=file][data-s3fileinput]'));
  inputs.forEach(init);
});
