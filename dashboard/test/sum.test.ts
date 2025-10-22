import { describe, it, expect } from 'vitest'
import { sum } from '../src/sum'

describe('sum', () => {
  it('adds numbers', () => {
    expect(sum(1, 2)).toBe(3)
  })
})
import { describe, it, expect } from "vitest";
import { sum } from "../src/sum";

describe("sum", () => {
  it("adds numbers", () => {
    expect(sum(2, 3)).toBe(5);
  });
});
