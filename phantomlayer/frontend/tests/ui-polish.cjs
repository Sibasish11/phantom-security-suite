// Frontend-only UI regression. Uses the running local API without rebuilding it.
// A fresh synthetic QA organization/domain/configuration/agent is retained per run.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const base = process.env.PHANTOMLAYER_UI_URL || 'http://localhost:3000';
const output = process.env.UI_SCREENSHOTS || '/tmp/phantomlayer-ui-polish';
fs.mkdirSync(output, {recursive:true});

(async()=>{
  assert(process.env.PHANTOMLAYER_EMAIL && process.env.PHANTOMLAYER_PASSWORD, 'Set the local defender login in your environment');
  const browser = await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH || undefined});
  const errors=[];
  let expectedFeedInterruption=false;
  const attach=page=>{
    page.on('pageerror',error=>errors.push(error.message));
    page.on('console',message=>{
      if(message.type()!=='error') return;
      const expected=expectedFeedInterruption && message.location().url.includes('/security/events') && message.text().includes('503');
      if(!expected) errors.push('Console: '+message.text());
    });
  };
  async function noOverflow(page,label) {
    const info=await page.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth,offenders:Array.from(document.querySelectorAll('main *')).filter(el=>el.getBoundingClientRect().right>innerWidth+2 && getComputedStyle(el).position!=='absolute').slice(0,5).map(el=>el.tagName+'.'+el.className)}));
    assert(info.width<=info.viewport+1, `${label}: horizontal overflow ${JSON.stringify(info)}`);
  }
  async function screenshot(page,name) {await page.screenshot({path:path.join(output,name+'.png'),fullPage:true});}
  try {
    const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
    const page=await context.newPage();attach(page);
    for(const width of [1440,820]) {
      await page.setViewportSize({width,height:1000});
      for(const route of ['/','/how-it-works','/protection','/login','/signup']) {
        await page.goto(base+route);await page.locator('h1').waitFor();await noOverflow(page,width+' public '+route);
        if(width===1440) await screenshot(page,'desktop-'+(route.slice(1)||'landing'));
      }
    }
    await page.setViewportSize({width:1440,height:1000});
    assert.equal(await page.locator('.phantom-logo:visible').count(),1,'No duplicate signup logo');
    await page.getByLabel('Create password',{exact:true}).fill('SyntheticPassword123!');
    await page.getByRole('button',{name:'Show password'}).click();
    assert.equal(await page.locator('#signup-password').getAttribute('type'),'text');
    await page.getByRole('button',{name:'Hide password'}).click();
    assert.equal(await page.locator('#signup-password').getAttribute('type'),'password');
    await page.goto(base+'/login');
    await page.locator('#login-email').fill(process.env.PHANTOMLAYER_EMAIL);
    await page.locator('#login-password').fill(process.env.PHANTOMLAYER_PASSWORD);
    await page.getByRole('button',{name:'Sign in',exact:true}).click();
    await page.getByRole('heading',{name:/Security overview/}).waitFor();
    await page.getByText('Telemetry connected',{exact:true}).waitFor();
    const incidentPath=await page.locator('.overview-primary').getAttribute('href');
    assert(incidentPath.startsWith('/dashboard/incidents/'),'Run the controlled demo before UI QA');
    const routes=['/dashboard', '/dashboard/incidents', incidentPath, '/dashboard/events', '/dashboard/sessions', '/dashboard/protection', '/dashboard/agent', '/dashboard/settings', '/onboarding', '/onboarding/domain', '/onboarding/domain/verify', '/onboarding/protection', '/onboarding/agent', '/onboarding/activation', '/admin', '/admin/organizations', '/admin/domains', '/admin/agents', '/admin/protections', '/admin/events', '/admin/incidents'];
    const failedResponses=[];
    page.on('response',response=>{if(response.url().startsWith(base) && response.status()>=400) failedResponses.push(response.status()+' '+new URL(response.url()).pathname);});
    for(const width of [1440,820,390]) {
      await page.setViewportSize({width,height:width===390?844:1000});
      for(const route of routes) {
        await page.goto(base+route);
        await page.locator('main h1, main h2').first().waitFor();
        await page.waitForTimeout(250);
        await noOverflow(page,`${width} ${route}`);
        assert.equal(await page.getByText('No incident ID was provided.',{exact:true}).count(),0);
        if(route.startsWith('/onboarding/')) {
          const position=await page.locator('.setup-position').innerText();
          const stage=await page.locator('.onboarding-eyebrow').first().innerText();
          if(stage==='DOMAIN READY') {
            assert.equal(route,'/onboarding/domain','Only the completed domain screen replaces its numbered caption');
            assert(position.includes('Step 2 of 6'));
          } else {
            assert.match(stage,/STEP (\d+)/,'Expected a numbered setup caption');
            assert.equal(Number(stage.match(/STEP (\d+)/)[1]),Number(position.match(/Step (\d+)/)[1]),'Setup step labels must agree');
          }
        }
        if(route==='/dashboard/incidents') {
          await page.locator('.incident-row').first().waitFor();
          assert(await page.locator('.incident-row-risk').first().isVisible(),'Risk, status and timestamp remain visible on mobile');
        }
        if(route===incidentPath) {
          assert((await page.getByRole('heading',{name:'Attack timeline',exact:true}).boundingBox()).y < (width===390?1200:900),'Attack timeline remains prominent');
        }
        if(width!==820) await screenshot(page,`${width}-${route===incidentPath?'incident-detail':route.slice(1).replaceAll('/','-')}`);
      }
      if(width<900) {
        await page.getByRole('button',{name:'Open navigation'}).click();
        await page.locator('dialog[open]').waitFor();
        await page.keyboard.press('Tab');
        assert(await page.evaluate(()=>Boolean(document.activeElement.closest('dialog'))),'Mobile navigation contains keyboard focus');
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('dialog[open]').count(),0);
        await page.getByRole('button',{name:'Open navigation'}).click();
        await page.locator('dialog').getByRole('link',{name:'Domains',exact:true}).click();
        await page.waitForURL('**/admin/domains');
        await page.locator('dialog[open]').waitFor({state:'hidden'});
      }
    }
    // Actual populated admin registries, keyboard row selection, focus trapping and Escape.
    for(const [route,name] of [['/admin/events','Event details'],['/admin/incidents','Incident details']]) {
      await page.goto(base+route);
      const row=page.locator('tbody tr').first();
      await row.waitFor();await row.focus();await page.keyboard.press('Enter');
      await page.getByRole('dialog',{name,exact:true}).waitFor();
      await page.keyboard.press('Tab');
      assert(await page.evaluate(()=>Boolean(document.activeElement.closest('dialog'))),'Detail drawer contains focus');
      await noOverflow(page,'mobile '+name);
      await screenshot(page,'mobile-'+name.replaceAll(' ','-').toLowerCase());
      await page.keyboard.press('Escape');
      await page.getByRole('dialog',{name,exact:true}).waitFor({state:'hidden'});
    }
    // The customer queue must lead to the full investigation without requiring
    // a dashboard shortcut or manually constructing an incident URL.
    await page.goto(base+'/dashboard/incidents');
    await page.locator('.incident-row').first().click();
    await page.getByRole('link',{name:'Open full investigation ↗',exact:true}).click();
    await page.getByRole('heading',{name:'Attack timeline',exact:true}).waitFor();
    await page.getByRole('button',{name:'Refresh evidence',exact:true}).click();
    await page.getByRole('button',{name:'Refresh evidence',exact:true}).waitFor();
    assert.deepEqual(failedResponses,[],'Functional pages must not have API errors');
    // Actual event filters, expandable metadata, and no-match state.
    await page.goto(base+'/dashboard/events');
    await page.locator('.event-entry').first().waitFor();
    await page.getByRole('button',{name:'Deception',exact:true}).click();
    await page.getByRole('button',{name:'High',exact:true}).click();
    assert(await page.locator('.event-entry').count()>0,'Uppercase API severities must filter correctly');
    await page.locator('.event-entry summary').first().click();
    await page.locator('.event-entry[open] .event-expanded').waitFor();
    await noOverflow(page,'expanded event mobile');
    await screenshot(page,'mobile-event-inspection');
    await page.getByRole('textbox',{name:'Search security events'}).fill('no-such-event-'+Date.now());
    await page.getByRole('heading',{name:'No matching signals'}).waitFor();
    await screenshot(page,'mobile-event-empty');
    await page.getByRole('button',{name:'Clear filters'}).click();
    assert(await page.locator('.event-entry').count()>0);
    // Error and retry state; scoped browser interception, no backend changes.
    expectedFeedInterruption=true;
    await page.route('**/security/events?limit=100',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Temporary QA feed interruption'})}));
    await page.getByRole('button',{name:'Refresh',exact:true}).click();
    await page.getByRole('alert').filter({hasText:'Event feed unavailable'}).waitFor();
    await screenshot(page,'mobile-event-error');
    await page.unroute('**/security/events?limit=100');
    await page.getByRole('button',{name:'Refresh',exact:true}).click();
    await page.getByRole('alert').filter({hasText:'Event feed unavailable'}).waitFor({state:'hidden'});
    expectedFeedInterruption=false;
    // Public forms, errors and navigation must also fit phone widths.
    for(const route of ['/','/how-it-works','/protection','/login','/signup','/unauthorized','/not-a-real-page']) {
      await page.goto(base+route);await page.locator('h1').waitFor();await noOverflow(page,'mobile '+route);await screenshot(page,'mobile-'+(route.slice(1)||'landing'));
    }
    // Complete the actual registration -> domain -> demo verification ->
    // protection -> pending agent flow in a separate synthetic tenant.
    const fresh=await browser.newContext({viewport:{width:1280,height:960},reducedMotion:'reduce'});
    const setup=await fresh.newPage();attach(setup);
    const suffix=crypto.randomUUID().slice(0,8);
    await setup.goto(base+'/signup');
    await setup.getByLabel('Organization name',{exact:true}).fill('UI QA '+suffix);
    await setup.getByLabel('Your full name',{exact:true}).fill('Synthetic UI Reviewer');
    await setup.getByLabel('Work email',{exact:true}).fill(`ui-qa-${suffix}@phantomlayer.example.com`);
    await setup.getByLabel('Create password',{exact:true}).fill(crypto.randomBytes(18).toString('base64url')+'aA1!');
    await setup.getByLabel('Your full name',{exact:true}).fill('   ');
    await setup.getByRole('button',{name:'Create organization',exact:true}).click();
    await setup.getByRole('alert').filter({hasText:'non-space characters'}).waitFor();
    await setup.getByLabel('Your full name',{exact:true}).fill('Synthetic UI Reviewer');
    await setup.getByRole('button',{name:'Create organization',exact:true}).click();
    await setup.waitForURL('**/onboarding');
    await setup.getByRole('link',{name:/Begin deployment/}).click();
    await setup.getByPlaceholder('example.com').fill('not-a-domain');
    await setup.getByRole('button',{name:/Continue to verification/}).click();
    await setup.getByRole('alert').filter({hasText:'Enter a valid domain'}).waitFor();
    await setup.getByPlaceholder('example.com').fill(`ui-qa-${suffix}.example.test`);
    await setup.getByRole('button',{name:/Continue to verification/}).click();
    await setup.waitForURL('**/onboarding/domain/verify');
    await setup.getByRole('button',{name:/Verify DNS record/}).waitFor();
    await noOverflow(setup,'fresh verification');
    // No public DNS probe: exercise the negative result using the existing response shape.
    await setup.route('**/domains/*/verify',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({verified:false})}));
    await setup.getByRole('button',{name:/Verify DNS record/}).click();
    await setup.getByRole('alert').filter({hasText:'not been confirmed'}).waitFor();
    await setup.unroute('**/domains/*/verify');
    await setup.getByRole('button',{name:/Use local demo verification/}).click();
    await setup.waitForURL('**/onboarding/protection');
    await setup.getByRole('button',{name:/Continue/}).last().click();
    await setup.waitForURL('**/onboarding/agent');
    await setup.getByRole('button',{name:/Register agent/}).click();
    await setup.getByText('Save this token now',{exact:true}).waitFor();
    // Do not screenshot/log the one-time registration credential.
    await setup.getByRole('button',{name:/Check activation/}).click();
    await setup.waitForURL('**/onboarding/activation');
    await setup.getByText('Waiting for your agent to connect.',{exact:true}).waitFor();
    await setup.getByRole('link',{name:/Go to workspace/}).click();
    await setup.getByText('No correlated incidents yet',{exact:true}).waitFor();
    await noOverflow(setup,'new tenant empty dashboard');
    await screenshot(setup,'empty-workspace');
    await setup.goto(base+'/dashboard/protection');
    await setup.getByRole('button',{name:'Pause protection',exact:true}).click();
    await setup.getByRole('button',{name:'Enable protection',exact:true}).waitFor();
    assert.equal(await setup.getByText('No protection configured',{exact:true}).count(),0,'Paused protection remains manageable');
    await setup.getByRole('button',{name:'Enable protection',exact:true}).click();
    await setup.getByRole('button',{name:'Pause protection',exact:true}).waitFor();
    await setup.goto(base+'/dashboard/settings');
    await setup.locator('.loading-screen').waitFor({state:'hidden'});
    await setup.waitForTimeout(200);
    assert.equal(await setup.getByText('Loading domain information…',{exact:true}).count(),0,'No endless empty-tenant loading state');
    assert.deepEqual(errors,[],'Browser JavaScript errors');
    console.log('PASS: all public/setup/customer/admin pages at 1440/820/390px; mobile risk/status and keyboard navigation; prominent timeline; event filters/details/empty/error/retry; actual signup validation/domain/demo verification/protection/pending agent flow; no overflow or unexpected console/page errors (one deliberate 503 recovery check).');
    await fresh.close();await context.close();
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
