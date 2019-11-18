const path = require('path');

module.exports = {
  entry: './js/index.ts',
  output: {
    path: path.resolve('./static/s3fileinput/'),
    filename: 's3fileinput.js',
    libraryExport: 'S3FileInput',
    libraryTarget: 'umd',
  },
  resolve: {
    // Add `.ts` and `.tsx` as a resolvable extension.
    extensions: ['.ts', '.tsx', '.js']
  },
  module: {
    rules: [
      // all files with a `.ts` or `.tsx` extension will be handled by `ts-loader`
      { test: /\.tsx?$/, loader: 'ts-loader' }
    ]
  }
}
