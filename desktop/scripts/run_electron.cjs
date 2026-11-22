const { spawn } = require('child_process');
const electronPath = require('electron');

const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;
if (process.argv.includes('--capture-sync')) {
  env.ELECTRON_CAPTURE_SYNC = '1';
}

const args = process.argv.slice(2).filter((a) => a !== '--capture-sync');
if (args.length === 0) {
  args.push('electron/main.cjs');
}

const child = spawn(electronPath, args, {
  stdio: 'inherit',
  env: env,
});

child.on('exit', (code) => {
  process.exit(code || 0);
});
