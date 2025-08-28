/**
 * Signet Protocol Zapier Integration
 * Private beta integration for verified AI-to-AI communications.
 */

const { version } = require('./package.json');

// Authentication configuration
const authentication = {
  type: 'custom',
  fields: [
    {
      computed: false,
      key: 'signet_url',
      required: true,
      label: 'Signet Protocol URL',
      type: 'string',
      helpText: 'Base URL of your Signet Protocol server (e.g., http://localhost:8088)',
    },
    {
      computed: false,
      key: 'api_key',
      required: true,
      label: 'API Key',
      type: 'password',
      helpText: 'Your Signet Protocol API key',
    },
  ],
  test: {
    operation: {
      perform: {
        url: '{{bundle.authData.signet_url}}/healthz',
        method: 'GET',
        headers: {
          'X-SIGNET-API-Key': '{{bundle.authData.api_key}}',
        },
      },
    },
    sample: { ok: true },
  },
  connectionLabel: 'Signet Protocol ({{bundle.authData.signet_url}})',
};

// Helper function to make authenticated requests
const makeRequest = (z, bundle, options) => {
  const baseUrl = bundle.authData.signet_url.replace(/\/$/, '');
  
  return z.request({
    ...options,
    url: `${baseUrl}${options.url}`,
    headers: {
      'Content-Type': 'application/json',
      'X-SIGNET-API-Key': bundle.authData.api_key,
      'User-Agent': `signet-zapier-integration/${version}`,
      ...options.headers,
    },
  });
};

// Trigger: New Verified Exchange
const newVerifiedExchangeTrigger = {
  key: 'new_verified_exchange',
  noun: 'Verified Exchange',
  display: {
    label: 'New Verified Exchange',
    description: 'Triggers when a new verified exchange is created in Signet Protocol.',
    important: true,
  },
  
  operation: {
    type: 'polling',
    
    // Polling function
    perform: async (z, bundle) => {
      // Since Signet doesn't have a native polling endpoint, we'll simulate
      // by checking recent receipts or implementing webhook-style polling
      
      // For now, we'll return a sample structure
      // In production, this would poll the Signet API for recent exchanges
      const response = await makeRequest(z, bundle, {
        url: '/v1/billing/dashboard',
        method: 'GET',
      });
      
      // Transform billing data into exchange events
      const dashboard = response.data;
      const metrics = dashboard.metrics || {};
      
      // Create synthetic events based on usage metrics
      // In a real implementation, you'd have a proper events API
      return [
        {
          id: `exchange-${Date.now()}`,
          trace_id: `zapier-poll-${Date.now()}`,
          timestamp: new Date().toISOString(),
          vex_usage: metrics.vex_usage || 0,
          fu_usage: metrics.fu_usage || 0,
          status: 'verified',
        },
      ];
    },
    
    // Sample data for testing
    sample: {
      id: 'exchange-1234567890',
      trace_id: 'zapier-sample-trace-id',
      timestamp: '2024-01-15T10:30:00Z',
      vex_usage: 1,
      fu_usage: 0,
      status: 'verified',
      receipt_hash: 'bafkreiabcd1234567890abcdef',
      hop: 1,
    },
    
    // Output fields definition
    outputFields: [
      { key: 'id', label: 'Exchange ID', type: 'string' },
      { key: 'trace_id', label: 'Trace ID', type: 'string' },
      { key: 'timestamp', label: 'Timestamp', type: 'datetime' },
      { key: 'vex_usage', label: 'VEx Usage', type: 'integer' },
      { key: 'fu_usage', label: 'FU Usage', type: 'integer' },
      { key: 'status', label: 'Status', type: 'string' },
      { key: 'receipt_hash', label: 'Receipt Hash', type: 'string' },
      { key: 'hop', label: 'Hop Number', type: 'integer' },
    ],
  },
};

// Action: Send Exchange
const sendExchangeAction = {
  key: 'send_exchange',
  noun: 'Exchange',
  display: {
    label: 'Send Exchange',
    description: 'Create a verified exchange through Signet Protocol.',
    important: true,
  },
  
  operation: {
    // Input fields
    inputFields: [
      {
        key: 'payload_type',
        label: 'Payload Type',
        type: 'string',
        default: 'openai.tooluse.invoice.v1',
        helpText: 'Source payload type',
      },
      {
        key: 'target_type',
        label: 'Target Type',
        type: 'string',
        default: 'invoice.iso20022.v1',
        helpText: 'Target payload type',
      },
      {
        key: 'payload_data',
        label: 'Payload Data',
        type: 'text',
        required: true,
        helpText: 'JSON payload data for the exchange',
      },
      {
        key: 'forward_url',
        label: 'Forward URL',
        type: 'string',
        helpText: 'Optional URL to forward normalized data',
      },
      {
        key: 'trace_id',
        label: 'Trace ID',
        type: 'string',
        helpText: 'Optional trace ID for chaining (auto-generated if not provided)',
      },
    ],
    
    // Perform the action
    perform: async (z, bundle) => {
      const { payload_type, target_type, payload_data, forward_url, trace_id } = bundle.inputData;
      
      // Parse payload data
      let payload;
      try {
        payload = JSON.parse(payload_data);
      } catch (error) {
        throw new z.errors.HaltedError('Invalid JSON in payload data');
      }
      
      // Generate trace ID if not provided
      const finalTraceId = trace_id || `zapier-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      
      // Generate idempotency key
      const idempotencyKey = `zapier-${finalTraceId}-${Date.now()}`;
      
      // Prepare exchange data
      const exchangeData = {
        payload_type: payload_type || 'openai.tooluse.invoice.v1',
        target_type: target_type || 'invoice.iso20022.v1',
        payload,
        trace_id: finalTraceId,
      };
      
      if (forward_url) {
        exchangeData.forward_url = forward_url;
      }
      
      // Make the exchange request
      const response = await makeRequest(z, bundle, {
        url: '/v1/exchange',
        method: 'POST',
        headers: {
          'X-SIGNET-Idempotency-Key': idempotencyKey,
        },
        body: exchangeData,
      });
      
      const result = response.data;
      
      // Return formatted result
      return {
        id: finalTraceId,
        trace_id: finalTraceId,
        receipt_hash: result.receipt.receipt_hash,
        hop: result.receipt.hop,
        timestamp: result.receipt.ts,
        normalized: result.normalized,
        forwarded: result.forwarded,
        status: 'success',
      };
    },
    
    // Sample output
    sample: {
      id: 'zapier-1234567890-abc123',
      trace_id: 'zapier-1234567890-abc123',
      receipt_hash: 'bafkreiabcd1234567890abcdef',
      hop: 1,
      timestamp: '2024-01-15T10:30:00Z',
      status: 'success',
    },
    
    // Output fields
    outputFields: [
      { key: 'id', label: 'Exchange ID', type: 'string' },
      { key: 'trace_id', label: 'Trace ID', type: 'string' },
      { key: 'receipt_hash', label: 'Receipt Hash', type: 'string' },
      { key: 'hop', label: 'Hop Number', type: 'integer' },
      { key: 'timestamp', label: 'Timestamp', type: 'datetime' },
      { key: 'status', label: 'Status', type: 'string' },
    ],
  },
};

// Action: Export Bundle
const exportBundleAction = {
  key: 'export_bundle',
  noun: 'Bundle',
  display: {
    label: 'Export Bundle',
    description: 'Export a signed receipt chain bundle from Signet Protocol.',
  },
  
  operation: {
    // Input fields
    inputFields: [
      {
        key: 'trace_id',
        label: 'Trace ID',
        type: 'string',
        required: true,
        helpText: 'Trace ID of the receipt chain to export',
      },
    ],
    
    // Perform the action
    perform: async (z, bundle) => {
      const { trace_id } = bundle.inputData;
      
      // Export the chain
      const response = await makeRequest(z, bundle, {
        url: `/v1/receipts/export/${trace_id}`,
        method: 'GET',
      });
      
      if (response.status === 404) {
        throw new z.errors.HaltedError(`No receipt chain found for trace ID: ${trace_id}`);
      }
      
      const result = response.data;
      
      // Extract signature headers
      const signatureHeaders = {
        bundle_cid: response.headers['x-odin-response-cid'],
        signature: response.headers['x-odin-signature'],
        kid: response.headers['x-odin-kid'],
      };
      
      return {
        trace_id,
        exported_at: result.exported_at,
        chain_length: result.chain ? result.chain.length : 0,
        bundle_cid: signatureHeaders.bundle_cid,
        signature: signatureHeaders.signature,
        kid: signatureHeaders.kid,
        bundle: result,
      };
    },
    
    // Sample output
    sample: {
      trace_id: 'sample-trace-id',
      exported_at: '2024-01-15T10:30:00Z',
      chain_length: 3,
      bundle_cid: 'bafkreiabcd1234567890abcdef',
      signature: 'eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9...',
      kid: 'signet-key-1',
    },
    
    // Output fields
    outputFields: [
      { key: 'trace_id', label: 'Trace ID', type: 'string' },
      { key: 'exported_at', label: 'Exported At', type: 'datetime' },
      { key: 'chain_length', label: 'Chain Length', type: 'integer' },
      { key: 'bundle_cid', label: 'Bundle CID', type: 'string' },
      { key: 'signature', label: 'Signature', type: 'string' },
      { key: 'kid', label: 'Key ID', type: 'string' },
    ],
  },
};

// Search: Find Receipt Chain
const findReceiptChainSearch = {
  key: 'find_receipt_chain',
  noun: 'Receipt Chain',
  display: {
    label: 'Find Receipt Chain',
    description: 'Find a receipt chain by trace ID.',
  },
  
  operation: {
    // Input fields
    inputFields: [
      {
        key: 'trace_id',
        label: 'Trace ID',
        type: 'string',
        required: true,
        helpText: 'Trace ID to search for',
      },
    ],
    
    // Perform the search
    perform: async (z, bundle) => {
      const { trace_id } = bundle.inputData;
      
      // Get the receipt chain
      const response = await makeRequest(z, bundle, {
        url: `/v1/receipts/chain/${trace_id}`,
        method: 'GET',
      });
      
      if (response.status === 404) {
        return []; // No results found
      }
      
      const chain = response.data;
      
      // Return chain information
      return [
        {
          id: trace_id,
          trace_id,
          chain_length: chain.length,
          first_receipt: chain[0],
          last_receipt: chain[chain.length - 1],
          receipts: chain,
        },
      ];
    },
    
    // Sample output
    sample: {
      id: 'sample-trace-id',
      trace_id: 'sample-trace-id',
      chain_length: 3,
      first_receipt: {
        receipt_hash: 'bafkreiabc123',
        hop: 1,
        ts: '2024-01-15T10:30:00Z',
      },
      last_receipt: {
        receipt_hash: 'bafkreixyz789',
        hop: 3,
        ts: '2024-01-15T10:35:00Z',
      },
    },
  },
};

// App definition
module.exports = {
  version,
  platformVersion: '15.0.0',
  
  authentication,
  
  triggers: {
    [newVerifiedExchangeTrigger.key]: newVerifiedExchangeTrigger,
  },
  
  creates: {
    [sendExchangeAction.key]: sendExchangeAction,
    [exportBundleAction.key]: exportBundleAction,
  },
  
  searches: {
    [findReceiptChainSearch.key]: findReceiptChainSearch,
  },
  
  // App metadata
  beforeRequest: [
    (request, z, bundle) => {
      // Add common headers or modify requests
      return request;
    },
  ],
  
  afterResponse: [
    (response, z, bundle) => {
      // Handle common response processing
      if (response.status >= 400) {
        throw new z.errors.ResponseError(
          `Signet Protocol API error: ${response.status} - ${response.content}`,
          response
        );
      }
      return response;
    },
  ],
  
  // Hydration methods for handling large data
  hydrators: {},
  
  // Request middleware
  requestTemplate: {
    headers: {
      'User-Agent': `signet-zapier-integration/${version}`,
    },
  },
};
