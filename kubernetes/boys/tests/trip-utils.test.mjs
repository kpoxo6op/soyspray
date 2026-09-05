import test from 'node:test';
import assert from 'node:assert/strict';
import { dateText, fullDays, parseMoney, perPerson, localInstants, localTime, equal } from '../app/trip-utils.mjs';

test('nights and shared days exclude arrival and departure', () => {
  assert.deepEqual(fullDays('2030-02-07', '2030-02-10'), { nights: 3, count: 2, first: '2030-02-08', last: '2030-02-09' });
  assert.equal(fullDays('2030-02-07', '2030-02-11').count, 3);
  assert.equal(fullDays('2030-02-07', '2030-02-08').count, 0);
  assert.match(dateText('2000-01-01'), /суббота.*2000/);
  assert.throws(() => fullDays('2030-02-31', '2030-03-02'));
});

test('money distinguishes unknown zero and integer cents', () => {
  assert.equal(parseMoney(''), null);
  assert.equal(parseMoney('0'), 0);
  assert.equal(parseMoney('123,45'), 12345);
  assert.equal(parseMoney('123.4'), 12340);
  for (const value of ['1e3', '-2', '1.234', 'NaN']) assert.throws(() => parseMoney(value));
  assert.equal(perPerson(123456, null), null);
  assert.equal(perPerson(null, 9), null);
  assert.equal(perPerson(123456, 9), 13717);
});

test('Auckland changes offset while Brisbane stays on UTC plus ten', () => {
  assert.deepEqual(localInstants('2030-01-15T19:00', 'Pacific/Auckland'), ['2030-01-15T06:00:00.000Z']);
  assert.deepEqual(localInstants('2030-07-15T19:00', 'Pacific/Auckland'), ['2030-07-15T07:00:00.000Z']);
  assert.equal(localTime('2030-01-15T06:00:00Z', 'Australia/Brisbane'), '2030-01-15T16:00:00');
  assert.equal(localTime('2030-07-15T07:00:00Z', 'Australia/Brisbane'), '2030-07-15T17:00:00');
});

test('clock changes reject nonexistent time and expose both repeated times', () => {
  assert.throws(() => localInstants('2030-09-29T02:30', 'Pacific/Auckland'));
  assert.deepEqual(localInstants('2030-04-07T02:30', 'Pacific/Auckland'), ['2030-04-06T13:30:00.000Z', '2030-04-06T14:30:00.000Z']);
});

test('document comparisons ignore object key order and retain array order', () => {
  assert.equal(equal({a: 1, b: [null, 0]}, {b: [null, 0], a: 1}), true);
  assert.equal(equal([1, 2], [2, 1]), false);
});
