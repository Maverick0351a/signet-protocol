/**
 * Signet Protocol - TypeScript Type Definitions
 */

export interface SignetReceipt {
  trace_id: string;
  hop: number;
  ts: string;
  cid: string;
  canon: string;
  algo: string;
  prev_receipt_hash: string | null;
  policy: {
    engine: string;
    allowed: boolean;
    reason: string;
    [key: string]: any;
  };
  tenant: string;
  receipt_hash: string;
  [key: string]: any;
}

export interface SignetChain extends Array<SignetReceipt> {}

export interface SignetExportBundle {
  trace_id: string;
  chain: SignetChain;
  exported_at: string;
  bundle_cid: string;
  signature?: string;
  kid?: string;
  [key: string]: any;
}

export interface VerificationResult {
  valid: boolean;
  reason: string;
}

export interface JWK {
  kty: string;
  crv: string;
  x: string;
  kid: string;
  use?: string;
  [key: string]: any;
}

export interface JWKS {
  keys: JWK[];
}

export interface SignetVerifierOptions {
  jwksCacheTtl?: number;
}

export interface SignetClientOptions {
  signetUrl: string;
  apiKey: string;
  forwardUrl?: string;
  tenant?: string;
  timeout?: number;
  autoVerify?: boolean;
}

export interface ExchangePayload {
  payload_type: string;
  target_type: string;
  trace_id: string;
  payload: {
    tool_calls: Array<{
      type: string;
      function: {
        name: string;
        arguments: string;
      };
    }>;
  };
  forward_url?: string;
}

export interface SignetResponse {
  success: boolean;
  traceId: string;
  normalized?: any;
  receipt?: SignetReceipt;
  forwarded?: any;
  error?: string;
  statusCode?: number;
}

export interface ExchangeOptions {
  apiKey: string;
  idem?: string;
  payloadType?: string;
  targetType?: string;
  payload: any;
  forwardUrl?: string;
  traceId?: string;
  autoVerify?: boolean;
}
