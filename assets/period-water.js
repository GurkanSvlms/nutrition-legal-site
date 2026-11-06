// Period water weight check: pure logic shared by the EN and TR tool pages.
// Ranges: ~0.45 kg average rise during menstruation (PubMed 37395124);
// common guidance 1–5 lb (~0.5–2.3 kg); Cleveland Clinic suggests a doctor visit above 5 lb.
// It never predicts a future period: it only places today in the cycle from a past start date.
(function (root) {
  var LB_TO_KG = 0.45359237;
  var WATER_MAX_KG = 2.3; // ~5 lb
  var NOISE_MAX_KG = 1.0; // ordinary day-to-day swing (salt, carbs, digestion)

  function dayDiff(fromISO, toISO) {
    var a = Date.UTC.apply(null, fromISO.split('-').map(function (n, i) { return i === 1 ? n - 1 : +n; }));
    var b = Date.UTC.apply(null, toISO.split('-').map(function (n, i) { return i === 1 ? n - 1 : +n; }));
    return Math.round((b - a) / 86400000);
  }

  function phaseFor(cycleDay, cycleLength) {
    if (cycleDay <= 5) return 'menstrual';
    if (cycleDay <= cycleLength - 14) return 'follicular';
    if (cycleDay <= cycleLength - 7) return 'early_luteal';
    if (cycleDay <= cycleLength + 7) return 'late_luteal';
    return 'unknown';
  }

  // input: { lastStart: 'YYYY-MM-DD', today: 'YYYY-MM-DD', cycleLength: 21..40, change: number, unit: 'kg'|'lb' }
  function assess(input) {
    var len = Math.round(+input.cycleLength);
    var change = +input.change;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(input.lastStart || '')) return { error: 'date' };
    if (!(len >= 21 && len <= 40)) return { error: 'length' };
    if (!isFinite(change) || input.change === '' || input.change === null) return { error: 'change' };
    var cycleDay = dayDiff(input.lastStart, input.today) + 1;
    if (cycleDay < 1) return { error: 'future' };
    var kg = input.unit === 'lb' ? change * LB_TO_KG : change;
    if (Math.abs(kg) > 10) return { error: 'too_big' };
    var phase = phaseFor(cycleDay, len);
    var result;
    if (phase === 'unknown') result = 'unknown_phase';
    else if (kg <= 0) result = 'no_gain';
    else if (phase === 'menstrual' || phase === 'late_luteal') result = kg <= WATER_MAX_KG ? 'likely_water' : 'more_than_water';
    else result = kg <= NOISE_MAX_KG ? 'normal_noise' : 'unlikely_cycle';
    return { cycleDay: cycleDay, phase: phase, kg: Math.round(kg * 10) / 10, result: result };
  }

  var api = { assess: assess, phaseFor: phaseFor, dayDiff: dayDiff };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.PeriodWater = api;
})(this);
