import * as vscode from 'vscode';
import { SignetClient } from './signetClient';

export class ReceiptDecorationProvider implements vscode.Disposable {
  private decorationType = vscode.window.createTextEditorDecorationType({
    after: { color: new vscode.ThemeColor('editorCodeLens.foreground') }
  });
  constructor(private client: SignetClient) {}

  async updateDecorations(doc: vscode.TextDocument) {
    if (doc.languageId !== 'json') return;
    try {
      const text = doc.getText();
      const data = JSON.parse(text);
      const decorations: vscode.DecorationOptions[] = [];
      if (Array.isArray(data)) {
        // Mark first line with chain summary
        const firstLine = doc.lineAt(0);
        const res = await this.client.verifyChain(data);
        decorations.push({ range: firstLine.range, renderOptions: { after: { contentText: res.valid ? ' ✅ verified chain ('+data.length+' hops)' : ' ❌ '+res.error } } });
      } else if (data.trace_id) {
        const firstLine = doc.lineAt(0);
        decorations.push({ range: firstLine.range, renderOptions: { after: { contentText: ' trace_id: '+data.trace_id } } });
      }
      const editor = vscode.window.visibleTextEditors.find(e => e.document === doc);
      if (editor) editor.setDecorations(this.decorationType, decorations);
    } catch { /* ignore */ }
  }

  dispose(): void { this.decorationType.dispose(); }
}
