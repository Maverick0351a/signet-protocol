import * as vscode from 'vscode';
import { SignetClient } from './signetClient';

export class ChainVisualizerProvider implements vscode.WebviewViewProvider {
  constructor(private context: vscode.ExtensionContext, private client: SignetClient) {}

  resolveWebviewView(view: vscode.WebviewView): void | Thenable<void> {
    view.webview.options = { enableScripts: true };    
    view.webview.html = this.renderSkeleton();
  }

  async visualizeChain(traceId: string, chain: any[]) {
    const panel = await this.ensurePanel();
    panel.webview.postMessage({ type: 'chain', traceId, chain });
  }

  private panel: vscode.WebviewView | undefined;
  private async ensurePanel(): Promise<vscode.WebviewView> {
    if (this.panel) return this.panel;
    await vscode.commands.executeCommand('workbench.view.explorer');
    await vscode.commands.executeCommand('signet-lens.chainVisualizer.focus');
    // VS Code sets focus & triggers resolve – slight delay
    await new Promise(r => setTimeout(r, 150));
    return this.panel!;
  }

  private renderSkeleton(): string {
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
