import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { CapabilityRegistry } from '../src/orchestrator/capabilities/CapabilityRegistry.js';

function makeDeps() {
  return { logger: { info() {}, debug() {}, warn() {}, error() {} } } as any;
}

describe('CapabilityRegistry', () => {
  it('registers and lists capabilities', () => {
    const reg = new CapabilityRegistry(makeDeps());
    reg.register({ name: 'echo', description: 'Echo command', enabled: true });
    reg.register({ name: 'shard', description: 'Shard management', enabled: false });

    assert.equal(reg.list().length, 2);
  });

  it('retrieves a capability by name', () => {
    const reg = new CapabilityRegistry(makeDeps());
    reg.register({ name: 'echo', description: 'Echo', enabled: true });

    const cap = reg.get('echo');
    assert.ok(cap);
    assert.equal(cap!.name, 'echo');
  });

  it('enables and disables capabilities', () => {
    const reg = new CapabilityRegistry(makeDeps());
    reg.register({ name: 'test', description: 'Test', enabled: false });

    reg.enable('test');
    assert.equal(reg.get('test')!.enabled, true);

    reg.disable('test');
    assert.equal(reg.get('test')!.enabled, false);
  });

  it('lists only enabled capabilities', () => {
    const reg = new CapabilityRegistry(makeDeps());
    reg.register({ name: 'a', description: 'A', enabled: true });
    reg.register({ name: 'b', description: 'B', enabled: false });
    reg.register({ name: 'c', description: 'C', enabled: true });

    assert.equal(reg.listEnabled().length, 2);
  });

  it('unregisters a capability', () => {
    const reg = new CapabilityRegistry(makeDeps());
    reg.register({ name: 'temp', description: 'Temporary', enabled: true });
    reg.unregister('temp');

    assert.equal(reg.get('temp'), undefined);
    assert.equal(reg.list().length, 0);
  });

  it('returns undefined for unknown capability', () => {
    const reg = new CapabilityRegistry(makeDeps());
    assert.equal(reg.get('nonexistent'), undefined);
  });

  it('overwrites duplicate registrations with latest', () => {
    const reg = new CapabilityRegistry(makeDeps());
    reg.register({ name: 'dup', description: 'First', enabled: true });
    reg.register({ name: 'dup', description: 'Second', enabled: false });

    assert.equal(reg.list().length, 1);
    assert.equal(reg.get('dup')!.description, 'Second');
    assert.equal(reg.get('dup')!.enabled, false);
  });

  it('isEnabled returns true for enabled capability', () => {
    const reg = new CapabilityRegistry(makeDeps());
    reg.register({ name: 'active', description: 'Active', enabled: true });
    assert.equal(reg.isEnabled('active'), true);
  });

  it('isEnabled returns false for disabled capability', () => {
    const reg = new CapabilityRegistry(makeDeps());
    reg.register({ name: 'off', description: 'Off', enabled: false });
    assert.equal(reg.isEnabled('off'), false);
  });

  it('isEnabled returns false for unknown capability', () => {
    const reg = new CapabilityRegistry(makeDeps());
    assert.equal(reg.isEnabled('ghost'), false);
  });

  it('setEnabled toggles and returns updated definition', () => {
    const reg = new CapabilityRegistry(makeDeps());
    reg.register({ name: 'toggle', description: 'Toggle', enabled: true });

    const result = reg.setEnabled('toggle', false);
    assert.ok(result);
    assert.equal(result!.enabled, false);
    assert.equal(reg.isEnabled('toggle'), false);
  });

  it('setEnabled returns undefined for unknown capability', () => {
    const reg = new CapabilityRegistry(makeDeps());
    assert.equal(reg.setEnabled('missing', true), undefined);
  });
});
