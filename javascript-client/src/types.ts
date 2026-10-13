export interface PresignedPart {
  // biome-ignore-start lint/style/useNamingConvention: API interface names
  part_number: number;
  size: number;
  url: string;
  // biome-ignore-end lint/style/useNamingConvention: API interface names
}

export interface InitiationResponse {
  // biome-ignore-start lint/style/useNamingConvention: API interface names
  upload_token: string;
  parts: PresignedPart[];
  // biome-ignore-end lint/style/useNamingConvention: API interface names
}

export interface CompletedPart {
  // biome-ignore-start lint/style/useNamingConvention: API interface names
  part_number: number;
  etag: string;
  // biome-ignore-end lint/style/useNamingConvention: API interface names
}

export interface CompletionResponse {
  url: string;
  body: string;
}

export interface FinalizationResponse {
  // biome-ignore-start lint/style/useNamingConvention: API interface names
  field_value: string;
  // biome-ignore-end lint/style/useNamingConvention: API interface names
}

export interface ValidationError {
  type: string;
  loc: (string | number)[];
  msg: string;
}

export interface ErrorResponse {
  detail: string | ValidationError[];
}
