// vscode-extension/src/extension.ts
import * as vscode from "vscode";
import { exec } from "child_process";

function runFirstTryDoctor(): void {
  const channel = vscode.window.createOutputChannel("FirstTry Doctor");
  channel.show(true);
  channel.appendLine("[FirstTry] Running health scan...");

  // We call `firsttry doctor`. If 'firsttry' isn't on PATH,
  // users can alias 'python -m firsttry.cli'.
  const cmd = "firsttry doctor || python -m firsttry.cli doctor";

  const workspaceRoot = vscode.workspace.workspaceFolders
    ? vscode.workspace.workspaceFolders[0].uri.fsPath
    : undefined;

  exec(cmd, { cwd: workspaceRoot }, (err, stdout, stderr) => {
    if (stdout && stdout.length > 0) {
      channel.appendLine(stdout);
    }
    if (stderr && stderr.length > 0) {
      channel.appendLine(stderr);
    }
    if (err) {
      channel.appendLine(
        "[FirstTry] ❌ Doctor reported failures or could not run."
      );
    } else {
      channel.appendLine("[FirstTry] ✅ Doctor completed.");
    }
  });
}

export function activate(context: vscode.ExtensionContext) {
  const disposable = vscode.commands.registerCommand(
    "firsttry.runDoctor",
    () => {
      runFirstTryDoctor();
    }
  );

  context.subscriptions.push(disposable);
}

export function deactivate() {
  // no-op
}
