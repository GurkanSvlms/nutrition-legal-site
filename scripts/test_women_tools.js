// Run: node scripts/test_women_tools.js
const assert = require('assert');
const { calc } = require('../assets/cycle-calories.js');
const { protein, bmi, goalPlan } = require('../assets/women-tools.js');

// Macros come from calc(): fat 28% (min 40 g), carbs the rest (min 50 g), like the app
const base = { age: 30, heightCm: 165, weightKg: 65, activity: 'moderate', goal: 'lose' };
const r = calc(base); // target 1724, protein 104
assert.strictEqual(r.fatG, 54);           // 1724*0.28/9 = 53.6
assert.strictEqual(r.carbsG, 206);        // (1724 - 416 - 482.7)/4 = 206.3
const m = calc({ ...base, goal: 'muscle' });
assert.strictEqual(m.target, 2349);       // 2123.9 + 225
assert.strictEqual(m.proteinG, 117);      // 65 * 1.8

// Protein: app factors, clamp 75–230 g, per meal split
assert.deepStrictEqual(protein({ weightKg: 65, goal: 'lose' }), { g: 104, factor: 1.6, perMeal3: 35, perMeal4: 26, low: 78, high: 130 });
assert.strictEqual(protein({ weightKg: 65, goal: 'maintain' }).g, 91);
assert.strictEqual(protein({ weightKg: 65, goal: 'muscle' }).g, 117);
assert.strictEqual(protein({ weightKg: 45, goal: 'maintain' }).g, 75);   // floor
assert.strictEqual(protein({ weightKg: 140, goal: 'muscle' }).g, 230);   // cap
assert.deepStrictEqual(protein({ weightKg: 20, goal: 'lose' }), { error: 'weight' });
assert.deepStrictEqual(protein({ weightKg: 65, goal: 'x' }), { error: 'goal' });

// BMI: WHO adult categories, healthy range for height
assert.deepStrictEqual(bmi({ heightCm: 165, weightKg: 65 }), { bmi: 23.9, cat: 'normal', lowKg: 50.4, highKg: 67.8 });
assert.strictEqual(bmi({ heightCm: 165, weightKg: 50 }).cat, 'under');
assert.strictEqual(bmi({ heightCm: 165, weightKg: 70 }).cat, 'over');
assert.strictEqual(bmi({ heightCm: 165, weightKg: 82 }).cat, 'obese');
assert.deepStrictEqual(bmi({ heightCm: 100, weightKg: 65 }), { error: 'height' });

// Goal date: 7700 kcal per kg, max deficit 550 a day (the app's fastest pace), 1200 kcal floor
const p = goalPlan({ tdee: 2124, weightKg: 65, goalKg: 60, days: 70, heightCm: 165 }); // 5 kg in 10 weeks
assert.strictEqual(p.deficit, 550);       // 5*7700/70 = 550
assert.strictEqual(p.target, 1574);
assert.strictEqual(p.feasible, true);
assert.strictEqual(p.weeklyKg, 0.5);
const fast = goalPlan({ tdee: 2124, weightKg: 65, goalKg: 60, days: 30, heightCm: 165 });
assert.strictEqual(fast.feasible, false);
assert.strictEqual(fast.deficit, 1283);
assert.strictEqual(fast.safeDeficit, 550);
assert.strictEqual(fast.safeDays, 70);
const low = goalPlan({ tdee: 1500, weightKg: 55, goalKg: 52, days: 200, heightCm: 160 }); // floor limits deficit to 300
assert.strictEqual(low.feasible, true);
assert.strictEqual(low.deficit, 116);
const lowFast = goalPlan({ tdee: 1500, weightKg: 55, goalKg: 52, days: 30, heightCm: 160 });
assert.strictEqual(lowFast.safeDeficit, 300);
assert.strictEqual(lowFast.safeDays, 77);
assert.strictEqual(goalPlan({ tdee: 2124, weightKg: 65, goalKg: 48, days: 400, heightCm: 165 }).lowGoal, true); // BMI 17.6
assert.deepStrictEqual(goalPlan({ tdee: 2124, weightKg: 65, goalKg: 66, days: 70, heightCm: 165 }), { error: 'goalkg' });
assert.deepStrictEqual(goalPlan({ tdee: 2124, weightKg: 65, goalKg: 60, days: 0, heightCm: 165 }), { error: 'date' });
assert.deepStrictEqual(goalPlan({ tdee: 1230, weightKg: 50, goalKg: 48, days: 90, heightCm: 160 }), { error: 'nodeficit' });

console.log('women-tools: all tests passed');
