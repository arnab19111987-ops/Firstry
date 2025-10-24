import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the VS Code API surface we use
vi.mock('vscode', () => {
  const registered: Array<{ command: string; cb: Function }> = []
  return {
    window: {
      showInformationMessage: vi.fn((msg: string) => msg),
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

import * as vscode from 'vscode' // resolved to our mock above
import { activate, deactivate } from '../src/extension.js'

describe('FirstTry VS Code extension', () => {
  beforeEach(() => {
    // clean any previous registrations if you run watch mode later
    ;(vscode as any).__internal.getRegistered().length = 0
  })

  it('registers the hello command on activate', () => {
    const context = { subscriptions: [] } as unknown as import('vscode').ExtensionContext
    activate(context)
    const regs = (vscode as any).__internal.getRegistered()
    expect(regs.some((r: any) => r.command === 'firsttry.hello')).toBe(true)
    expect(context.subscriptions.length).toBeGreaterThan(0)
  })

  it('deactivate does not throw', () => {
    expect(() => deactivate()).not.toThrow()
  })
})
