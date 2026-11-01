import { spawnSync } from 'node:child_process';
import { readdirSync } from 'node:fs';
const files = readdirSync('test').filter((f) => f.endsWith('.test.mjs')).map((f) => `test/${f}`);
const result = spawnSync(process.execPath, ['--test', ...files], { stdio: 'inherit' });
process.exit(result.status ?? 1);
