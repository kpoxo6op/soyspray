const DAY = 86400000;

export function dateInstant(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) throw new Error('Проверьте дату.');
  const instant = Date.parse(value + 'T00:00:00Z');
  if (!Number.isFinite(instant) || new Date(instant).toISOString().slice(0, 10) !== value) throw new Error('Проверьте дату.');
  return instant;
}

export function dayCount(arrival, departure) {
  return (dateInstant(departure) - dateInstant(arrival)) / DAY;
}

export function fullDays(arrival, departure) {
  const nights = dayCount(arrival, departure);
  return {
    nights, count: Math.max(0, nights - 1),
    first: nights > 1 ? new Date(dateInstant(arrival) + DAY).toISOString().slice(0, 10) : null,
    last: nights > 1 ? new Date(dateInstant(departure) - DAY).toISOString().slice(0, 10) : null,
  };
}

export function dateText(value, weekday = true) {
  if (!value) return 'Не указано';
  return new Intl.DateTimeFormat('ru-RU', {
    weekday: weekday ? 'long' : undefined, day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
  }).format(dateInstant(value));
}

export function parseMoney(value) {
  const input = value.trim();
  if (!input) return null;
  const match = /^(\d{1,7})(?:[.,](\d{1,2}))?$/.exec(input);
  if (!match) throw new Error('Укажите сумму в AUD с точностью до цента.');
  const cents = Number(match[1]) * 100 + Number((match[2] || '').padEnd(2, '0'));
  if (cents > 100000000) throw new Error('Проверьте сумму.');
  return cents;
}

export function money(value) {
  if (value == null) return 'Неизвестно';
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'AUD', currencyDisplay: 'code' }).format(value / 100);
}

export function budgetText(value) {
  if (value.min_cents == null && value.max_cents == null) return 'Не указан';
  if (value.min_cents == null) return 'до ' + money(value.max_cents);
  if (value.max_cents == null) return 'от ' + money(value.min_cents);
  return value.min_cents === value.max_cents ? money(value.min_cents) : `${money(value.min_cents)} — ${money(value.max_cents)}`;
}

export function perPerson(total, paying) {
  return total == null || paying == null || paying < 1 ? null : Math.round(total / paying);
}

export function localTime(instant, zone) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(instant));
  const get = (name) => parts.find((part) => part.type === name).value;
  return `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}:${get('second')}`;
}

export function localInstants(value, zone) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) throw new Error('Укажите дату и время.');
  const wall = Date.parse(value + ':00Z');
  if (!Number.isFinite(wall) || new Date(wall).toISOString().slice(0, 16) !== value) throw new Error('Проверьте дату и время.');
  // Offsets on either side include both occurrences of a repeated local time.
  const offsets = new Set([-DAY, 0, DAY].map((delta) => Date.parse(localTime(wall + delta, zone) + 'Z') - (wall + delta)));
  const candidates = [...offsets].map((offset) => wall - offset)
    .filter((instant) => localTime(instant, zone).slice(0, 16) === value).sort((a, b) => a - b);
  if (!candidates.length) throw new Error('Такого времени нет из-за перевода часов. Выберите другое время.');
  return candidates.map((instant) => new Date(instant).toISOString());
}

export function callTimes(call) {
  if (!call.at) return [];
  return [['Окленд', 'Pacific/Auckland'], ['Брисбен', 'Australia/Brisbane']].map(([name, timeZone]) =>
    `${name}: ${new Intl.DateTimeFormat('ru-RU', { timeZone, weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(call.at))}`);
}

export function equal(first, second) {
  if (first === second) return true;
  if (first == null || second == null || typeof first !== 'object' || typeof second !== 'object') return false;
  if (Array.isArray(first) !== Array.isArray(second)) return false;
  const a = Object.keys(first).sort();
  const b = Object.keys(second).sort();
  return a.length === b.length && a.every((key, index) => key === b[index] && equal(first[key], second[key]));
}
