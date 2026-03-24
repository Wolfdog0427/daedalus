export interface ITestClock {
  now(): number;
  advance(ms: number): void;
  reset(epoch?: number): void;
}

export class TestClock implements ITestClock {
  private _now: number;

  constructor(epoch: number = 0) {
    this._now = epoch;
  }

  now(): number {
    return this._now;
  }

  advance(ms: number): void {
    if (ms < 0) {
      throw new Error(`TestClock.advance: cannot advance by negative ms: ${ms}`);
    }
    this._now += ms;
  }

  reset(epoch: number = 0): void {
    this._now = epoch;
  }
}
