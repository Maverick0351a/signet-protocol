/**
 * Signet Protocol - JavaScript/TypeScript Client SDK
 * One-line "send + verify" for developers
 */

import { SignetReceipt, SignetResponse, ExchangeOptions } from './types';

export class SignetClient {
  private signetUrl: string;
  private apiKey: string;
  private forwardUrl?: string;
  private tenant: string;
  private timeout: number;
  private autoVerify: boolean;

  constructor(options: {
    signetUrl: string;
    apiKey: string;
    forwardUrl?: string;
    tenant?: string;
    timeout?: number;
    autoVerify?: boolean;
  }) {
    this.signetUrl = options.signetUrl.replace(/\/$/, '');
    this.apiKey = options.apiKey;
    this.forwardUrl = options.forwardUrl;
    this.tenant = options.tenant || 'client';
    this.timeout = options.timeout || 30000;
    this.autoVerify = options.autoVerify ?? true;
  }

  /**
   * Send data through Signet Protocol for verification
   */
  async exchange(options: Omit<ExchangeOptions, 'apiKey'>): Promise<SignetResponse> {
    try {
      // Generate IDs if not provided
      const traceId = options.traceId || `${this.tenant}-${this.generateUuid()}`;
      const idem = options.idem || `${traceId}-${this.generateUuid()}`;

      // Create payload
      const payload = this.createPayload({
        ...options,
        traceId,
      });

      // Make request
      const response = await this.makeRequest('/v1/exchange', {
        method: 'POST',
        headers: {
          'X-SIGNET-API-Key': this.apiKey,
          'X-SIGNET-Idempotency-Key': idem,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      // Parse response
      const result = await this.parseResponse(response, traceId);

      // Auto-verify receipt if enabled
      if (result.success && result.receipt && this.autoVerify) {
        const { verifyReceipt } = await import('./signet-verify');
        const { valid, reason } = await verifyReceipt(result.receipt);
        if (!valid) {
          return {
            ...result,
            success: false,
            error: `Receipt verification failed: ${reason}`,
          };
        }
      }

      return result;
    } catch (error) {
      return {
        success: false,
        traceId: options.traceId || 'unknown',
        error: `Request failed: ${error instanceof Error ? error.message : String(error)}`,
      };
    }
  }

  /**
   * Retrieve receipt chain for a trace
   */
  async getReceipts(traceId: string): Promise<SignetReceipt[] | null> {
    try {
      const response = await this.makeRequest(`/v1/receipts/chain/${traceId}`, {
        method: 'GET',
        headers: {
          'X-SIGNET-API-Key': this.apiKey,
        },
      });

      if (response.ok) {
        return await response.json();
      }
      return null;
    } catch {
      return null;
    }
  }

  /**
   * Export signed receipt bundle
   */
  async exportBundle(traceId: string): Promise<any | null> {
    try {
      const response = await this.makeRequest(`/v1/receipts/export/${traceId}`, {
        method: 'GET',
        headers: {
          'X-SIGNET-API-Key': this.apiKey,
        },
      });

      if (response.ok) {
        return await response.json();
      }
      return null;
    } catch {
      return null;
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.makeRequest('/healthz', {
        method: 'GET',
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  private createPayload(options: Omit<ExchangeOptions, 'apiKey'> & { traceId: string }): any {
    const argumentsJson = JSON.stringify(options.payload);

    return {
      payload_type: options.payloadType || 'openai.tooluse.invoice.v1',
      target_type: options.targetType || 'invoice.iso20022.v1',
      trace_id: options.traceId,
      payload: {
        tool_calls: [{
          type: 'function',
          function: {
            name: 'create_invoice',
            arguments: argumentsJson,
          },
        }],
      },
      forward_url: options.forwardUrl || this.forwardUrl,
    };
  }

  private async makeRequest(path: string, init: RequestInit): Promise<Response> {
    const url = `${this.signetUrl}${path}`;
    
    // Use fetch (browser) or node-fetch (Node.js)
    const fetchFn = this.getFetch();
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetchFn(url, {
        ...init,
        signal: controller.signal,
      });
      return response;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  private async parseResponse(response: Response, traceId: string): Promise<SignetResponse> {
    try {
      if (response.ok) {
        const data = await response.json();
        return {
          success: true,
          traceId: data.trace_id || traceId,
          normalized: data.normalized,
          receipt: data.receipt,
          forwarded: data.forwarded,
          statusCode: response.status,
        };
      } else {
        let errorMsg: string;
        try {
          const errorData = await response.json();
          errorMsg = errorData.detail || `HTTP ${response.status}`;
        } catch {
          errorMsg = `HTTP ${response.status}: ${response.statusText}`;
        }

        return {
          success: false,
          traceId,
          error: errorMsg,
          statusCode: response.status,
        };
      }
    } catch (error) {
      return {
        success: false,
        traceId,
        error: `Response parsing failed: ${error instanceof Error ? error.message : String(error)}`,
        statusCode: response.status,
      };
    }
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
      throw new Error('fetch is not available. In Node.js, install node-fetch: npm install node-fetch');
    }
  }

  private generateUuid(): string {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    
    // Fallback UUID v4 implementation
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
}

/**
 * One-liner exchange function
 */
export async function exchange(options: ExchangeOptions): Promise<SignetResponse> {
  const client = new SignetClient({
    signetUrl: process.env.SIGNET_URL || 'http://localhost:8088',
    apiKey: options.apiKey,
    forwardUrl: options.forwardUrl,
  });

  return client.exchange(options);
}

/**
 * Convenience function for invoice verification
 */
export async function verifyInvoice(
  apiKey: string,
  invoiceData: any,
  options?: {
    signetUrl?: string;
    forwardUrl?: string;
    autoVerify?: boolean;
  }
): Promise<SignetResponse> {
  return exchange({
    apiKey,
    payload: invoiceData,
    forwardUrl: options?.forwardUrl,
    autoVerify: options?.autoVerify,
  });
}

// Export types
export * from './types';
