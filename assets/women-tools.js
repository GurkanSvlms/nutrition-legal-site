// Protein, BMI and goal-date calculators. Same rules as the Pofu app (QuizPlanCalculator):
// protein 1.4 g/kg (maintain), 1.6 (lose), 1.8 (build muscle), kept within 75–230 g;
// 7,700 kcal ≈ 1 kg; fastest pace −550 kcal a day; never below 1,200 kcal.
(function (root) {
  var FACTOR = { maintain: 1.4, lose: 1.6, muscle: 1.8 };
  var KCAL_PER_KG = 7700, MAX_DEFICIT = 550, FLOOR = 1200;
  function r1(x) { return Math.round(x * 10) / 10; }

  function protein(input) {
    var w = +input.weightKg;
    if (!(w >= 35 && w <= 250)) return { error: 'weight' };
    if (!(input.goal in FACTOR)) return { error: 'goal' };
    var g = Math.round(Math.min(Math.max(w * FACTOR[input.goal], 75), 230));
    return { g: g, factor: FACTOR[input.goal], perMeal3: Math.round(g / 3), perMeal4: Math.round(g / 4),
             low: Math.round(w * 1.2), high: Math.round(w * 2.0) };
  }

  function bmi(input) {
    var h = +input.heightCm / 100, w = +input.weightKg;
    if (!(h >= 1.3 && h <= 2.1)) return { error: 'height' };
    if (!(w >= 30 && w <= 250)) return { error: 'weight' };
    var b = w / (h * h);
    var cat = b < 18.5 ? 'under' : b < 25 ? 'normal' : b < 30 ? 'over' : 'obese';
    return { bmi: r1(b), cat: cat, lowKg: r1(18.5 * h * h), highKg: r1(24.9 * h * h) };
  }

  // input: { tdee, weightKg, goalKg, days, heightCm }
  function goalPlan(input) {
    var tdee = +input.tdee, w = +input.weightKg, g = +input.goalKg, days = Math.round(+input.days), h = +input.heightCm / 100;
    if (!(g >= 30 && g < w)) return { error: 'goalkg' };
    if (!(days >= 1 && days <= 1100)) return { error: 'date' };
    var room = Math.min(MAX_DEFICIT, tdee - FLOOR);
    if (room < 50) return { error: 'nodeficit' };
    var need = Math.round((w - g) * KCAL_PER_KG / days);
    var out = { deficit: need, target: Math.round(tdee - need), feasible: need <= room,
                weeklyKg: r1(need * 7 / KCAL_PER_KG), lowGoal: h > 0 && g / (h * h) < 18.5 };
    if (!out.feasible) {
      out.safeDeficit = Math.round(room);
      out.safeTarget = Math.round(tdee - room);
      out.safeDays = Math.ceil((w - g) * KCAL_PER_KG / room);
    }
    return out;
  }

  var api = { protein: protein, bmi: bmi, goalPlan: goalPlan };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.WomenTools = api;
})(this);
