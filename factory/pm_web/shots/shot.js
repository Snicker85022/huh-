const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({
    headless: 'shell',
    executablePath: '/home/taza/.cache/puppeteer/chrome-headless-shell/linux-152.0.7977.54/chrome-headless-shell-linux64/chrome-headless-shell',
    args: ['--no-sandbox','--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  await page.setViewport({width:1680, height:1200, deviceScaleFactor:1});
  await page.goto('http://localhost:8095/architecture', {waitUntil:'networkidle0', timeout:30000});
  await new Promise(r=>setTimeout(r,1500));
  await page.screenshot({path:'/tmp/architecture_1680.png', fullPage:true});
  await page.goto('http://localhost:8095/sprinttracker', {waitUntil:'networkidle0', timeout:30000});
  await new Promise(r=>setTimeout(r,1500));
  await page.screenshot({path:'/tmp/sprinttracker_1680.png', fullPage:true});
  await browser.close();
  console.log('screenshots saved');
})().catch(e=>{console.error(e);process.exit(1);});
