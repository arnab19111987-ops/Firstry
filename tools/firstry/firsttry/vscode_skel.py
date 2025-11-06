"""VS Code extension skeleton for Day 6.
You will create a folder `vscode-extension/` with these two files:

1. package.json  (PACKAGE_JSON below)
2. extension.js  (EXTENSION_JS below)

Then in VS Code:
- Open that folder as part of your workspace (or as a multi-root).
- Press F5 to debug/run the extension.

The command "firsttry.runGate" will appear in the Command Palette.
When executed, it will create (or reuse) a terminal and run:
    python -m firsttry run
"""

import json

PACKAGE_JSON = json.dumps(
    {
        "name": "firsttry-gate",
        "displayName": "FirstTry Gate",
        "description": "Run FirstTry local gate (lint/tests/probes) from VS Code.",
        "version": "0.0.1",
        "publisher": "you",
        "engines": {"vscode": "^1.80.0"},
        "activationEvents": ["onCommand:firsttry.runGate"],
        "main": "./extension.js",
        "contributes": {
            "commands": [
                {
                    "command": "firsttry.runGate",
                    "title": "FirstTry: Run Gate",
                    "category": "FirstTry",
                },
            ],
        },
    },
    indent=2,
)

EXTENSION_JS = r"""
const vscode = require('vscode');

function activate(context) {
    const disposable = vscode.commands.registerCommand('firsttry.runGate', function () {
        // Create or reuse an integrated terminal, then run our gate
        const termName = "FirstTry Gate";
        let term = vscode.window.terminals.find(t => t.name === termName);
        if (!term) {
            term = vscode.window.createTerminal(termName);
        }
        term.show();
        term.sendText("python -m firsttry run");
    });

    context.subscriptions.push(disposable);
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};
"""
