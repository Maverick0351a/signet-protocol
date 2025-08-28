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
exports.ReceiptDecorationProvider = void 0;
const vscode = __importStar(require("vscode"));
class ReceiptDecorationProvider {
    constructor(client) {
        this.client = client;
        this.decorationType = vscode.window.createTextEditorDecorationType({
            after: { color: new vscode.ThemeColor('editorCodeLens.foreground') }
        });
    }
    async updateDecorations(doc) {
        if (doc.languageId !== 'json')
            return;
        try {
            const text = doc.getText();
            const data = JSON.parse(text);
            const decorations = [];
            if (Array.isArray(data)) {
                // Mark first line with chain summary
                const firstLine = doc.lineAt(0);
                const res = await this.client.verifyChain(data);
                decorations.push({ range: firstLine.range, renderOptions: { after: { contentText: res.valid ? ' ✅ verified chain (' + data.length + ' hops)' : ' ❌ ' + res.error } } });
            }
            else if (data.trace_id) {
                const firstLine = doc.lineAt(0);
                decorations.push({ range: firstLine.range, renderOptions: { after: { contentText: ' trace_id: ' + data.trace_id } } });
            }
            const editor = vscode.window.visibleTextEditors.find(e => e.document === doc);
            if (editor)
                editor.setDecorations(this.decorationType, decorations);
        }
        catch { /* ignore */ }
    }
    dispose() { this.decorationType.dispose(); }
}
exports.ReceiptDecorationProvider = ReceiptDecorationProvider;
//# sourceMappingURL=receiptDecorationProvider.js.map