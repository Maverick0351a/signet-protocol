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
Object.defineProperty(exports, "__esModule", { value: true });
exports.deactivate = exports.activate = void 0;
const vscode = __importStar(require("vscode"));
const signetClient_1 = require("./signetClient");
const receiptChainProvider_1 = require("./receiptChainProvider");
const chainVisualizerProvider_1 = require("./chainVisualizerProvider");
const receiptDecorationProvider_1 = require("./receiptDecorationProvider");
let signetClient;
let receiptChainProvider;
let chainVisualizerProvider;
let receiptDecorationProvider;
function activate(context) {
    console.log('Signet Lens extension is now active!');
    // Initialize providers
    signetClient = new signetClient_1.SignetClient();
    receiptChainProvider = new receiptChainProvider_1.ReceiptChainProvider(signetClient);
    chainVisualizerProvider = new chainVisualizerProvider_1.ChainVisualizerProvider(context, signetClient);
    receiptDecorationProvider = new receiptDecorationProvider_1.ReceiptDecorationProvider(signetClient);
    // Register tree data provider
    vscode.window.registerTreeDataProvider('signet-lens.receiptChains', receiptChainProvider);
    // Register webview provider
    vscode.window.registerWebviewViewProvider('signet-lens.chainVisualizer', chainVisualizerProvider);
    // Register commands
    const commands = [
        vscode.commands.registerCommand('signet-lens.verifyReceipt', verifyReceipt),
        vscode.commands.registerCommand('signet-lens.visualizeChain', visualizeChain),
        vscode.commands.registerCommand('signet-lens.copyBundleCID', copyBundleCID),
        vscode.commands.registerCommand('signet-lens.diffCID', diffCID),
        vscode.commands.registerCommand('signet-lens.openSettings', openSettings),
        vscode.commands.registerCommand('signet-lens.refreshChains', () => receiptChainProvider.refresh()),
    ];
    // Register text document change listener for auto-verification
    const documentChangeListener = vscode.workspace.onDidChangeTextDocument(async (event) => {
        const config = vscode.workspace.getConfiguration('signet-lens');
        if (config.get('autoVerify') && event.document.languageId === 'json') {
            await receiptDecorationProvider.updateDecorations(event.document);
        }
    });
    // Register active editor change listener
    const activeEditorChangeListener = vscode.window.onDidChangeActiveTextEditor(async (editor) => {
        if (editor && editor.document.languageId === 'json') {
            const config = vscode.workspace.getConfiguration('signet-lens');
            if (config.get('autoVerify')) {
                await receiptDecorationProvider.updateDecorations(editor.document);
            }
        }
    });
    // Add all disposables to context
    context.subscriptions.push(...commands, documentChangeListener, activeEditorChangeListener, receiptDecorationProvider);
    // Set context for when receipt chains are available
    vscode.commands.executeCommand('setContext', 'signet-lens.hasReceiptChains', true);
    // Show welcome message
    vscode.window.showInformationMessage('Signet Lens is ready! Paste a receipt chain to verify and visualize.');
}
exports.activate = activate;
async function verifyReceipt() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active editor found');
        return;
    }
    try {
        const selection = editor.selection;
        const text = selection.isEmpty ? editor.document.getText() : editor.document.getText(selection);
        // Try to parse as JSON
        let receiptData;
        try {
            receiptData = JSON.parse(text);
        }
        catch (error) {
            vscode.window.showErrorMessage('Invalid JSON format');
            return;
        }
        // Check if it looks like a receipt or chain
        if (Array.isArray(receiptData)) {
            // It's a chain
            const result = await signetClient.verifyChain(receiptData);
            showVerificationResult(result, receiptData.length);
        }
        else if (receiptData.receipt_hash || receiptData.trace_id) {
            // It's a single receipt or has trace_id
            const traceId = receiptData.trace_id || extractTraceIdFromReceipt(receiptData);
            if (traceId) {
                const chain = await signetClient.getReceiptChain(traceId);
                if (chain) {
                    const result = await signetClient.verifyChain(chain);
                    showVerificationResult(result, chain.length);
                    receiptChainProvider.addChain(traceId, chain);
                }
                else {
                    vscode.window.showErrorMessage(`No chain found for trace ID: ${traceId}`);
                }
            }
            else {
                vscode.window.showErrorMessage('No trace ID found in receipt data');
            }
        }
        else {
            vscode.window.showErrorMessage('Selected text does not appear to be a Signet receipt or chain');
        }
    }
    catch (error) {
        vscode.window.showErrorMessage(`Verification failed: ${error}`);
    }
}
async function visualizeChain() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active editor found');
        return;
    }
    try {
        const selection = editor.selection;
        const text = selection.isEmpty ? editor.document.getText() : editor.document.getText(selection);
        let receiptData;
        try {
            receiptData = JSON.parse(text);
        }
        catch (error) {
            vscode.window.showErrorMessage('Invalid JSON format');
            return;
        }
        let chain;
        let traceId;
        if (Array.isArray(receiptData)) {
            // It's already a chain
            chain = receiptData;
            traceId = chain[0]?.trace_id || 'unknown';
        }
        else if (receiptData.trace_id) {
            // Get chain from trace ID
            traceId = receiptData.trace_id;
            chain = await signetClient.getReceiptChain(traceId);
        }
        else {
            vscode.window.showErrorMessage('No trace ID found in data');
            return;
        }
        if (chain && chain.length > 0) {
            await chainVisualizerProvider.visualizeChain(traceId, chain);
            receiptChainProvider.addChain(traceId, chain);
        }
        else {
            vscode.window.showErrorMessage('No valid chain data found');
        }
    }
    catch (error) {
        vscode.window.showErrorMessage(`Visualization failed: ${error}`);
    }
}
async function copyBundleCID() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active editor found');
        return;
    }
    try {
        const selection = editor.selection;
        const text = selection.isEmpty ? editor.document.getText() : editor.document.getText(selection);
        let receiptData;
        try {
            receiptData = JSON.parse(text);
        }
        catch (error) {
            vscode.window.showErrorMessage('Invalid JSON format');
            return;
        }
        let traceId;
        if (receiptData.trace_id) {
            traceId = receiptData.trace_id;
        }
        else if (Array.isArray(receiptData) && receiptData[0]?.trace_id) {
            traceId = receiptData[0].trace_id;
        }
        else {
            vscode.window.showErrorMessage('No trace ID found in data');
            return;
        }
        // Export the chain to get the bundle CID
        const exportBundle = await signetClient.exportChain(traceId);
        if (exportBundle && exportBundle.signature_headers?.bundle_cid) {
            const bundleCID = exportBundle.signature_headers.bundle_cid;
            await vscode.env.clipboard.writeText(bundleCID);
            vscode.window.showInformationMessage(`Bundle CID copied to clipboard: ${bundleCID}`);
        }
        else {
            vscode.window.showErrorMessage('Could not retrieve bundle CID');
        }
    }
    catch (error) {
        vscode.window.showErrorMessage(`Failed to copy bundle CID: ${error}`);
    }
}
async function diffCID() {
    const input = await vscode.window.showInputBox({
        prompt: 'Enter CID to compare with current selection',
        placeHolder: 'bafkreiabc123...'
    });
    if (!input) {
        return;
    }
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showErrorMessage('No active editor found');
        return;
    }
    try {
        const selection = editor.selection;
        const text = selection.isEmpty ? editor.document.getText() : editor.document.getText(selection);
        // Calculate CID of current selection
        const currentCID = await signetClient.calculateCID(text);
        // Show diff result
        if (currentCID === input) {
            vscode.window.showInformationMessage('✅ CIDs match! Content is identical.');
        }
        else {
            vscode.window.showWarningMessage(`❌ CIDs differ:\nCurrent: ${currentCID}\nProvided: ${input}`);
        }
    }
    catch (error) {
        vscode.window.showErrorMessage(`CID comparison failed: ${error}`);
    }
}
function openSettings() {
    vscode.commands.executeCommand('workbench.action.openSettings', 'signet-lens');
}
function showVerificationResult(result, chainLength) {
    if (result.valid) {
        vscode.window.showInformationMessage(`✅ Receipt chain verified! ${chainLength} hops, integrity confirmed.`);
    }
    else {
        vscode.window.showErrorMessage(`❌ Receipt chain verification failed: ${result.error || 'Unknown error'}`);
    }
}
function extractTraceIdFromReceipt(receipt) {
    // Try to extract trace ID from various possible locations
    return receipt.trace_id ||
        receipt.traceId ||
        receipt.id ||
        receipt.receipt?.trace_id ||
        null;
}
function deactivate() {
    // Cleanup if needed
}
exports.deactivate = deactivate;
//# sourceMappingURL=extension.js.map