"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.SignetClient = void 0;
const axios_1 = __importDefault(require("axios"));
const crypto = __importStar(require("crypto"));
const vscode = __importStar(require("vscode"));
// Lightweight client (extension-local) – avoids bundling full SDK
class SignetClient {
    constructor() {
        const cfg = vscode.workspace.getConfiguration('signet-lens');
        const baseURL = cfg.get('serverUrl') || 'http://localhost:8088';
        this.apiKey = cfg.get('apiKey') || undefined;
        this.http = axios_1.default.create({ baseURL, timeout: 10000 });
    }
    authHeaders() {
        return this.apiKey ? { 'X-SIGNET-API-Key': this.apiKey } : {};
    }
    async getReceiptChain(traceId) {
        try {
            const r = await this.http.get(`/v1/receipts/chain/${traceId}`, { headers: this.authHeaders() });
            return Array.isArray(r.data) ? r.data : null;
        }
        catch {
            return null;
        }
    }
    async exportChain(traceId) {
        try {
            const r = await this.http.get(`/v1/receipts/export/${traceId}`, { headers: this.authHeaders() });
            const bundle_cid = r.headers['x-odin-response-cid'] || r.headers['x-signet-response-cid'];
            return { ...r.data, signature_headers: { bundle_cid, signature: r.headers['x-odin-signature'] } };
        }
        catch {
            return null;
        }
    }
    async verifyChain(chain) {
        if (!Array.isArray(chain) || chain.length === 0)
            return { valid: false, error: 'Empty chain' };
        let prev = null;
        for (const rec of chain) {
            if (!rec.receipt_hash)
                return { valid: false, error: 'Missing receipt_hash' };
            const recomputed = this.hashReceiptLike(rec);
            if (recomputed !== rec.receipt_hash) {
                return { valid: false, error: `Hash mismatch at hop ${rec.hop}` };
            }
            if (rec.prev_receipt_hash !== (prev || null)) {
                if (prev !== null)
                    return { valid: false, error: `Broken prev hash link at hop ${rec.hop}` };
            }
            prev = rec.receipt_hash;
        }
        return { valid: true };
    }
    calculateCID(raw) {
        try {
            const obj = JSON.parse(raw);
            const canonical = this.canonicalize(obj);
            return crypto.createHash('sha256').update(canonical).digest('hex');
        }
        catch {
            return crypto.createHash('sha256').update(raw).digest('hex');
        }
    }
    // Simplified canonicalization: sort object keys recursively
    canonicalize(v) {
        if (v === null || typeof v !== 'object')
            return JSON.stringify(v);
        if (Array.isArray(v))
            return '[' + v.map(x => this.canonicalize(x)).join(',') + ']';
        const keys = Object.keys(v).sort();
        return '{' + keys.map(k => JSON.stringify(k) + ':' + this.canonicalize(v[k])).join(',') + '}';
    }
    hashReceiptLike(r) {
        // Exclude receipt_hash itself when recomputing – approximate logic
        const clone = { ...r };
        delete clone.receipt_hash;
        const canonical = this.canonicalize(clone);
        return crypto.createHash('sha256').update(canonical).digest('hex');
    }
}
exports.SignetClient = SignetClient;
//# sourceMappingURL=signetClient.js.map