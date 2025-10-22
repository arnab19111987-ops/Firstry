import * as vscode from 'vscode'

export function activate(context: vscode.ExtensionContext) {
  const disposable = vscode.commands.registerCommand('firsttry.hello', () => {
    vscode.window.showInformationMessage('Hello from firsttry!')
  })
  context.subscriptions.push(disposable)
}

export function deactivate() {
  // no-op
}
import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext) {
  const disposable = vscode.commands.registerCommand("firsttry.hello", () => {
    vscode.window.showInformationMessage("FirstTry says hello!");
  });
  context.subscriptions.push(disposable);
}

export function deactivate() {
  // noop
}
