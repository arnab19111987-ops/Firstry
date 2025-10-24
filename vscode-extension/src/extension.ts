import * as vscode from 'vscode'

// Simple sample activate/deactivate for the extension skeleton.
export function activate(context: vscode.ExtensionContext) {
  const disposable = vscode.commands.registerCommand('firsttry.hello', () => {
    vscode.window.showInformationMessage('FirstTry says hello!')
  })
  context.subscriptions.push(disposable)
}

export function deactivate() {
  // noop
}
