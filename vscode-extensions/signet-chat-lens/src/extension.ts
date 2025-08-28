import * as vscode from 'vscode';
import { fetch } from 'undici';

interface AgentDescriptor {
  name: string;
  model?: string;
  endpoint: string;
  description?: string;
  headers?: Record<string, string>;
}

class ChatTreeProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
  refresh() { this._onDidChangeTreeData.fire(); }
  getTreeItem(el: vscode.TreeItem) { return el; }
  getChildren(): vscode.ProviderResult<vscode.TreeItem[]> {
    const chat = new vscode.TreeItem('Open Chat');
    chat.command = { command: 'signet.openChat', title: 'Open Chat' };
    const lens = new vscode.TreeItem('Open Lens');
    lens.command = { command: 'signet.openLens', title: 'Open Lens' };
    const cfg = new vscode.TreeItem('Configure API & Key');
    cfg.command = { command: 'signet.configureApi', title: 'Configure API' };
    return [chat, lens, cfg];
  }
}

function ensureConfig(): { apiBase: string } | undefined {
  const apiBase = vscode.workspace.getConfiguration().get<string>('signet.apiBase') || '';
  if (!apiBase) {
    vscode.window.showWarningMessage('Signet API base not set. Run: Signet: Configure API & Key');
    return;
  }
  return { apiBase };
}

async function promptApiConfig(context: vscode.ExtensionContext) {
  const apiBase = await vscode.window.showInputBox({ prompt: 'Signet API Base URL', placeHolder: 'https://signet-protocol.fly.dev' });
  if (!apiBase) { return; }
  await vscode.workspace.getConfiguration().update('signet.apiBase', apiBase, vscode.ConfigurationTarget.Global);
  const apiKey = await vscode.window.showInputBox({ prompt: 'API Key (stored securely)', password: true });
  if (apiKey) await context.secrets.store('signet.apiKey', apiKey);
  vscode.window.showInformationMessage('Signet configuration saved.');
}

async function openChat(context: vscode.ExtensionContext) {
  const webview = createPanel('signetChat', 'Signet Chat', context);
  webview.html = getChatHtml();
}

async function openLens(context: vscode.ExtensionContext) {
  const webview = createPanel('signetLens', 'Signet Lens', context);
  webview.html = getLensHtml();
}

function createPanel(viewId: string, title: string, context: vscode.ExtensionContext): vscode.Webview {
  const panel = vscode.window.createWebviewPanel(viewId, title, { viewColumn: vscode.ViewColumn.One, preserveFocus: true }, { enableScripts: true });
  panel.webview.onDidReceiveMessage(async (msg: any) => {
    try {
      if (msg.type === 'exchange') {
        const cfg = ensureConfig(); if (!cfg) return;
        const key = await context.secrets.get('signet.apiKey');
        const res = await fetch(`${cfg.apiBase}/v1/exchange`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-SIGNET-API-Key': key || '',
            'X-SIGNET-Idempotency-Key': `ext-${Date.now()}`
          },
          body: JSON.stringify(msg.payload)
        });
        panel.webview.postMessage({ type: 'exchangeResult', ok: res.ok, json: await res.json().catch(()=>({})) });
      } else if (msg.type === 'export') {
        const cfg = ensureConfig(); if (!cfg) return;
        const key = await context.secrets.get('signet.apiKey');
        const res = await fetch(`${cfg.apiBase}/v1/export/bundle`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-SIGNET-API-Key': key || '' },
          body: JSON.stringify({ trace_id: msg.traceId })
        });
        panel.webview.postMessage({ type: 'exportResult', ok: res.ok, json: await res.json().catch(()=>({})) });
      }
    } catch (e:any) {
      panel.webview.postMessage({ type: 'error', error: String(e) });
    }
  });
  return panel.webview;
}

function getChatHtml(): string {
  return `<!DOCTYPE html><html><body style="font-family:var(--vscode-font-family);padding:8px;">
  <h3>Signet Chat (Preview)</h3>
  <textarea id="input" style="width:100%;height:80px" placeholder='{"payload_type":"...","target_type":"...","payload":{}}'></textarea>
  <div style="margin-top:6px;">
    <button id="send">Send Exchange</button>
    <button id="export" title="Export last trace id" disabled>Export Bundle</button>
  </div>
  <pre id="out" style="margin-top:10px;white-space:pre-wrap"></pre>
  <script>
  let lastTrace = null;
  const vscode = acquireVsCodeApi();
  document.getElementById('send').onclick = () => {
    let payload; try { payload = JSON.parse(document.getElementById('input').value); } catch { return alert('JSON required'); }
    vscode.postMessage({ type: 'exchange', payload });
  };
  document.getElementById('export').onclick = () => { if (lastTrace) vscode.postMessage({ type: 'export', traceId: lastTrace }); };
  window.addEventListener('message', ev => {
    const msg = ev.data;
    if (msg.type === 'exchangeResult') { lastTrace = msg.json.trace_id; document.getElementById('export').disabled = !lastTrace; }
    document.getElementById('out').textContent = JSON.stringify(msg, null, 2);
  });
  </script></body></html>`;
}

function getLensHtml(): string {
  return `<!DOCTYPE html><html><body style="font-family:var(--vscode-font-family);padding:8px;">
  <h3>Signet Lens (Preview)</h3>
  <p>Paste a trace_id below to export & inspect the receipt bundle.</p>
  <input id="trace" style="width:60%" placeholder="trace_id" /> <button id="go">Load</button>
  <pre id="out" style="margin-top:10px;white-space:pre-wrap"></pre>
  <script>
  const vscode = acquireVsCodeApi();
  document.getElementById('go').onclick = () => {
    const t = document.getElementById('trace').value.trim();
    if (!t) return;
    vscode.postMessage({ type: 'export', traceId: t });
  };
  window.addEventListener('message', ev => {
    const msg = ev.data; document.getElementById('out').textContent = JSON.stringify(msg, null, 2);
  });
  </script></body></html>`;
}

async function addAgentDescriptor() {
  const tpl: AgentDescriptor = { name: 'example-agent', endpoint: 'https://your.api/agent', model: 'gpt-4', headers: { 'Authorization': 'Bearer <token>' } };
  const doc = await vscode.workspace.openTextDocument({ content: JSON.stringify(tpl, null, 2), language: 'json' });
  vscode.window.showTextDocument(doc);
}

export function activate(context: vscode.ExtensionContext) {
  const tree = new ChatTreeProvider();
  vscode.window.registerTreeDataProvider('signetChatView', tree);
  console.log('[signet-chat-lens] activating');
  context.subscriptions.push(
    vscode.commands.registerCommand('signet.openChat', () => openChat(context)),
    vscode.commands.registerCommand('signet.openLens', () => openLens(context)),
    vscode.commands.registerCommand('signet.configureApi', () => promptApiConfig(context)),
    vscode.commands.registerCommand('signet.addAgentDescriptor', () => addAgentDescriptor())
  );
}

export function deactivate() {}
