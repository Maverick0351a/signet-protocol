import * as crypto from 'crypto';
import * as vscode from 'vscode';

// Minimal fetch type shims (Node 18+ provides global fetch at runtime)
// Avoid adding DOM lib to tsconfig to keep bundle small.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type FetchHeaders = any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type FetchResponse = any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type FetchRequestInit = any;

export interface VerifyResult { valid: boolean; error?: string }

// Lightweight client (extension-local) – avoids bundling full SDK
export class SignetClient {
  private apiKey: string | undefined;
  private baseURL: string;

  constructor() {
    const cfg = vscode.workspace.getConfiguration('signet-lens');
  const baseURL = cfg.get<string>('serverUrl') || 'http://localhost:8088';
    this.apiKey = cfg.get<string>('apiKey') || undefined;
  this.baseURL = baseURL.replace(/\/$/, '');
  }

  private authHeaders() {
    return this.apiKey ? { 'X-SIGNET-API-Key': this.apiKey } : {};
  }

  async getReceiptChain(traceId: string): Promise<any[] | null> {
    try {
      const res = await this.fetchJson(`/v1/receipts/chain/${traceId}`);
      return Array.isArray(res) ? res : null;
    } catch { return null; }
  }

  async exportChain(traceId: string): Promise<any | null> {
    try {
      const resp = await this.rawFetch(`/v1/receipts/export/${traceId}`);
      const data = await resp.json().catch(() => null);
      const headers: Record<string,string> = {};
      try {
        const iter = resp.headers && typeof resp.headers.forEach === 'function'
          ? (resp.headers as FetchHeaders).forEach((v: string, k: string) => { headers[k.toLowerCase()] = v; })
          : null;
        if (!iter && resp.headers && resp.headers.entries) {
          for (const [k, v] of resp.headers.entries()) { headers[String(k).toLowerCase()] = String(v); }
        }
      } catch { /* ignore header extraction errors */ }
      const bundle_cid = headers['x-odin-response-cid'] || headers['x-signet-response-cid'];
      return { ...data, signature_headers: { bundle_cid, signature: headers['x-odin-signature'] } };
    } catch { return null; }
  }

  async verifyChain(chain: any[]): Promise<VerifyResult> {
    if (!Array.isArray(chain) || chain.length === 0) return { valid: false, error: 'Empty chain' };
    let prev: string | null = null;
    for (const rec of chain) {
      if (!rec.receipt_hash) return { valid: false, error: 'Missing receipt_hash' };
      const recomputed = this.hashReceiptLike(rec);
      if (recomputed !== rec.receipt_hash) {
        return { valid: false, error: `Hash mismatch at hop ${rec.hop}` };
      }
      if (rec.prev_receipt_hash !== (prev || null)) {
        if (prev !== null) return { valid: false, error: `Broken prev hash link at hop ${rec.hop}` };
      }
      prev = rec.receipt_hash;
    }
    return { valid: true };
  }

  calculateCID(raw: string): string {
    try {
      const obj = JSON.parse(raw);
      const canonical = this.canonicalize(obj);
      return crypto.createHash('sha256').update(canonical).digest('hex');
    } catch {
      return crypto.createHash('sha256').update(raw).digest('hex');
    }
  }

  // Simplified canonicalization: sort object keys recursively
  private canonicalize(v: any): string {
    if (v === null || typeof v !== 'object') return JSON.stringify(v);
    if (Array.isArray(v)) return '[' + v.map(x => this.canonicalize(x)).join(',') + ']';
    const keys = Object.keys(v).sort();
    return '{' + keys.map(k => JSON.stringify(k) + ':' + this.canonicalize(v[k])).join(',') + '}';
  }

  private hashReceiptLike(r: any): string {
    // Exclude receipt_hash itself when recomputing – approximate logic
    const clone: any = { ...r };
    delete clone.receipt_hash;
    const canonical = this.canonicalize(clone);
    return crypto.createHash('sha256').update(canonical).digest('hex');
  }

  private async fetchJson(path: string, init?: FetchRequestInit, timeoutMs = 10_000): Promise<any> {
    const resp = await this.rawFetch(path, init, timeoutMs);
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    return resp.json();
  }

  private async rawFetch(path: string, init?: FetchRequestInit, timeoutMs = 10_000): Promise<FetchResponse> {
    const controller = new AbortController();
    const to = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const headers = { ...(init?.headers || {}), ...this.authHeaders() } as any;
  const f: any = (globalThis as any).fetch;
  if (!f) throw new Error('Global fetch not available in this Node version.');
  return await f(this.baseURL + path, { ...(init||{}), headers, signal: controller.signal });
    } finally { clearTimeout(to); }
  }
}
