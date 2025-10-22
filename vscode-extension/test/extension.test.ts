import { describe, it, expect, vi } from 'vitest'

// Mock the vscode module
vi.mock('vscode', () => {
  const window = { showInformationMessage: vi.fn() }
  const commands = { registerCommand: vi.fn((name, cb) => ({ dispose: vi.fn() })) }
  return {
    window,
    commands,
    ExtensionContext: class {},
  }
})

describe('extension.activate', () => {
  it('registers firsttry.hello', async () => {
    const vscode = await import('vscode')
    const ext = await import('../src/extension')
    const ctx = new vscode.ExtensionContext()
    ext.activate(ctx as any)
    expect(vscode.commands.registerCommand).toHaveBeenCalled()
  })

  it('deactivate does not throw', () => {
    const ext = require('../src/extension')
    expect(() => ext.deactivate()).not.toThrow()
  })
})
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("vscode", () => {
  const registered: Array<{ command: string; cb: Function }> = [];
  return {
    window: { showInformationMessage: vi.fn((msg: string) => msg) },
    commands: {
      registerCommand: vi.fn((command: string, cb: Function) => {
        registered.push({ command, cb });
        return { dispose: () => void 0 };
      })
    },
    __internal: { getRegistered: () => registered }
  };
});

import * as vscode from "vscode";
import { activate, deactivate } from "../src/extension";

describe("FirstTry VS Code extension", () => {
  beforeEach(() => {
    (vscode as any).__internal.getRegistered().length = 0;
  });

  it("registers the hello command on activate", () => {
    const context = { subscriptions: [] } as unknown as import("vscode").ExtensionContext;
    activate(context);
    const regs = (vscode as any).__internal.getRegistered();
    expect(regs.some((r: any) => r.command === "firsttry.hello")).toBe(true);
    expect(context.subscriptions.length).toBeGreaterThan(0);
  });

  it("deactivate does not throw", () => {
    expect(() => deactivate()).not.toThrow();
  });
});
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock the VS Code API surface we use
vi.mock("vscode", () => {
  const registered: Array<{ command: string; cb: Function }> = [];
  return {
    window: {
      showInformationMessage: vi.fn((msg: string) => msg),
    },
    commands: {
      registerCommand: vi.fn((command: string, cb: Function) => {
        registered.push({ command, cb });
        return { dispose: () => void 0 };
      }),
    },
    // helper for assertions
    __internal: {
      getRegistered: () => registered,
    },
  };
});

import * as vscode from "vscode"; // resolved to our mock above
import { activate, deactivate } from "../src/extension";

describe("FirstTry VS Code extension", () => {
  beforeEach(() => {
    // clean any previous registrations if you run watch mode later
    (vscode as any).__internal.getRegistered().length = 0;
  });

  it("registers the hello command on activate", () => {
    const context = { subscriptions: [] } as unknown as import("vscode").ExtensionContext;
    activate(context);
    const regs = (vscode as any).__internal.getRegistered();
    expect(regs.some((r: any) => r.command === "firsttry.hello")).toBe(true);
    expect(context.subscriptions.length).toBeGreaterThan(0);
  });

  it("deactivate does not throw", () => {
    expect(() => deactivate()).not.toThrow();
  });
});
