import * as vscode from 'vscode';
import { SignetClient } from './signetClient';

interface ChainEntry { traceId: string; chain: any[]; };

export class ReceiptChainProvider implements vscode.TreeDataProvider<ChainItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<ChainItem | void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;
  private items: ChainEntry[] = [];
  constructor(private client: SignetClient) {}

  refresh() { this._onDidChangeTreeData.fire(); }

  addChain(traceId: string, chain: any[]) {
    const existing = this.items.find(i => i.traceId === traceId);
    if (existing) existing.chain = chain; else this.items.unshift({ traceId, chain });
    if (this.items.length > 20) this.items.pop();
    this.refresh();
  }

  getTreeItem(e: ChainItem): vscode.TreeItem { return e; }
  getChildren(e?: ChainItem): Thenable<ChainItem[]> {
    if (!e) {
      return Promise.resolve(this.items.map(i => new ChainItem(`${i.traceId}`, vscode.TreeItemCollapsibleState.Collapsed, i)));
    }
    if (e.entry) {
      return Promise.resolve(e.entry.chain.map(rec => new ChainItem(`Hop ${rec.hop} – ${rec.receipt_hash?.slice(0,8)}`, vscode.TreeItemCollapsibleState.None)));
    }
    return Promise.resolve([]);
  }
}

class ChainItem extends vscode.TreeItem {
  constructor(label: string, collapsible: vscode.TreeItemCollapsibleState, public entry?: ChainEntry) { super(label, collapsible); }
}
