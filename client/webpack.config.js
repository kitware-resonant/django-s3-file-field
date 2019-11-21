const path = require('path');
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

module.exports = {
  entry: "./src/bundle.ts",
  output: {
    path: path.resolve("build"),
    filename: "joist.js",
    libraryExport: "Joist",
    libraryTarget: "umd"
  },
  resolve: {
    // Add `.ts` and `.tsx` as a resolvable extension.
    extensions: [".ts", ".tsx", ".js"]
  },
  module: {
    rules: [
      // all files with a `.ts` or `.tsx` extension will be handled by `ts-loader`
      {
        test: /\.tsx?$/,
        loader: "ts-loader",
        options: {
          configFile: "tsconfig.lib.json"
        }
      },
      {
        test: /\.s[ac]ss$/i,
        use: [
          { loader: MiniCssExtractPlugin.loader },
          "css-loader",
          "sass-loader"
        ]
      }
    ]
  },
  plugins: [
    new MiniCssExtractPlugin(),
  ],
};
