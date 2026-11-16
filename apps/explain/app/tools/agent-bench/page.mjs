#!/usr/bin/env node
// The agent's one tool: node page.mjs <port> <command> [args...]. Prints what the page answered.
const [port, cmd, ...args] = process.argv.slice(2);
const res = await fetch(`http://127.0.0.1:${port}/`, { method: 'POST', body: JSON.stringify({ cmd, args }) });
process.stdout.write((await res.text()) + '\n');
