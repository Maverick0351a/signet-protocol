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
exports.ChainVisualizerProvider = void 0;
const vscode = __importStar(require("vscode"));
class ChainVisualizerProvider {
    constructor(context, client) {
        this.context = context;
        this.client = client;
    }
    resolveWebviewView(view) {
        view.webview.options = { enableScripts: true };
        view.webview.html = this.renderSkeleton();
    }
    async visualizeChain(traceId, chain) {
        const panel = await this.ensurePanel();
        panel.webview.postMessage({ type: 'chain', traceId, chain });
    }
    async ensurePanel() {
        if (this.panel)
            return this.panel;
        await vscode.commands.executeCommand('workbench.view.explorer');
        await vscode.commands.executeCommand('signet-lens.chainVisualizer.focus');
        // VS Code sets focus & triggers resolve – slight delay
        await new Promise(r => setTimeout(r, 150));
        return this.panel;
    }
    renderSkeleton() {
        return /* html */ `<!DOCTYPE html><html><head><meta charset='utf-8' />
    <style>
      body { font-family: sans-serif; padding: 8px; }
      .node { border:1px solid #555; padding:6px; margin:4px; border-radius:4px; }
      .hash { font-family: monospace; font-size: 11px; }
    </style></head><body>
    <h3>Receipt Chain</h3>
    <div id='meta'></div>
    <div id='chain'></div>
    <script>
      const vscode = acquireVsCodeApi();
      window.addEventListener('message', ev => {
        const { type, traceId, chain } = ev.data;
        if (type === 'chain') {
          document.getElementById('meta').textContent = 'Trace: ' + traceId + ' (' + chain.length + ' hops)';
          const c = document.getElementById('chain'); c.innerHTML='';
          chain.forEach(rec => {
            const d=document.createElement('div'); d.className='node';
            d.innerHTML = '<div><b>Hop ' + rec.hop + '</b></div>' +
                          '<div class="hash">' + rec.receipt_hash + '</div>' +
                          (rec.prev_receipt_hash?'<div class="hash prev">prev '+ rec.prev_receipt_hash.substring(0,16)+'…</div>':'');
            c.appendChild(d);
          });
        }
      });
    </script></body></html>`;
    }
}
exports.ChainVisualizerProvider = ChainVisualizerProvider;
//# sourceMappingURL=chainVisualizerProvider.js.map