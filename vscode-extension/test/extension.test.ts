import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the VS Code API surface we use
vi.mock('vscode', () => {
  const registered: Array<{ command: string; cb: Function }> = []
  return {
    window: {
      createOutputChannel: vi.fn(() => ({
        appendLine: vi.fn(),
        show: vi.fn(),
      })),
    },
    workspace: {
      workspaceFolders: [],
    },
    commands: {
      registerCommand: vi.fn((command: string, cb: Function) => {
        registered.push({ command, cb })
        return { dispose: () => void 0 }
      }),
    },
    // helper for assertions
    __internal: {
      getRegistered: () => registered,
    },
  }
})

// Mock child_process
vi.mock('child_process', () => ({
  exec: vi.fn((_cmd: string, _opts: any, cb: any) => {
    cb(null, '# FirstTry Doctor Report\nHealth: OK\n', '')
  }),
}))

import * as vscode from 'vscode' // resolved to our mock above
import { activate, deactivate } from '../src/extension.js'

describe('FirstTry VS Code extension', () => {
  beforeEach(() => {
    // clean any previous registrations if you run watch mode later
    ;(vscode as any).__internal.getRegistered().length = 0
  })

  it('registers the runDoctor command on activate', () => {
    const context = { subscriptions: [] } as unknown as import('vscode').ExtensionContext
    activate(context)
    const regs = (vscode as any).__internal.getRegistered()
    expect(regs.some((r: any) => r.command === 'firsttry.runDoctor')).toBe(true)
    expect(context.subscriptions.length).toBeGreaterThan(0)
  })

  it('deactivate does not throw', () => {
    expect(() => deactivate()).not.toThrow()
  })
})
