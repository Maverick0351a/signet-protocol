/**
 * Signet Protocol - JavaScript Verification SDK
 * Verify receipts and chains in 5 lines of code.
 */

class SignetVerifier {
    constructor(options = {}) {
        this.jwksCache = new Map();
        this.jwksCacheTtl = options.jwksCacheTtl || 3600000; // 1 hour in ms
    }

    /**
     * Verify a single Signet receipt
     * @param {Object} receipt - The receipt to verify
     * @param {Object} previousReceipt - The previous receipt in the chain (optional)
     * @returns {Promise<{valid: boolean, reason: string}>}
     */
    async verifyReceipt(receipt, previousReceipt = null) {
        try {
            // 1. Verify receipt hash
            const computedHash = await this._computeReceiptHash(receipt);
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
                const computedCid = await this._computeCid(receipt.canon);
                if (receipt.cid !== computedCid) {
                    return { valid: false, reason: 'Invalid content identifier' };
                }
            }

            // 4. Verify timestamp format
            if (receipt.ts) {
                try {
                    new Date(receipt.ts);
                } catch (e) {
                    return { valid: false, reason: 'Invalid timestamp format' };
                }
            }

            return { valid: true, reason: 'Valid receipt' };

        } catch (error) {
            return { valid: false, reason: `Verification error: ${error.message}` };
        }
    }

    /**
     * Verify a complete receipt chain
     * @param {Array} receipts - List of receipts in chronological order
     * @returns {Promise<{valid: boolean, reason: string}>}
     */
    async verifyChain(receipts) {
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
            const previousReceipt = i > 0 ? receipts[i - 1] : null;
            
            const result = await this.verifyReceipt(receipt, previousReceipt);
            if (!result.valid) {
                return { valid: false, reason: `Receipt ${i}: ${result.reason}` };
            }
        }

        return { valid: true, reason: 'Valid chain' };
    }

    /**
     * Verify a signed export bundle
     * @param {Object} bundle - The export bundle to verify
     * @param {string} jwksUrl - URL to fetch JWKS (optional)
     * @returns {Promise<{valid: boolean, reason: string}>}
     */
    async verifyExportBundle(bundle, jwksUrl = null) {
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
                exported_at: bundle.exported_at
            };
            const computedCid = await this._computeCid(this._canonicalize(bundleContent));
            if (bundle.bundle_cid !== computedCid) {
                return { valid: false, reason: 'Invalid bundle CID' };
            }

            // 3. Verify signature (if JWKS available)
            if (bundle.signature && bundle.kid && jwksUrl) {
                const sigResult = await this._verifySignature(
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
            return { valid: false, reason: `Bundle verification error: ${error.message}` };
        }
    }

    /**
     * Compute the hash of a receipt (excluding the hash field itself)
     */
    async _computeReceiptHash(receipt) {
        const receiptCopy = { ...receipt };
        delete receiptCopy.receipt_hash;
        const canonical = this._canonicalize(receiptCopy);
        return 'sha256:' + await this._sha256(canonical);
    }

    /**
     * Compute content identifier for canonicalized content
     */
    async _computeCid(content) {
        return 'sha256:' + await this._sha256(content);
    }

    /**
     * JSON Canonicalization Scheme (JCS) implementation
     * Simplified version - for production use a full RFC 8785 implementation
     */
    _canonicalize(obj) {
        return JSON.stringify(obj, Object.keys(obj).sort());
    }

    /**
     * Compute SHA-256 hash
     */
    async _sha256(message) {
        if (typeof crypto !== 'undefined' && crypto.subtle) {
            // Browser environment
            const msgBuffer = new TextEncoder().encode(message);
            const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        } else {
            // Node.js environment
            const crypto = require('crypto');
            return crypto.createHash('sha256').update(message).digest('hex');
        }
    }

    /**
     * Verify Ed25519 signature using JWKS
     */
    async _verifySignature(message, signature, kid, jwksUrl) {
        try {
            // Fetch JWKS
            const jwks = await this._fetchJwks(jwksUrl);

            // Find key
            const key = jwks.keys?.find(k => 
                k.kid === kid && k.kty === 'OKP' && k.crv === 'Ed25519'
            );

            if (!key) {
                return { valid: false, reason: `Key ${kid} not found in JWKS` };
            }

            // Verify signature (requires Web Crypto API or Node.js crypto)
            if (typeof crypto !== 'undefined' && crypto.subtle) {
                try {
                    // Browser environment with Web Crypto API
                    const publicKeyBytes = this._base64UrlDecode(key.x);
                    const signatureBytes = this._base64Decode(signature);
                    
                    const publicKey = await crypto.subtle.importKey(
                        'raw',
                        publicKeyBytes,
                        { name: 'Ed25519', namedCurve: 'Ed25519' },
                        false,
                        ['verify']
                    );

                    const messageBytes = new TextEncoder().encode(message);
                    const isValid = await crypto.subtle.verify(
                        'Ed25519',
                        publicKey,
                        signatureBytes,
                        messageBytes
                    );

                    return { valid: isValid, reason: isValid ? 'Valid signature' : 'Invalid signature' };

                } catch (error) {
                    return { valid: false, reason: `Signature verification failed: ${error.message}` };
                }
            } else {
                // Node.js environment - would need additional crypto library
                return { valid: false, reason: 'Ed25519 verification requires Web Crypto API or additional library' };
            }

        } catch (error) {
            return { valid: false, reason: `JWKS verification error: ${error.message}` };
        }
    }

    /**
     * Fetch JWKS with caching
     */
    async _fetchJwks(jwksUrl) {
        const now = Date.now();
        
        if (this.jwksCache.has(jwksUrl)) {
            const { jwks, timestamp } = this.jwksCache.get(jwksUrl);
            if (now - timestamp < this.jwksCacheTtl) {
                return jwks;
            }
        }

        // Fetch fresh JWKS
        const response = await fetch(jwksUrl);
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
    _base64UrlDecode(str) {
        // Add padding if needed
        str += '='.repeat((4 - str.length % 4) % 4);
        // Replace URL-safe characters
        str = str.replace(/-/g, '+').replace(/_/g, '/');
        // Decode
        return Uint8Array.from(atob(str), c => c.charCodeAt(0));
    }

    /**
     * Base64 decode
     */
    _base64Decode(str) {
        return Uint8Array.from(atob(str), c => c.charCodeAt(0));
    }
}

// Convenience functions for one-liner usage
async function verifyReceipt(receipt, previousReceipt = null) {
    const verifier = new SignetVerifier();
    return await verifier.verifyReceipt(receipt, previousReceipt);
}

async function verifyChain(receipts) {
    const verifier = new SignetVerifier();
    return await verifier.verifyChain(receipts);
}

async function verifyExportBundle(bundle, jwksUrl = null) {
    const verifier = new SignetVerifier();
    return await verifier.verifyExportBundle(bundle, jwksUrl);
}

// Export for different environments
if (typeof module !== 'undefined' && module.exports) {
    // Node.js
    module.exports = {
        SignetVerifier,
        verifyReceipt,
        verifyChain,
        verifyExportBundle
    };
} else if (typeof window !== 'undefined') {
    // Browser
    window.SignetVerifier = SignetVerifier;
    window.verifyReceipt = verifyReceipt;
    window.verifyChain = verifyChain;
    window.verifyExportBundle = verifyExportBundle;
}

// Example usage
if (typeof module !== 'undefined' && require.main === module) {
    // Example receipt
    const receipt = {
        trace_id: 'example-123',
        hop: 1,
        ts: '2025-01-27T12:00:00Z',
        tenant: 'demo',
        cid: 'sha256:abc123',
        canon: '{"test":"data"}',
        algo: 'sha256',
        prev_receipt_hash: null,
        receipt_hash: 'sha256:def456',
        policy: { engine: 'HEL', allowed: true, reason: 'ok' }
    };

    // Verify in one line
    verifyReceipt(receipt).then(result => {
        console.log(`Receipt valid: ${result.valid}, reason: ${result.reason}`);
    });
}
