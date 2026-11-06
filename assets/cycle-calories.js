// Cycle calorie calculator: same math as the Pofu app (QuizPlanCalculator, CycleIntelligence).
// Mifflin-St Jeor (female), activity multiplier, goal delta, 1200 kcal floor, 4200 cap,
// luteal allowance = 5% of target clipped to 80–150 kcal, protein 1.6 g/kg when losing else 1.4 (75–230 g).
// Phases follow the app: days 1–5 menstrual, ovulation = cycle length − 14 (3 days), luteal after.
// It never predicts a future period: it only places today in the cycle from a past start date.
(function (root) {
  var ACTIVITY = { sedentary: 1.2, light: 1.375, moderate: 1.55, active: 1.725, very_active: 1.9 };
  var GOAL = { maintain: 0, lose_slow: -250, lose: -400, lose_fast: -550 };
  var FLOOR = 1200, CAP = 4200;

  function dayDiff(fromISO, toISO) {
    function utc(s) { var p = s.split('-'); return Date.UTC(+p[0], +p[1] - 1, +p[2]); }
    return Math.round((utc(toISO) - utc(fromISO)) / 86400000);
  }

  function phaseFor(day, len) {
    var ov = Math.max(len - 14, 21 - 14);
    if (day <= 5) return 'menstrual';
    if (day < ov) return 'follicular';
    if (day <= ov + 2) return 'ovulation';
    if (day <= len + 7) return 'luteal';
    return 'unknown';
  }

  function lutealAllowance(target) { return Math.round(Math.min(Math.max(target * 0.05, 80), 150)); }

  // input: { age, heightCm, weightKg, activity, goal, lastStart?, cycleLength?, today? }
  function calc(input) {
    var age = +input.age, h = +input.heightCm, w = +input.weightKg;
    if (!(age >= 18 && age <= 80)) return { error: 'age' };
    if (!(h >= 130 && h <= 210)) return { error: 'height' };
    if (!(w >= 35 && w <= 250)) return { error: 'weight' };
    if (!(input.activity in ACTIVITY)) return { error: 'activity' };
    if (!(input.goal in GOAL)) return { error: 'goal' };
    var bmr = 10 * w + 6.25 * h - 5 * age - 161;
    var tdee = bmr * ACTIVITY[input.activity];
    var raw = tdee + GOAL[input.goal];
    var target = Math.round(Math.min(Math.max(raw, FLOOR), CAP));
    var allowance = lutealAllowance(target);
    var out = {
      bmr: Math.round(bmr), tdee: Math.round(tdee), target: target, floorApplied: raw < FLOOR,
      allowance: allowance, lutealTarget: target + allowance,
      proteinG: Math.round(Math.min(Math.max(w * (GOAL[input.goal] < 0 ? 1.6 : 1.4), 75), 230))
    };
    if (input.lastStart) {
      var len = Math.round(+input.cycleLength);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(input.lastStart)) return { error: 'date' };
      if (!(len >= 21 && len <= 40)) return { error: 'length' };
      var day = dayDiff(input.lastStart, input.today) + 1;
      if (day < 1) return { error: 'future' };
      out.cycleDay = day;
      out.phase = phaseFor(day, len);
      out.todayTarget = out.phase === 'luteal' ? out.lutealTarget : target;
    }
    return out;
  }

  var api = { calc: calc, phaseFor: phaseFor, lutealAllowance: lutealAllowance, dayDiff: dayDiff };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CycleCalories = api;
})(this);
