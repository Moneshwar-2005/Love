const http = require('http');

async function getPageWsUrl() {
  return new Promise((resolve, reject) => {
    http.get('http://127.0.0.1:9222/json', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        const targets = JSON.parse(data);
        const page = targets.find(t => t.type === 'page');
        if (page && page.webSocketDebuggerUrl) resolve(page.webSocketDebuggerUrl);
        else reject(new Error('Page target not found'));
      });
    }).on('error', reject);
  });
}

function callCdp(ws, method, params) {
  return new Promise((resolve, reject) => {
    const id = Math.floor(Math.random() * 1000000);
    const timer = setTimeout(() => reject(new Error(`Timeout on ${method}`)), 8000);
    const handler = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id === id) {
        clearTimeout(timer);
        ws.removeEventListener('message', handler);
        if (msg.error) reject(msg.error);
        else resolve(msg.result);
      }
    };
    ws.addEventListener('message', handler);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function run() {
  const wsUrl = await getPageWsUrl();
  const ws = new WebSocket(wsUrl);
  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = reject;
  });

  async function evaluate(expr) {
    const res = await callCdp(ws, 'Runtime.evaluate', {
      expression: expr,
      awaitPromise: true,
      returnByValue: true
    });
    return res;
  }

  // 1. Inspect initial form inputs
  const checkInputs = await evaluate(`(() => {
    const inputs = Array.from(document.querySelectorAll('input')).map(i => ({
      type: i.type,
      placeholder: i.placeholder,
      value: i.value
    }));
    return { inputs };
  })()`);
  console.log('Initial Inputs:', JSON.stringify(checkInputs.result.value));

  // 2. Set username and password
  const fillResult = await evaluate(`(() => {
    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    const inputs = document.querySelectorAll('input');
    let userInput = null;
    let passInput = null;
    for (const inp of inputs) {
      if (inp.type === 'text' || inp.placeholder.includes('username')) userInput = inp;
      if (inp.type === 'password') passInput = inp;
    }

    if (!userInput || !passInput) return { success: false, error: 'Inputs not found' };

    nativeSetter.call(userInput, 'invalid_test_user');
    userInput.dispatchEvent(new Event('input', { bubbles: true }));

    nativeSetter.call(passInput, 'WrongPassword123!');
    passInput.dispatchEvent(new Event('input', { bubbles: true }));

    return {
      success: true,
      userVal: userInput.value,
      passVal: passInput.value ? '••••••••' : ''
    };
  })()`);
  console.log('Fill Result:', JSON.stringify(fillResult.result.value));

  // 3. Click submit
  const submitResult = await evaluate(`(() => {
    const btn = document.querySelector('button[type="submit"]');
    if (!btn) return { error: 'Submit button not found' };
    btn.click();
    return { clicked: true, btnText: btn.innerText };
  })()`);
  console.log('Submit Clicked:', JSON.stringify(submitResult.result.value));

  // 4. Wait for network response (2 seconds)
  await new Promise(r => setTimeout(r, 2000));

  // 5. Inspect final DOM state
  const postSubmitState = await evaluate(`(() => {
    const alertBox = document.querySelector('.bg-rose-500\\\\/10, [class*="rose"]');
    const submitBtn = document.querySelector('button[type="submit"]');
    const bodyText = document.body.innerText;
    return {
      hasAlert: !!alertBox,
      alertText: alertBox ? alertBox.innerText : null,
      btnDisabled: submitBtn ? submitBtn.disabled : null,
      btnText: submitBtn ? submitBtn.innerText : null,
      bodySnippet: bodyText
    };
  })()`);
  console.log('Post Submit State:', JSON.stringify(postSubmitState.result.value, null, 2));

  // 6. Blur all inputs
  await evaluate(`(() => {
    document.querySelectorAll('input').forEach(i => i.blur());
  })()`);

  ws.close();
}

run().catch(err => {
  console.error('Test execution failed:', err);
  process.exit(1);
});