// An actual, single-session browser rehearsal of docs/JUDGE-DEMO.md.
// Both local stacks must be running. Never run alongside isolation/restart checks.
// Uses existing synthetic demo data; evidence persists and nothing is reset.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const bankRoot = path.resolve(__dirname, '../../../PhantomBank');
const output = process.env.JUDGE_SCREENSHOTS || '/tmp/phantomlayer-judge-rehearsal';
const socBase = 'http://localhost:3000';
const bankBase = 'http://localhost:3001';

(async () => {
  assert(process.env.PHANTOMLAYER_EMAIL && process.env.PHANTOMLAYER_PASSWORD, 'Supply the local defender login privately');
  fs.mkdirSync(output, {recursive:true});
  const browser = await chromium.launch({headless:true, executablePath:process.env.CHROMIUM_PATH || undefined});
  const failures = [];
  const audit = page => {
    page.on('pageerror', error => failures.push('JavaScript: '+error.message));
    page.on('console', message => {if(message.type()==='error') failures.push('Console: '+message.text());});
    page.on('response', response => {if(response.status()>=400) failures.push(`HTTP ${response.status()}: ${new URL(response.url()).pathname}`);});
  };
  const fingerprint = () => execFileSync('python', ['-c', 'from scripts.verify_isolation import real_fingerprint; print(real_fingerprint())'], {cwd:bankRoot, encoding:'utf8'}).trim();
  try {
    const defender = await browser.newContext({viewport:{width:1440,height:1000}, reducedMotion:'reduce'});
    const soc = await defender.newPage();audit(soc);
    await soc.goto(socBase+'/login');
    await soc.getByLabel('Email address', {exact:true}).fill(process.env.PHANTOMLAYER_EMAIL);
    await soc.getByLabel('Password', {exact:true}).fill(process.env.PHANTOMLAYER_PASSWORD);
    await soc.getByRole('button', {name:'Sign in',exact:true}).click();
    await soc.getByText('Telemetry connected', {exact:true}).waitFor();
    // The bearer credential is used only inside the browser, never returned or logged.
    const socGet = route => soc.evaluate(async route => {
      const response = await fetch(route, {headers:{Authorization:'Bearer '+localStorage.getItem('phantomlayer_access_token')}});
      if(!response.ok) throw new Error(`Defender request failed: ${response.status}`);
      return response.json();
    }, route);
    const beforeIds = new Set((await socGet('/incidents?limit=1000')).incidents.map(item=>item.incident_id));
    const statsBefore = await socGet('/security/stats');

    const customer = await browser.newContext({viewport:{width:1440,height:1000}, reducedMotion:'reduce'});
    const bank = await customer.newPage();audit(bank);
    await bank.goto(bankBase);
    await bank.getByLabel('Password',{exact:true}).fill('DemoMaya!2025');
    await bank.getByRole('button',{name:/Sign in/}).click();
    await bank.getByRole('heading',{name:'Welcome back, Maya'}).waitFor();
    await bank.locator('.total-balance').waitFor();
    const bankGet = route => bank.evaluate(async route => {
      const response = await fetch(route);
      if(!response.ok) throw new Error(`Bank request failed: ${response.status}`);
      return response.json();
    }, route);
    assert.equal((await bankGet('/api/profile')).profile.full_name, 'Maya Bennett');
    assert((await bankGet('/api/accounts')).accounts.length>0);
    await bank.locator('.sidebar button').filter({hasText:'Activity'}).click();
    await bank.getByRole('heading',{name:'Activity',exact:true}).waitFor();
    const realEvents = (await socGet('/security/events?limit=100')).events;
    assert(realEvents.some(event=>event.operation==='get_profile' && event.final_target==='real' && event.risk_score===0));
    assert((await socGet('/security/stats')).requests_routed_to_real>statsBefore.requests_routed_to_real);
    const beforeAttack = fingerprint();
    console.log('PASS: browser sign-in, Maya profile/accounts/activity, real routing decisions at risk 0');

    // These are the exact bounded browser requests in the live runbook.
    await bankGet('/api/security/list-tables');
    await bankGet('/api/security/enumerate-api');
    const customers = await bankGet('/api/security/customers');
    assert(customers.result.records.some(row=>row.full_name==='John Carter'));
    assert(!JSON.stringify(customers).includes('Maya Bennett'));
    assert(!/"(target|destination|risk_score|triggered_rules|agent_token|customer_marker)"\s*:/.test(JSON.stringify(customers)), 'Public responses must not reveal routing metadata');
    assert.equal((await bankGet('/api/profile')).profile.full_name,'John Carter');
    assert.equal(fingerprint(), beforeAttack, 'Real business rows or gateway-access audit changed during the attack');
    const newIncidents = (await socGet('/incidents?limit=1000')).incidents.filter(item=>!beforeIds.has(item.incident_id));
    assert.equal(newIncidents.length,1,'Exactly this new bank session must correlate to one incident');
    const incident = newIncidents[0];
    const timeline = (await socGet(`/incidents/${incident.incident_id}/timeline`)).timeline;
    assert.deepEqual(timeline.map(item=>item.risk_score),[27,49,67,67]);
    assert(timeline.every(item=>item.final_target==='honeypot' && item.success));
    const events = (await socGet('/security/events?limit=100&session_id='+encodeURIComponent(incident.session_id))).events;
    assert(events.some(event=>event.event_type==='request_analyzed' && event.triggered_rules.length>0));
    assert(events.some(event=>event.event_type==='routing_decision' && event.final_target==='honeypot'));
    assert(events.every(event=>event.session_id===incident.session_id));
    console.log('PASS: controlled recon, risk 27 → 49 → 67, pinned profile at 67, John-only data, correlated detection/routing telemetry, unchanged real data AND audit');

    await soc.goto(socBase+'/dashboard/incidents/'+incident.incident_id);
    await soc.getByRole('heading',{name:'Attack timeline',exact:true}).waitFor();
    assert.deepEqual(await soc.locator('.timeline-risk-history li strong').allTextContents(),['27','49','67','67']);
    assert.equal(await soc.locator('.incident-pipeline li').count(),6);
    // Timeline must be immediately visible, not buried below session metadata.
    assert((await soc.locator('#attack-timeline-title').boundingBox()).y < 900);
    await soc.getByRole('button',{name:'Analyze incident',exact:true}).click();
    await soc.getByText('mock',{exact:true}).waitFor();
    await soc.getByText('Likely objective · advisory inference',{exact:true}).waitFor();
    await soc.screenshot({path:path.join(output,'investigation.png'),fullPage:true});
    await soc.getByRole('link',{name:/Inspect this session's detection and routing events/}).click();
    await soc.locator('.session-filter-banner').waitFor();
    await soc.locator('.event-entry').first().waitFor();
    await soc.getByRole('button',{name:'Deception',exact:true}).click();
    await soc.locator('.event-entry summary').first().click();
    await soc.locator('.event-entry[open] .event-expanded').waitFor();
    await soc.screenshot({path:path.join(output,'session-evidence.png'),fullPage:true});
    await soc.getByRole('button',{name:'Show all sessions',exact:true}).click();
    assert.equal(new URL(soc.url()).search,'');
    console.log('PASS: exact incident in defender UI, six-stage pipeline, visible risk timeline, session-scoped event inspection and mock analysis');

    // Reloading the bank shows the believable synthetic identity in the UI too.
    await bank.reload();
    await bank.getByRole('heading',{name:'Welcome back, John'}).waitFor();
    await bank.locator('.total-balance').waitFor();
    await bank.locator('.sidebar button').filter({hasText:'Profile'}).click();
    await bank.getByRole('heading',{name:'John Carter',exact:true}).waitFor();
    await bank.screenshot({path:path.join(output,'synthetic-profile.png'),fullPage:true});
    assert.equal(fingerprint(),beforeAttack,'Reloaded pinned bank UI touched real business/audit data');
    await soc.goto(socBase+'/dashboard/incidents/'+incident.incident_id);
    await soc.getByRole('heading',{name:'Attack timeline',exact:true}).waitFor();
    await soc.getByRole('button',{name:'Refresh evidence',exact:true}).click();
    await soc.getByRole('button',{name:'Refresh evidence',exact:true}).waitFor();
    assert(await soc.locator('.full-timeline-event').count()>4,'UI reload must append observable deception interactions');
    await soc.getByRole('button',{name:'Analyze incident',exact:true}).click();
    await soc.getByText('mock',{exact:true}).waitFor();
    await soc.reload();
    await soc.getByText('mock',{exact:true}).waitFor();
    assert.equal(fingerprint(),beforeAttack);
    // A new login is the documented local-demo way to start a normal session.
    // This is deliberately after the attack-isolation fingerprint window.
    await bank.getByRole('button',{name:/Sign out/}).click();
    await bank.getByLabel('Password',{exact:true}).fill('DemoMaya!2025');
    await bank.getByRole('button',{name:/Sign in/}).click();
    await bank.getByRole('heading',{name:'Welcome back, Maya'}).waitFor();
    await bank.locator('.total-balance').waitFor();
    assert.deepEqual(failures,[],'No browser console/page errors or failed HTTP requests during the full rehearsal');
    console.log('PASS: believable John profile in browser, fresh telemetry invalidates old analysis, refresh/re-analysis persists, real fingerprint unchanged; sign-out/new login returns to Maya; ZERO console/page/HTTP errors');
    await customer.close();await defender.close();
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
