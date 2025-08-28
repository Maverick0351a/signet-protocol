import axios, { AxiosInstance } from 'axios';
import * as crypto from 'crypto';
import * as vscode from 'vscode';

export interface VerifyResult { valid: boolean; error?: string }

// Lightweight client (extension-local) – avoids bundling full SDK
export class SignetClient {
  private http: AxiosInstance;
  private apiKey: string | undefined;

  constructor() {
    const cfg = vscode.workspace.getConfiguration('signet-lens');
    const baseURL = cfg.get<string>('serverUrl') || 'http://localhost:8088';
    this.apiKey = cfg.get<string>('apiKey') || undefined;
    this.http = axios.create({ baseURL, timeout: 10_000 });
  }

  private authHeaders() {
    return this.apiKey ? { 'X-SIGNET-API-Key': this.apiKey } : {};
  }

  async getReceiptChain(traceId: string): Promise<any[] | null> {
    try {
      const r = await this.http.get(`/v1/receipts/chain/${traceId}`, { headers: this.authHeaders() });
      return Array.isArray(r.data) ? r.data : null;
    } catch { return null; }
  }

  async exportChain(traceId: string): Promise<any | null> {
    try {
      const r = await this.http.get(`/v1/receipts/export/${traceId}`, { headers: this.authHeaders() });
      const bundle_cid = r.headers['x-odin-response-cid'] || r.headers['x-signet-response-cid'];
      return { ...r.data, signature_headers: { bundle_cid, signature: r.headers['x-odin-signature'] } };
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
}
