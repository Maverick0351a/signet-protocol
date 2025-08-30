/**
 * Signet Protocol - JavaScript/TypeScript SDK
 * Complete SDK for Signet Protocol verification and client operations
 */

// Export verification functions
export {
  SignetVerifier,
  verifyReceipt,
  verifyChain,
  verifyExportBundle,
  computeCid,
  canonicalize,
} from './signet-verify';

// Export client functions
export {
  SignetClient,
  exchange,
  verifyInvoice,
} from './signet-client';

// Export all types
export * from './types';

// Default export for convenience
export { SignetClient as default } from './signet-client';
