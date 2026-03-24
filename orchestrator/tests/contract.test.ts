import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { DaedalusContractV04 } from '../../shared/contracts/daedalus.contract.js';

describe('DaedalusContractV04', () => {
  it('has version 0.4', () => {
    assert.equal(DaedalusContractV04.version, '0.4');
  });

  it('tracks all surface versions', () => {
    const surfaces = DaedalusContractV04.surfaces;
    assert.ok(surfaces.presence);
    assert.ok(surfaces.capabilities);
    assert.ok(surfaces.expressive);
    assert.ok(surfaces.continuity);
    assert.ok(surfaces.risk);
    assert.ok(surfaces.verification);
    assert.ok(surfaces.notifications);
  });

  it('marks v0.4 surfaces correctly', () => {
    assert.equal(DaedalusContractV04.surfaces.capabilities, 'v0.4');
    assert.equal(DaedalusContractV04.surfaces.expressive, 'v0.4');
    assert.equal(DaedalusContractV04.surfaces.notifications, 'v0.4');
  });

  it('preserves v0.3 surface versions', () => {
    assert.equal(DaedalusContractV04.surfaces.presence, 'v0.3');
    assert.equal(DaedalusContractV04.surfaces.risk, 'v0.3');
    assert.equal(DaedalusContractV04.surfaces.verification, 'v0.3');
    assert.equal(DaedalusContractV04.surfaces.continuity, 'v0.3');
  });

  it('enforces all invariants as true', () => {
    assert.equal(DaedalusContractV04.invariants.operatorSovereignty, true);
    assert.equal(DaedalusContractV04.invariants.explicitOverride, true);
    assert.equal(DaedalusContractV04.invariants.trustBoundaries, true);
    assert.equal(DaedalusContractV04.invariants.expressiveDiscipline, true);
  });
});
