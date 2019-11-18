const path = require('path');

module.exports = {
  entry: './js/index.js',
  output: {
    path: path.resolve('./static/s3fileinput/'),
    filename: 's3fileinput.js',
    libraryExport: 'S3FileInput',
    libraryTarget: 'umd',
  },
}
