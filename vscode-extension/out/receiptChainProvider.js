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
exports.ReceiptChainProvider = void 0;
const vscode = __importStar(require("vscode"));
;
class ReceiptChainProvider {
    constructor(client) {
        this.client = client;
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
        this.items = [];
    }
    refresh() { this._onDidChangeTreeData.fire(); }
    addChain(traceId, chain) {
        const existing = this.items.find(i => i.traceId === traceId);
        if (existing)
            existing.chain = chain;
        else
            this.items.unshift({ traceId, chain });
        if (this.items.length > 20)
            this.items.pop();
        this.refresh();
    }
    getTreeItem(e) { return e; }
    getChildren(e) {
        if (!e) {
            return Promise.resolve(this.items.map(i => new ChainItem(`${i.traceId}`, vscode.TreeItemCollapsibleState.Collapsed, i)));
        }
        if (e.entry) {
            return Promise.resolve(e.entry.chain.map(rec => new ChainItem(`Hop ${rec.hop} – ${rec.receipt_hash?.slice(0, 8)}`, vscode.TreeItemCollapsibleState.None)));
        }
        return Promise.resolve([]);
    }
}
exports.ReceiptChainProvider = ReceiptChainProvider;
class ChainItem extends vscode.TreeItem {
    constructor(label, collapsible, entry) {
        super(label, collapsible);
        this.entry = entry;
    }
}
//# sourceMappingURL=receiptChainProvider.js.map