// Minimal Insomnia plugin to verify Signet receipts embedded in responses.
// Place this file in Insomnia's plugins folder or symlink from this repo.
// Exposes an action to parse a JSON response body and verify receipt signature
// using the public JWKS endpoint of the running Signet server.

module.exports.templateTags = [
  {
    name: 'signetVerify',
    displayName: 'Signet Verify Receipt',
    description: 'Verify a Signet protocol receipt in a JSON response',
    args: [
      { displayName: 'Receipt JSON', type: 'string' },
      { displayName: 'JWKS URL', type: 'string', defaultValue: 'http://localhost:8000/jwks' }
    ],
    async run (ctx, receiptJson, jwksUrl) {
      try {
        const receipt = JSON.parse(receiptJson);
        if (!receipt || !receipt.signature || !receipt.payload) {
          throw new Error('Invalid receipt structure');
        }
        // Fetch JWKS
        const res = await require('node-fetch')(jwksUrl);
        if (!res.ok) throw new Error('Failed to fetch JWKS: ' + res.status);
        const jwks = await res.json();
        const key = jwks.keys && jwks.keys[0];
        if (!key) throw new Error('No keys present in JWKS');
        // Simple Ed25519 verify using tweetnacl (Insomnia ships with Node environment)
        const nacl = require('tweetnacl');
        const util = require('tweetnacl-util');
        const pubKey = Buffer.from(key.x, 'base64url');
        const message = Buffer.from(receipt.payload, 'utf8');
        const sig = Buffer.from(receipt.signature, 'base64url');
        const ok = nacl.sign.detached.verify(message, sig, pubKey);
        return ok ? 'VALID' : 'INVALID';
      } catch (e) {
        return 'ERROR: ' + e.message;
      }
    }
  }
];
