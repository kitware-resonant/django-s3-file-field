const path = require('path');

module.exports = {
  entry: "./src/widget.ts",
  output: {
    path: path.resolve("../s3_file_field/static/s3_file_field/"),
    filename: "s3_file_field.js",
    libraryTarget: "umd"
  },
  resolve: {
    extensions: [".ts", ".tsx", ".js"]
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        loader: "ts-loader"
      },
      {
        test: /\.s[ac]ss$/i,
        use: ["style-loader", "css-loader", "sass-loader"]
      }
    ]
  }
};
