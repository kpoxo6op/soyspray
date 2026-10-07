const {defineConfig} = require('@playwright/test');
module.exports = defineConfig({testDir:'./tests',testMatch:'**/*.spec.js',workers:1,
  use:{baseURL:'http://127.0.0.1:18185',launchOptions:process.env.MEMES_TEST_BROWSER ? {executablePath:process.env.MEMES_TEST_BROWSER} : {}},
  projects:[{name:'phone',use:{viewport:{width:390,height:844}}},{name:'desktop',use:{viewport:{width:1280,height:900}}}],
  webServer:{command:'PYTHONPATH=.:tests "${MEMES_TEST_PYTHON:-python3}" tests/serve.py',url:'http://127.0.0.1:18185/healthz',reuseExistingServer:false}
});
