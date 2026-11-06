// Run: node scripts/test_cycle_calories.js
const assert = require('assert');
const { calc, phaseFor, lutealAllowance } = require('../assets/cycle-calories.js');

const base = { age: 30, heightCm: 165, weightKg: 65, activity: 'moderate', goal: 'lose' };

// BMR = 10*65 + 6.25*165 - 5*30 - 161 = 1370.25; TDEE = 2123.9; target = 1723.9 -> 1724
const r = calc(base);
assert.strictEqual(r.bmr, 1370);
assert.strictEqual(r.tdee, 2124);
assert.strictEqual(r.target, 1724);
assert.strictEqual(r.allowance, 86); // 5% of 1724 = 86.2
assert.strictEqual(r.lutealTarget, 1810);
assert.strictEqual(r.proteinG, 104); // 65 * 1.6
assert.strictEqual(r.floorApplied, false);

assert.strictEqual(calc({ ...base, goal: 'maintain' }).proteinG, 91); // 65 * 1.4
assert.strictEqual(lutealAllowance(1200), 80);
assert.strictEqual(lutealAllowance(4000), 150);

const small = calc({ ...base, age: 60, heightCm: 150, weightKg: 48, activity: 'sedentary', goal: 'lose_fast' });
assert.strictEqual(small.target, 1200);
assert.strictEqual(small.floorApplied, true);
assert.strictEqual(small.proteinG, 77); // 48 * 1.6 = 76.8

// Phases match the app: ovulation = len - 14, 3 days
assert.strictEqual(phaseFor(5, 28), 'menstrual');
assert.strictEqual(phaseFor(13, 28), 'follicular');
assert.strictEqual(phaseFor(14, 28), 'ovulation');
assert.strictEqual(phaseFor(16, 28), 'ovulation');
assert.strictEqual(phaseFor(17, 28), 'luteal');
assert.strictEqual(phaseFor(35, 28), 'luteal');
assert.strictEqual(phaseFor(36, 28), 'unknown');
assert.strictEqual(phaseFor(7, 21), 'ovulation'); // ovulation day = max(21 - 14, 7) = 7
assert.strictEqual(phaseFor(10, 21), 'luteal');

// Today's target uses the luteal allowance only in the luteal phase
const at = (lastStart) => calc({ ...base, lastStart, cycleLength: 28, today: '2026-11-06' });
assert.strictEqual(at('2026-10-12').phase, 'luteal'); // day 26
assert.strictEqual(at('2026-10-12').todayTarget, 1810);
assert.strictEqual(at('2026-10-29').phase, 'follicular'); // day 9
assert.strictEqual(at('2026-10-29').todayTarget, 1724);
assert.strictEqual(at('2026-09-20').phase, 'unknown'); // day 48

// Validation
assert.deepStrictEqual(calc({ ...base, age: 15 }), { error: 'age' });
assert.deepStrictEqual(calc({ ...base, heightCm: 300 }), { error: 'height' });
assert.deepStrictEqual(calc({ ...base, weightKg: 20 }), { error: 'weight' });
assert.deepStrictEqual(calc({ ...base, activity: 'x' }), { error: 'activity' });
assert.deepStrictEqual(at('2026-11-07'), { error: 'future' });
assert.deepStrictEqual(calc({ ...base, lastStart: '2026-11-01', cycleLength: 50, today: '2026-11-06' }), { error: 'length' });

console.log('cycle-calories: all tests passed');
