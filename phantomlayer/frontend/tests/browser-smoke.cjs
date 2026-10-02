// Requires both running stacks and a tenant with at least one incident.
// CHROMIUM_PATH may select an existing browser; otherwise run npx playwright install chromium.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');

(async () => {
  const email = process.env.PHANTOMLAYER_EMAIL;
  const password = process.env.PHANTOMLAYER_PASSWORD;
  assert(email && password, 'Set PHANTOMLAYER_EMAIL and PHANTOMLAYER_PASSWORD for the local demo tenant');
  const output = process.env.QA_SCREENSHOTS || '/tmp/phantomlayer-qa-screenshots';
  fs.mkdirSync(output, {recursive: true});
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_PATH || undefined});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1080}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://localhost:3001');
    await page.getByLabel('Password', {exact: true}).fill('DemoMaya!2025');
    await page.getByRole('button', {name: /Sign in/}).click();
    await page.getByRole('heading', {name: 'Welcome back, Maya'}).waitFor();
    await page.locator('.total-balance').waitFor();
    await page.screenshot({path: path.join(output, 'bank-desktop.png'), fullPage: true});
    const balanceResponse = await page.request.get('http://localhost:3001/api/balance');
    assert.equal(balanceResponse.status(), 200);
    const balanceBefore = (await balanceResponse.json()).total_balance_cents;
    assert(Number.isInteger(balanceBefore));
    await page.getByPlaceholder('0.00', {exact: true}).fill('0.01');
    await page.getByPlaceholder('Reference (optional)').fill('Browser smoke QA');
    await page.getByRole('button', {name: /Send synthetic transfer/}).click();
    await page.getByText('Synthetic transfer completed. Your balance and activity are updated.', {exact: true}).waitFor();
    const expectedBalance = new Intl.NumberFormat('en-GB', {style:'currency', currency:'GBP'}).format((balanceBefore - 1) / 100);
    await page.waitForFunction(expected => document.querySelector('.total-balance')?.textContent === expected, expectedBalance);
    for (const name of ['Activity', 'Accounts', 'Cards', 'Profile', 'Support']) {
      await page.locator('.sidebar button').filter({hasText: name}).first().click();
      await page.waitForTimeout(100);
      assert.equal(await page.locator('[role="alert"]').count(), 0, `Bank page failed: ${name}`);
    }
    await page.setViewportSize({width: 390, height: 844});
    await page.getByRole('button', {name: 'Open navigation'}).click();
    await page.locator('.mobile-nav').getByRole('button', {name: /Overview/}).click();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Bank mobile overflow');
    await page.screenshot({path: path.join(output, 'bank-mobile.png'), fullPage: true});
    await page.setViewportSize({width: 1440, height: 1080});
    await page.goto('http://localhost:3000/login');
    await page.locator('input[type=email]').fill(email);
    await page.locator('input[type=password]').fill(password);
    await page.getByRole('button', {name: /Sign in/}).click();
    await page.getByRole('heading', {name: /Security overview/}).waitFor();
    await page.getByText('Telemetry connected', {exact: true}).waitFor();
    assert.equal(await page.locator('.ui-alert-error').count(), 0);
    await page.screenshot({path: path.join(output, 'security-overview.png'), fullPage: true});
    await page.locator('.overview-primary').click();
    await page.getByText('INCIDENT INVESTIGATION', {exact: true}).waitFor();
    await page.waitForTimeout(500);
    assert.equal(await page.getByText('Incident unavailable', {exact: true}).count(), 0);
    await page.getByRole('button', {name: /^(Analyze incident|Re-analyze)$/}).click();
    await page.getByText('mock', {exact: true}).waitFor();
    await page.screenshot({path: path.join(output, 'incident.png'), fullPage: true});
    for (const route of ['/dashboard/settings', '/dashboard/incidents', '/dashboard/events', '/dashboard/sessions', '/onboarding', '/admin', '/admin/organizations']) {
      await page.goto(`http://localhost:3000${route}`);
      await page.waitForTimeout(400);
      assert((await page.locator('body').innerText()).length > 40, `Blank route ${route}`);
      assert(!(await page.locator('body').innerText()).includes('No incident ID'));
      if (route === '/admin/organizations') {
        await page.locator('.admin-org-table-wrap tbody tr').waitFor();
        assert.equal(await page.locator('.admin-org-table-wrap tbody tr').count(), 1, 'Tenant-only directory');
        assert.equal(await page.getByText('Organization feed unavailable', {exact: true}).count(), 0);
      }
    }
    await page.setViewportSize({width: 390, height: 844});
    await page.goto('http://localhost:3000/dashboard');
    await page.getByRole('heading', {name: /Security overview/}).waitFor();
    await page.getByText('Telemetry connected', {exact: true}).waitFor();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Security mobile overflow');
    await page.screenshot({path: path.join(output, 'security-mobile.png'), fullPage: true});
    assert.deepEqual(errors, [], 'Browser runtime errors');
    console.log('PASS: bank desktop/mobile/navigation and real synthetic transfer, platform login/dashboard/analysis/settings/onboarding/tenant-admin; no page errors');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
