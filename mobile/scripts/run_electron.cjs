const { spawn } = require('child_process');
const path = require('path');

const electronExe = path.join(__dirname, '../../desktop/node_modules/electron/dist/electron.exe');
const scriptPath = path.join(__dirname, 'capture_screenshots.cjs');

const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;

console.log('Spawning electron for mobile screenshots capture...');
const child = spawn(electronExe, [scriptPath], {
  env,
  stdio: 'inherit',
  windowsHide: false
});

child.on('exit', (code) => {
  console.log('Electron mobile capture exited with code:', code);
  process.exit(code || 0);
});
