import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  CapabilityProfileRegistry,
  createCapabilityProfileRegistry,
} from '../src/orchestrator/profiles/CapabilityProfileRegistry.js';
import { CapabilityRegistry, createCapabilityRegistry } from '../src/orchestrator/capabilities/CapabilityRegistry.js';

function makeLogger() {
  return { info() {}, debug() {}, warn() {}, error() {} } as any;
}

describe('CapabilityProfileRegistry', () => {
  it('registers and retrieves a profile', () => {
    const reg = new CapabilityProfileRegistry({ logger: makeLogger() });
    reg.register({
      name: 'test',
      description: 'Test profile',
      capabilities: { expressive: true },
    });

    const p = reg.get('test');
    assert.ok(p);
    assert.equal(p!.name, 'test');
    assert.equal(p!.capabilities.expressive, true);
  });

  it('lists all profiles', () => {
    const reg = new CapabilityProfileRegistry({ logger: makeLogger() });
    reg.register({ name: 'a', description: 'A', capabilities: {} });
    reg.register({ name: 'b', description: 'B', capabilities: {} });

    const list = reg.list();
    assert.equal(list.length, 2);
    assert.deepEqual(list.map((p) => p.name).sort(), ['a', 'b']);
  });

  it('returns undefined for unknown profile', () => {
    const reg = new CapabilityProfileRegistry({ logger: makeLogger() });
    assert.equal(reg.get('ghost'), undefined);
  });

  it('overwrites duplicate profile names', () => {
    const reg = new CapabilityProfileRegistry({ logger: makeLogger() });
    reg.register({ name: 'dup', description: 'First', capabilities: {} });
    reg.register({ name: 'dup', description: 'Second', capabilities: {} });

    assert.equal(reg.list().length, 1);
    assert.equal(reg.get('dup')!.description, 'Second');
  });
});

describe('Built-in profiles from createCapabilityProfileRegistry', () => {
  it('seeds expressive, silent, and diagnostic profiles', () => {
    const reg = createCapabilityProfileRegistry({ logger: makeLogger() });
    const names = reg.list().map((p) => p.name).sort();
    assert.deepEqual(names, ['diagnostic', 'expressive', 'silent']);
  });

  it('expressive profile enables both expressive and notifications', () => {
    const reg = createCapabilityProfileRegistry({ logger: makeLogger() });
    const p = reg.get('expressive')!;
    assert.equal(p.capabilities.expressive, true);
    assert.equal(p.capabilities.notifications, true);
  });

  it('silent profile disables both', () => {
    const reg = createCapabilityProfileRegistry({ logger: makeLogger() });
    const p = reg.get('silent')!;
    assert.equal(p.capabilities.expressive, false);
    assert.equal(p.capabilities.notifications, false);
  });

  it('diagnostic profile disables expressive, enables notifications', () => {
    const reg = createCapabilityProfileRegistry({ logger: makeLogger() });
    const p = reg.get('diagnostic')!;
    assert.equal(p.capabilities.expressive, false);
    assert.equal(p.capabilities.notifications, true);
  });
});

describe('Profile application to CapabilityRegistry', () => {
  it('applying silent profile disables matching capabilities', () => {
    const logger = makeLogger();
    const caps = createCapabilityRegistry({ logger });
    const profiles = createCapabilityProfileRegistry({ logger });

    assert.equal(caps.isEnabled('expressive'), true);
    assert.equal(caps.isEnabled('notifications'), true);

    const profile = profiles.get('silent')!;
    for (const [name, enabled] of Object.entries(profile.capabilities)) {
      caps.setEnabled(name, enabled);
    }

    assert.equal(caps.isEnabled('expressive'), false);
    assert.equal(caps.isEnabled('notifications'), false);
  });

  it('applying expressive profile re-enables capabilities', () => {
    const logger = makeLogger();
    const caps = createCapabilityRegistry({ logger });
    const profiles = createCapabilityProfileRegistry({ logger });

    caps.setEnabled('expressive', false);
    caps.setEnabled('notifications', false);

    const profile = profiles.get('expressive')!;
    for (const [name, enabled] of Object.entries(profile.capabilities)) {
      caps.setEnabled(name, enabled);
    }

    assert.equal(caps.isEnabled('expressive'), true);
    assert.equal(caps.isEnabled('notifications'), true);
  });

  it('applying diagnostic profile sets mixed state', () => {
    const logger = makeLogger();
    const caps = createCapabilityRegistry({ logger });
    const profiles = createCapabilityProfileRegistry({ logger });

    const profile = profiles.get('diagnostic')!;
    for (const [name, enabled] of Object.entries(profile.capabilities)) {
      caps.setEnabled(name, enabled);
    }

    assert.equal(caps.isEnabled('expressive'), false);
    assert.equal(caps.isEnabled('notifications'), true);
  });

  it('does not affect capabilities not listed in profile', () => {
    const logger = makeLogger();
    const caps = createCapabilityRegistry({ logger });
    const profiles = createCapabilityProfileRegistry({ logger });

    const riskBefore = caps.isEnabled('risk');

    const profile = profiles.get('silent')!;
    for (const [name, enabled] of Object.entries(profile.capabilities)) {
      caps.setEnabled(name, enabled);
    }

    assert.equal(caps.isEnabled('risk'), riskBefore);
  });
});
