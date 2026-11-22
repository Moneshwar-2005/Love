const { spawnSync } = require('child_process');
const path = require('path');

const electronExe = path.join(__dirname, '../node_modules/electron/dist/electron.exe');
const scriptArg = process.argv[2] || 'verify_electron_runtime.cjs';
const targetScript = path.join(__dirname, scriptArg);

const childEnv = { ...process.env };
delete childEnv.ELECTRON_RUN_AS_NODE;

console.log('=== SPAWNING ELECTRON RUNTIME VERIFIER ===');
console.log('Binary:', electronExe);
console.log('Script:', targetScript);

const res = spawnSync(electronExe, [targetScript], {
  env: childEnv,
  encoding: 'utf-8',
});

console.log('Process Exit Code:', res.status);
console.log('--- STDOUT ---');
console.log(res.stdout);
if (res.stderr) {
  console.log('--- STDERR ---');
  console.log(res.stderr);
}

process.exit(res.status || 0);
