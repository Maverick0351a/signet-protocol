/**
 * Signet Protocol - JavaScript/TypeScript Verification SDK
 * Verify receipts and chains in 5 lines of code.
 */

import { SignetReceipt, SignetChain, SignetExportBundle, VerificationResult, JWKS, JWK, SignetVerifierOptions } from './types';

export class SignetVerifier {
  private jwksCache: Map<string, { jwks: JWKS; timestamp: number }>;
  private jwksCacheTtl: number;

  constructor(options: SignetVerifierOptions = {}) {
    this.jwksCache = new Map();
    this.jwksCacheTtl = options.jwksCacheTtl || 3600000; // 1 hour in ms
  }

  /**
   * Verify a single Signet receipt
   */
  async verifyReceipt(
    receipt: SignetReceipt,
    previousReceipt?: SignetReceipt
  ): Promise<VerificationResult> {
    try {
      // 1. Verify receipt hash
      const computedHash = await this.computeReceiptHash(receipt);
      if (receipt.receipt_hash !== computedHash) {
        return { valid: false, reason: 'Invalid receipt hash' };
      }

      // 2. Verify chain linkage
      if (previousReceipt) {
        if (receipt.prev_receipt_hash !== previousReceipt.receipt_hash) {
          return { valid: false, reason: 'Broken chain linkage' };
        }
        if (receipt.hop !== previousReceipt.hop + 1) {
          return { valid: false, reason: 'Invalid hop sequence' };
        }
        if (receipt.trace_id !== previousReceipt.trace_id) {
          return { valid: false, reason: 'Trace ID mismatch' };
        }
      }

      // 3. Verify content identifier
      if (receipt.canon && receipt.cid) {
        const computedCid = await this.computeCid(receipt.canon);
        if (receipt.cid !== computedCid) {
          return { valid: false, reason: 'Invalid content identifier' };
        }
      }

      // 4. Verify timestamp format
      if (receipt.ts) {
        try {
          new Date(receipt.ts);
        } catch {
          return { valid: false, reason: 'Invalid timestamp format' };
        }
      }

      return { valid: true, reason: 'Valid receipt' };
    } catch (error) {
      return {
        valid: false,
        reason: `Verification error: ${error instanceof Error ? error.message : String(error)}`,
      };
    }
  }

  /**
   * Verify a complete receipt chain
   */
  async verifyChain(receipts: SignetChain): Promise<VerificationResult> {
    if (!receipts || receipts.length === 0) {
      return { valid: true, reason: 'Empty chain' };
    }

    // Verify genesis receipt
    if (receipts[0].prev_receipt_hash !== null) {
      return { valid: false, reason: 'Invalid genesis receipt' };
    }

    // Verify each receipt and linkage
    for (let i = 0; i < receipts.length; i++) {
      const receipt = receipts[i];
      const previousReceipt = i > 0 ? receipts[i - 1] : undefined;

      const result = await this.verifyReceipt(receipt, previousReceipt);
      if (!result.valid) {
        return { valid: false, reason: `Receipt ${i}: ${result.reason}` };
      }
    }

    return { valid: true, reason: 'Valid chain' };
  }

  /**
   * Verify a signed export bundle
   */
  async verifyExportBundle(
    bundle: SignetExportBundle,
    jwksUrl?: string
  ): Promise<VerificationResult> {
    try {
      // 1. Verify chain
      const chainResult = await this.verifyChain(bundle.chain || []);
      if (!chainResult.valid) {
        return { valid: false, reason: `Invalid chain: ${chainResult.reason}` };
      }

      // 2. Verify bundle CID
      const bundleContent = {
        trace_id: bundle.trace_id,
        chain: bundle.chain,
        exported_at: bundle.exported_at,
      };
      const computedCid = await this.computeCid(this.canonicalize(bundleContent));
      if (bundle.bundle_cid !== computedCid) {
        return { valid: false, reason: 'Invalid bundle CID' };
      }

      // 3. Verify signature (if JWKS available)
      if (bundle.signature && bundle.kid && jwksUrl) {
        const sigResult = await this.verifySignature(
          bundle.bundle_cid,
          bundle.signature,
          bundle.kid,
          jwksUrl
        );
        if (!sigResult.valid) {
          return { valid: false, reason: `Invalid signature: ${sigResult.reason}` };
        }
      }

      return { valid: true, reason: 'Valid export bundle' };
    } catch (error) {
      return {
        valid: false,
        reason: `Bundle verification error: ${error instanceof Error ? error.message : String(error)}`,
      };
    }
  }

  /**
   * Compute the hash of a receipt (excluding the hash field itself)
   */
  private async computeReceiptHash(receipt: SignetReceipt): Promise<string> {
    const receiptCopy = { ...receipt };
    delete (receiptCopy as any).receipt_hash;
    const canonical = this.canonicalize(receiptCopy);
    return 'sha256:' + (await this.sha256(canonical));
  }

  /**
   * Compute content identifier for canonicalized content
   */
  private async computeCid(content: string): Promise<string> {
    return 'sha256:' + (await this.sha256(content));
  }

  /**
   * JSON Canonicalization Scheme (JCS) implementation
   * Simplified version - for production use a full RFC 8785 implementation
   */
  private canonicalize(obj: any): string {
    return JSON.stringify(obj, Object.keys(obj).sort());
  }

  /**
   * Compute SHA-256 hash
   */
  private async sha256(message: string): Promise<string> {
    if (typeof crypto !== 'undefined' && crypto.subtle) {
      // Browser environment
      const msgBuffer = new TextEncoder().encode(message);
      const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
    } else {
      // Node.js environment
      try {
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const crypto = require('crypto');
        return crypto.createHash('sha256').update(message).digest('hex');
      } catch {
        throw new Error('SHA-256 not available. In Node.js, crypto module is required.');
      }
    }
  }

  /**
   * Verify Ed25519 signature using JWKS
   */
  private async verifySignature(
    message: string,
    signature: string,
    kid: string,
    jwksUrl: string
  ): Promise<VerificationResult> {
    try {
      // Fetch JWKS
      const jwks = await this.fetchJwks(jwksUrl);

      // Find key
      const key = jwks.keys?.find(
        (k) => k.kid === kid && k.kty === 'OKP' && k.crv === 'Ed25519'
      );

      if (!key) {
        return { valid: false, reason: `Key ${kid} not found in JWKS` };
      }

      // Verify signature (requires Web Crypto API or Node.js crypto)
      if (typeof crypto !== 'undefined' && crypto.subtle) {
        try {
          // Browser environment with Web Crypto API
          const publicKeyBytes = this.base64UrlDecode(key.x);
          const signatureBytes = this.base64Decode(signature);

          // Note: Ed25519 signature verification in browsers requires additional libraries
          // For now, we'll skip signature verification in browsers and recommend server-side verification
          return {
            valid: false,
            reason: 'Ed25519 signature verification not supported in browser environment. Use server-side verification.',
          };
        } catch (error) {
          return {
            valid: false,
            reason: `Signature verification failed: ${error instanceof Error ? error.message : String(error)}`,
          };
        }
      } else {
        // Node.js environment - would need additional crypto library
        return {
          valid: false,
          reason: 'Ed25519 verification requires Web Crypto API or additional library',
        };
      }
    } catch (error) {
      return {
        valid: false,
        reason: `JWKS verification error: ${error instanceof Error ? error.message : String(error)}`,
      };
    }
  }

  /**
   * Fetch JWKS with caching
   */
  private async fetchJwks(jwksUrl: string): Promise<JWKS> {
    const now = Date.now();

    if (this.jwksCache.has(jwksUrl)) {
      const cached = this.jwksCache.get(jwksUrl)!;
      if (now - cached.timestamp < this.jwksCacheTtl) {
        return cached.jwks;
      }
    }

    // Fetch fresh JWKS
    const fetchFn = this.getFetch();
    const response = await fetchFn(jwksUrl);
    if (!response.ok) {
      throw new Error(`Failed to fetch JWKS: ${response.status}`);
    }

    const jwks = await response.json();

    // Cache result
    this.jwksCache.set(jwksUrl, { jwks, timestamp: now });

    return jwks;
  }

  /**
   * Base64 URL decode
   */
  private base64UrlDecode(str: string): Uint8Array {
    // Add padding if needed
    str += '='.repeat((4 - (str.length % 4)) % 4);
    // Replace URL-safe characters
    str = str.replace(/-/g, '+').replace(/_/g, '/');
    // Decode
    return Uint8Array.from(atob(str), (c) => c.charCodeAt(0));
  }

  /**
   * Base64 decode
   */
  private base64Decode(str: string): Uint8Array {
    return Uint8Array.from(atob(str), (c) => c.charCodeAt(0));
  }

  private getFetch(): typeof fetch {
    if (typeof fetch !== 'undefined') {
      return fetch;
    }

    // Node.js environment - require node-fetch
    try {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const nodeFetch = require('node-fetch');
      return nodeFetch.default || nodeFetch;
    } catch {
      throw new Error(
        'fetch is not available. In Node.js, install node-fetch: npm install node-fetch'
      );
    }
  }
}

// Convenience functions for one-liner usage
export async function verifyReceipt(
  receipt: SignetReceipt,
  previousReceipt?: SignetReceipt
): Promise<VerificationResult> {
  const verifier = new SignetVerifier();
  return await verifier.verifyReceipt(receipt, previousReceipt);
}

export async function verifyChain(receipts: SignetChain): Promise<VerificationResult> {
  const verifier = new SignetVerifier();
  return await verifier.verifyChain(receipts);
}

export async function verifyExportBundle(
  bundle: SignetExportBundle,
  jwksUrl?: string
): Promise<VerificationResult> {
  const verifier = new SignetVerifier();
  return await verifier.verifyExportBundle(bundle, jwksUrl);
}

// Compute functions for external use
export async function computeCid(content: string): Promise<string> {
  const verifier = new SignetVerifier();
  return await (verifier as any).computeCid(content);
}

export function canonicalize(obj: any): string {
  return JSON.stringify(obj, Object.keys(obj).sort());
}
