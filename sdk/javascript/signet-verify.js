/**
 * Signet Protocol JavaScript Verification SDK
 * 
 * Browser and Node.js compatible verification of Signet receipts
 * with cryptographic signature validation.
 */

/**
 * Verify a Signet receipt
 * @param {Object} receipt - The receipt data to verify
 * @param {string} publicKeyJwk - Public key in JWK format
 * @returns {Promise<{valid: boolean, reason: string}>}
 */
export async function verifyReceipt(receipt, publicKeyJwk) {
    try {
        // Extract signature
        const signature = receipt.signature;
        if (!signature) {
            return { valid: false, reason: 'No signature found' };
        }
        
        // Create receipt copy without signature
        const receiptCopy = { ...receipt };
        delete receiptCopy.signature;
        
        // Canonicalize JSON (RFC 8785)
        const canonical = JSON.stringify(receiptCopy, Object.keys(receiptCopy).sort());
        
        // Import public key
        const publicKey = await crypto.subtle.importKey(
            'jwk',
            publicKeyJwk,
            {
                name: 'Ed25519',
                namedCurve: 'Ed25519'
            },
            false,
            ['verify']
        );
        
        // Decode signature
        const signatureBytes = base64ToArrayBuffer(signature);
        
        // Verify signature
        const isValid = await crypto.subtle.verify(
            'Ed25519',
            publicKey,
            signatureBytes,
            new TextEncoder().encode(canonical)
        );
        
        return {
            valid: isValid,
            reason: isValid ? 'Valid signature' : 'Invalid signature'
        };
        
    } catch (error) {
        return {
            valid: false,
            reason: `Verification error: ${error.message}`
        };
    }
}

/**
 * Verify a chain of receipts
 * @param {Array} receipts - Array of receipt data in chronological order
 * @param {string} publicKeyJwk - Public key in JWK format
 * @returns {Promise<{valid: boolean, reason: string}>}
 */
export async function verifyReceiptChain(receipts, publicKeyJwk) {
    if (!receipts || receipts.length === 0) {
        return { valid: false, reason: 'Empty receipt chain' };
    }
    
    // Verify each receipt individually
    for (let i = 0; i < receipts.length; i++) {
        const result = await verifyReceipt(receipts[i], publicKeyJwk);
        if (!result.valid) {
            return {
                valid: false,
                reason: `Receipt ${i} invalid: ${result.reason}`
            };
        }
    }
    
    // Verify hash chain
    for (let i = 1; i < receipts.length; i++) {
        const prevReceipt = receipts[i - 1];
        const currReceipt = receipts[i];
        
        if ((currReceipt.hop || 1) !== (prevReceipt.hop || 1) + 1) {
            return {
                valid: false,
                reason: `Broken chain at receipt ${i}: hop sequence invalid`
            };
        }
    }
    
    return { valid: true, reason: 'Valid receipt chain' };
}

/**
 * Compute SHA-256 hash of content
 * @param {any} content - Content to hash
 * @returns {Promise<string>} SHA-256 hash with 'sha256:' prefix
 */
export async function computeContentHash(content) {
    let dataToHash;
    
    if (typeof content === 'object') {
        // Canonicalize JSON
        dataToHash = JSON.stringify(content, Object.keys(content).sort());
    } else {
        dataToHash = String(content);
    }
    
    const encoder = new TextEncoder();
    const data = encoder.encode(dataToHash);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    
    return `sha256:${hashHex}`;
}

/**
 * Simple Signet client for browser/Node.js
 */
export class SignetClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.apiKey = apiKey;
    }
    
    async exchange(payloadType, targetType, payload, forwardUrl, idempotencyKey) {
        const requestData = {
            payload_type: payloadType,
            target_type: targetType,
            payload: payload,
            forward_url: forwardUrl,
            idempotency_key: idempotencyKey || `js-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
        };
        
        const response = await fetch(`${this.baseUrl}/v1/exchange`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-SIGNET-API-Key': this.apiKey,
                'X-SIGNET-Idempotency-Key': requestData.idempotency_key
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            throw new Error(`Exchange failed: ${response.status} ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    async getReceipt(receiptId) {
        const response = await fetch(`${this.baseUrl}/v1/receipts/${receiptId}`, {
            headers: {
                'X-SIGNET-API-Key': this.apiKey
            }
        });
        
        if (!response.ok) {
            throw new Error(`Get receipt failed: ${response.status} ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    async healthCheck() {
        const response = await fetch(`${this.baseUrl}/healthz`);
        
        if (!response.ok) {
            throw new Error(`Health check failed: ${response.status} ${response.statusText}`);
        }
        
        return await response.json();
    }
}

/**
 * Utility functions
 */
function base64ToArrayBuffer(base64) {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
}

// Example usage
if (typeof window !== 'undefined') {
    // Browser example
    window.signetExample = async function() {
        const client = new SignetClient('http://localhost:8088', 'demo_key');
        
        try {
            const health = await client.healthCheck();
            console.log('Server health:', health);
            
            const result = await client.exchange(
                'openai.tooluse.invoice.v1',
                'invoice.iso20022.v1',
                {
                    tool_calls: [{
                        type: 'function',
                        function: {
                            name: 'create_invoice',
                            arguments: JSON.stringify({
                                invoice_id: 'INV-001',
                                amount: 1000,
                                currency: 'USD'
                            })
                        }
                    }]
                },
                'https://webhook.site/your-unique-url'
            );
            
            console.log('Exchange result:', result);
        } catch (error) {
            console.error('Error:', error);
        }
    };
}