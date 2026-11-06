// Run: node scripts/test_period_water.js
const assert = require('assert');
const { assess, phaseFor, dayDiff } = require('../assets/period-water.js');

const base = { today: '2026-11-06', cycleLength: 28, unit: 'kg' };
const at = (lastStart, change, extra = {}) => assess({ ...base, lastStart, change, ...extra });

assert.strictEqual(dayDiff('2026-10-31', '2026-11-06'), 6);
assert.strictEqual(dayDiff('2026-03-28', '2026-03-30'), 2); // across a DST change
assert.strictEqual(phaseFor(1, 28), 'menstrual');
assert.strictEqual(phaseFor(6, 28), 'follicular');
assert.strictEqual(phaseFor(14, 28), 'follicular');
assert.strictEqual(phaseFor(15, 28), 'early_luteal');
assert.strictEqual(phaseFor(22, 28), 'late_luteal');
assert.strictEqual(phaseFor(35, 28), 'late_luteal');
assert.strictEqual(phaseFor(36, 28), 'unknown');

assert.deepStrictEqual(at('2026-11-06', 1.2), { cycleDay: 1, phase: 'menstrual', kg: 1.2, result: 'likely_water' });
assert.strictEqual(at('2026-10-12', 1.5).result, 'likely_water'); // day 26, late luteal
assert.strictEqual(at('2026-10-12', 3).result, 'more_than_water');
assert.strictEqual(at('2026-10-12', 5, { unit: 'lb' }).result, 'likely_water'); // 5 lb ≈ 2.27 kg
assert.strictEqual(at('2026-10-12', 6, { unit: 'lb' }).result, 'more_than_water');
assert.strictEqual(at('2026-10-29', 0.6).result, 'normal_noise'); // day 9
assert.strictEqual(at('2026-10-29', 1.8).result, 'unlikely_cycle');
assert.strictEqual(at('2026-10-29', -0.5).result, 'no_gain');
assert.strictEqual(at('2026-09-20', 1).result, 'unknown_phase'); // day 48

assert.deepStrictEqual(at('2026-11-07', 1), { error: 'future' });
assert.deepStrictEqual(at('', 1), { error: 'date' });
assert.deepStrictEqual(at('2026-11-01', ''), { error: 'change' });
assert.deepStrictEqual(at('2026-11-01', 1, { cycleLength: 50 }), { error: 'length' });
assert.deepStrictEqual(at('2026-11-01', 12), { error: 'too_big' });

console.log('period-water: all tests passed');
