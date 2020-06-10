import {DEFAULT_BASE_URL, fetchOptions} from "./constants";

export class DjangoApi {
  private readonly abortController: AbortController;

  constructor(
      private readonly baseUrl: string = DEFAULT_BASE_URL,
  ) {
    this.abortController = new AbortController();
  }

  public abort(): void {
    this.abortController.abort();
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  public async fetchJson(path: string, init?: RequestInit): Promise<any> {
    const resp = await fetch(`${this.baseUrl}/${path}`, {
      ...fetchOptions(),
      signal: this.abortController.signal,
      ...init,
    });
    if(!resp.ok) {
      const text = await resp.text();
      throw new Error(`Server returned ${resp.status} error: ${text}`);
    }
    return resp.json();
  }
}
