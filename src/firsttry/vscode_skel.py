from __future__ import annotations

PACKAGE_JSON = r"""{
  "name": "firsttry-helper",
  "displayName": "FirstTry Helper",
  "description": "Run FirstTry gates (pre-commit / pre-push) right from VS Code.",
  "version": "0.0.1",
  "publisher": "firsttry",
  "engines": {
    "vscode": "^1.80.0"
  },
  "activationEvents": [
    "onCommand:firsttry.runGate"
  ],
  "contributes": {
    "commands": [
      {
        "command": "firsttry.runGate",
        "title": "FirstTry: Run Gate"
      }
    ]
  },
  "main": "./extension.js"
}
"""

EXTENSION_JS = r"""// VS Code integration for FirstTry.
// We effectively run: python -m firsttry run --gate <gate>

const vscode = require('vscode');
const cp = require('child_process');

function activate(context) {
    let disposable = vscode.commands.registerCommand(
        'firsttry.runGate',
        async function () {
            const choice = await vscode.window.showQuickPick(
                ['pre-commit', 'pre-push'],
                { placeHolder: 'Run which FirstTry gate?' }
            );
            if (!choice) {
                return;
            }

            // Equivalent shell command:
            //   python -m firsttry run --gate <choice>
            try {
                const result = cp.spawnSync(
                    'python',
                    ['-m', 'firsttry', 'run', '--gate', choice],
                    { encoding: 'utf-8' }
                );

                vscode.window.showInformationMessage(
                    result.stdout || '(no output)'
                );

                if (result.status !== 0) {
                    vscode.window.showErrorMessage(
                        'Gate reported BLOCKED ❌. Check output.'
                    );
                }
            } catch (err) {
                vscode.window.showErrorMessage(
                    'Failed to execute FirstTry gate: ' + err
                );
            }
        }
    );

    context.subscriptions.push(disposable);
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};
"""
