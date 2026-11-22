const electron = require('electron');
console.log('Type of electron export:', typeof electron);
console.log('Keys of electron export:', Object.keys(electron));
if (electron.app) {
  electron.app.whenReady().then(() => {
    console.log('Electron app is ready!');
    console.log('UserData path:', electron.app.getPath('userData'));
    electron.app.quit();
  });
} else {
  console.log('electron.app is undefined! Export is:', electron);
}
