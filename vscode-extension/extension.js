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
