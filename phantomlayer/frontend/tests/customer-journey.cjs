// Real browser onboarding + live PostgreSQL evidence. No provision_demo.py.
// Temporarily connects the bank to a disposable customer; finally restores its
// original .env and removes only manifest-owned QA tenants and access audits.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const layer = path.resolve(__dirname, '../..');
const bank = path.resolve(layer, '../PhantomBank');
const run = crypto.randomBytes(8).toString('hex');
const output = path.join('/tmp/omnirush', `customer-qa-${run}`);
fs.mkdirSync(output, { mode: 0o700 });
const manifest = { purpose: 'customer-journey-qa', run, organizations: [], agents: [], baseline_sessions: [] };
const save = () => fs.writeFileSync(path.join(output, 'manifest.json'), JSON.stringify(manifest, null, 2), {mode: 0o600});
const original = fs.readFileSync(path.join(bank, '.env'));
fs.writeFileSync(path.join(output, 'bank.env.backup'), original, { mode: 0o600 });
const report = {run, checks: []};
const check = value => { report.checks.push(value); console.log('PASS', value); };
const execute = (cmd, args, cwd, input) => execFileSync(cmd, args, {cwd, input, encoding:'utf8', timeout:120000, maxBuffer:10*1024*1024});
const python = (code, input) => execute('python', ['-c', code], bank, input);
const compose = (cwd, args) => execute('docker', ['compose', ...args], cwd);
const snapshot = () => JSON.parse(python("import sys,json; sys.path.insert(0,'scripts'); from compare_attack import fingerprints; print(json.dumps(fingerprints()))"));
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
async function api(route, token, body, method = body === undefined ? 'GET' : 'POST', expected = 200) {
  const response = await fetch('http://127.0.0.1:8000' + route, {method,
    headers: {'Content-Type':'application/json', ...(token ? {Authorization:'Bearer '+token} : {})},
    body:body === undefined ? undefined : JSON.stringify(body)});
  assert.equal(response.status, expected, `${method} ${route}: ${response.status}`);
  return response.status === 204 ? null : response.json();
}
async function active(token) {
  for (let i=0; i<30; i++) {
    const protections = await api('/protections', token);
    if (protections[0]?.status === 'active') return protections[0];
    await wait(2000);
  }
  throw new Error('Bank integration did not activate');
}
function remember(result, name, email) {
  manifest.organizations.push({id:result.user.organization_id, user_id:result.user.user_id, name, email}); save();
}

(async () => {
  let browser, initial;
  let cleanupOK = false;
  save();
  try {
    assert(!fs.existsSync(path.join(bank,'.env.integration-backup')), 'An operator recovery backup exists; stop rather than overwrite it');
    initial = snapshot();
    // Explicit deployment mode change only on this bounded local QA host. No DB edits.
    execute('python',['scripts/connect.py','standalone'],bank);
    const before = JSON.parse(execute('python',['scripts/compare_attack.py','before'],bank));
    manifest.baseline_sessions.push(before.steps[0].session_id); save();
    report.before = before;
    check('BEFORE: same eight allowlisted requests use REAL; Maya exposed; business data unchanged');

    browser = await chromium.launch({headless:true, executablePath:process.env.CHROMIUM_PATH || undefined});
    const context = await browser.newContext({viewport:{width:1440,height:1000}, reducedMotion:'reduce'});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    await page.goto('http://localhost:3001/owner');
    await page.getByText('BEFORE — standalone synthetic bank, no protection', {exact:true}).waitFor();
    await page.screenshot({path:path.join(output,'bank-owner-before.png'),fullPage:true});
    await page.goto('http://localhost:3000/signup');
    const name = `Customer QA ${run}`, email = `customer-qa-${run}@example.com`, password = crypto.randomBytes(24).toString('base64url');
    await page.getByLabel('Organization name').fill(name);
    await page.getByLabel('Your full name').fill('PhantomBank QA Owner');
    await page.getByLabel('Work email').fill(email);
    await page.getByLabel('Create password',{exact:true}).fill(password);
    const registered = page.waitForResponse(r => r.url().endsWith('/auth/register') && r.request().method() === 'POST');
    await page.getByRole('button',{name:'Create organization',exact:true}).click();
    const response = await registered; assert.equal(response.status(),201);
    const owner = await response.json(); remember(owner,name,email);
    await page.waitForURL('**/onboarding');
    await page.evaluate(() => localStorage.clear());
    await page.goto('http://localhost:3000/login');
    await page.locator('#login-email').fill(email);
    await page.locator('#login-password').fill(password);
    const loggedIn = page.waitForResponse(r => r.url().endsWith('/auth/login'));
    await page.getByRole('button',{name:'Sign in',exact:true}).click();
    const login = await (await loggedIn).json(); const token = login.access_token;
    assert.equal(login.user.organization_id, owner.user.organization_id);
    assert.equal((await api('/organizations',token))[0].name,name);
    check('Browser signup, organization creation and fresh login');
    await page.goto('http://localhost:3000/onboarding/domain');
    await page.getByRole('textbox').fill('phantombank.example.test');
    await page.getByRole('button',{name:/Continue to verification/}).click();
    await page.waitForURL('**/domain/verify');
    let domain = (await api('/domains',token))[0];
    await api(`/domains/${domain.id}/demo-verify`,token,{},'POST',422);
    await api('/agents/register',token,{name:'unverified',domain_id:domain.id,version:'qa'},'POST',422);
    python("import sys; sys.path.insert(0,'scripts'); from connect import publish_challenge; publish_challenge(sys.stdin.read())",domain.verification_token);
    await page.getByRole('button',{name:/Use local demo verification/}).click();
    await page.waitForURL('**/onboarding/protection');
    domain = (await api('/domains',token))[0]; assert(domain.verified);
    await page.getByRole('button',{name:/Continue to agent/}).click();
    await page.waitForURL('**/onboarding/agent');
    await page.getByRole('button',{name:'Register agent',exact:true}).click();
    await page.getByRole('button',{name:'Download integration configuration'}).waitFor();
    const agent = (await api('/agents',token))[0]; manifest.agents.push(agent.agent_id); save();
    assert.equal(agent.domain_id,domain.id); assert.equal(agent.status,'pending');
    const protection = (await api('/protections',token))[0];
    assert.equal(protection.status,'connecting');
    await api(`/protections/${protection.id}`,token,{status:'active'},'PATCH',422);
    // Simulate closing the one-time credential page before installation.
    await page.reload();
    await page.getByRole('button',{name:'Rotate credential and reconnect'}).click();
    await page.getByRole('button',{name:'Download integration configuration'}).waitFor();
    const downloadEvent = page.waitForEvent('download');
    await page.getByRole('button',{name:'Download integration configuration'}).click();
    const downloaded = await downloadEvent;
    const bundlePath = path.join(output,'integration.json'); await downloaded.saveAs(bundlePath); fs.chmodSync(bundlePath,0o600);
    const bundle = JSON.parse(fs.readFileSync(bundlePath));
    assert.equal(bundle.organization_id, owner.user.organization_id);
    assert(!(await page.locator('body').innerText()).includes(bundle.agent_token));
    execute('python',['scripts/connect.py','install',bundlePath],bank);
    const healthy = await active(token);
    assert.equal(healthy.organization_id,owner.user.organization_id);
    await page.getByRole('link',{name:/Check activation/}).click();
    await page.getByText('PROTECTION ACTIVE',{exact:true}).waitFor();
    await page.screenshot({path:path.join(output,'customer-active.png'),fullPage:true});
    check('Published local ownership proof, API selection, one-time bundle, correct tenant agent, real heartbeat, both DBs, ACTIVE');

    const bankPage = await context.newPage();
    bankPage.on('pageerror', error => errors.push(error.message));
    await bankPage.goto('http://localhost:3001/');
    await bankPage.getByLabel('Password',{exact:true}).fill('DemoMaya!2025');
    await bankPage.getByRole('button',{name:/^Sign in/}).click();
    await bankPage.getByRole('heading',{name:'Welcome back, Maya'}).waitFor();
    await bankPage.locator('.sidebar').getByRole('button',{name:/Accounts/}).click();
    await bankPage.getByRole('heading',{name:'Accounts',exact:true}).waitFor();
    await bankPage.screenshot({path:path.join(output,'bank-legitimate.png'),fullPage:true});
    await bankPage.close();
    check('Bank browser legitimate login/accounts and UI credential-recovery rotation');

    const after = JSON.parse(execute('python',['scripts/compare_attack.py','after'],bank)); report.after = after;
    assert.deepEqual(before.steps.map(s=>s.request),after.steps.map(s=>s.request));
    assert.deepEqual(after.steps.map(s=>s.risk_score),[27,49,67,77,87,97,100,100]);
    assert(after.steps[0].triggered_rules.length > 0);
    check('AFTER: identical requests divert at risk 27; John returned; risk progresses to 100; REAL dataset and access audit unchanged');
    const incident = (await api('/incidents',token)).incidents[0];
    manifest.incident = incident.incident_id; manifest.session = incident.session_id; save();
    let timeline = await api(`/incidents/${incident.incident_id}/timeline`,token);
    assert.equal(timeline.timeline.length,8); assert(timeline.timeline.every(e=>e.final_target==='honeypot'));
    assert(timeline.timeline[0].triggered_rules.length);
    const detailRoute = '/dashboard/incidents/'+incident.incident_id;
    await page.goto('http://localhost:3000'+detailRoute);
    await page.getByRole('heading',{name:'Attack timeline',exact:true}).waitFor();
    await page.getByRole('button',{name:'Analyze incident',exact:true}).click();
    await page.getByRole('button',{name:'Re-analyze',exact:true}).waitFor();
    const detail = await api('/incidents/'+incident.incident_id,token);
    assert.equal(detail.status,'completed'); assert.equal(detail.analysis.analysis_provider,'mock');
    const events = await api('/security/events?limit=1000',token);
    assert(events.events.some(e=>e.event_type==='honeypot_interaction'));
    const metadata = JSON.stringify({detail,events});
    for (const forbidden of ['Maya Bennett','John Carter','REAL-MAYA-7Q4N','DECOY-JOHN-3M8Z',bundle.agent_token,'DemoMaya!2025','maya.bennett@northstar.test']) assert(!metadata.includes(forbidden));
    report.incident = {id:incident.incident_id, session:incident.session_id, timeline:timeline.timeline,
      analysis_provider:detail.analysis.analysis_provider, analysis_status:detail.status, events:events.events.length};
    check('Tenant incident, rule/risk/routing timeline, honeypot counts, mock analysis and sanitized SaaS payload');

    const otherName = name+' isolation', otherEmail = `customer-qa-${run}-isolation@example.com`;
    const other = await api('/auth/register',null,{company_name:otherName,full_name:'Isolation Owner',email:otherEmail,password},'POST',201);
    remember(other,otherName,otherEmail);
    for (const route of [`/domains/${domain.id}`,`/agents/${agent.agent_id}`,`/protections/${protection.id}`,
      `/incidents/${incident.incident_id}`,`/incidents/${incident.incident_id}/timeline`,`/api/v1/incidents/${incident.session_id}`]) {
      await api(route,other.access_token,undefined,'GET',404);
    }
    await api(`/agents/${agent.agent_id}/rotate-token`,other.access_token,{},'POST',404);
    await api(`/protections/${protection.id}`,other.access_token,{enabled:false},'PATCH',404);
    assert.equal((await api('/incidents',other.access_token)).incidents.length,0);
    assert.equal((await api('/security/events',other.access_token)).events.length,0);
    await api(`/api/v1/incidents/${incident.session_id}/analyze`,other.access_token,{},'POST',404);
    const bad = await fetch('http://127.0.0.1:8000/agents/'+agent.agent_id+'/heartbeat',{method:'POST',headers:{'Content-Type':'application/json','X-Agent-Token':'invalid'},body:JSON.stringify({status:'healthy',real_db_reachable:true,honeypot_db_reachable:true})});
    assert.equal(bad.status,401);
    await api(`/protections/${protection.id}`,token,{enabled:false},'PATCH');
    const closed = await fetch('http://127.0.0.1:8000/integrations/bank/decision',{method:'POST',headers:{'Content-Type':'application/json','X-Agent-ID':bundle.agent_id,'X-Agent-Token':bundle.agent_token},body:JSON.stringify({session_id:crypto.randomUUID(),operation:'get_accounts'})});
    assert.equal(closed.status,503);
    await api(`/protections/${protection.id}`,token,{enabled:true},'PATCH');
    check('Cross-tenant reads/writes/rotation/analysis denied; invalid heartbeat denied; paused integration fails closed');

    for (const width of [1440,390]) {
      await page.setViewportSize({width,height:1000});
      for (const route of ['/dashboard',detailRoute,'/dashboard/protection','/dashboard/agent','/onboarding/agent','/onboarding/activation']) {
        await page.goto('http://localhost:3000'+route); await page.locator('main h1, main h2').first().waitFor(); await wait(400);
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1), `Overflow ${width} ${route}`);
      }
      await page.goto('http://localhost:3000'+detailRoute); await page.getByRole('heading',{name:'Attack timeline',exact:true}).waitFor();
      await page.screenshot({path:path.join(output,`incident-${width}.png`),fullPage:true});
    }
    assert.deepEqual(errors,[]);
    check('Desktop/mobile activation, deployment, SOC, incident investigation; no browser errors or horizontal overflow');
    await context.close(); await browser.close(); browser = null;

    const restartBefore = snapshot();
    compose(bank,['restart','bank-api']); compose(layer,['restart','backend']);
    await wait(12000); await active(token);
    assert.deepEqual(snapshot(),restartBefore);
    assert.deepEqual((await api(`/incidents/${incident.incident_id}/timeline`,token)).timeline,timeline.timeline);
    assert.equal((await api('/incidents/'+incident.incident_id,token)).analysis.analysis_provider,'mock');
    check('Restart recovery: same tenant/agent, health reactivation, persisted incident/timeline/mock analysis and unchanged databases/audits');
  } finally {
    if (browser) await browser.close();
    try {
      // Exact QA bank session prefixes and recorded baseline UUIDs only. No rows in business tables.
      const cleanup = `import json,sys\nfrom app.main import real_database,honeypot_database\nm=json.load(sys.stdin)\nfor db in (real_database,honeypot_database):\n with db.transaction() as cursor:\n  for sid in m['baseline_sessions']:\n   cursor.execute(db.adapt('DELETE FROM gateway_audit WHERE session_id = ?'),(sid,))\n  for aid in m['agents']:\n   from uuid import UUID\n   UUID(aid)\n   cursor.execute(db.adapt('DELETE FROM gateway_audit WHERE session_id LIKE ?'),('bank:'+aid+':%',))\nprint('Removed manifest-owned QA bank audits only')`;
      execute('docker',['compose','exec','-T','bank-api','python','-c',cleanup],bank,JSON.stringify(manifest));
      report.cleanup = execute('docker',['compose','run','--rm','--no-deps','-v',layer+'/backend:/app','backend','python','-m','scripts.cleanup_customer_qa'],layer,JSON.stringify(manifest));
      cleanupOK = true;
    } finally {
      if (initial && fs.existsSync(path.join(bank,'.env.integration-backup'))) {
        execute('python',['scripts/connect.py','restore'],bank);
      }
      fs.writeFileSync(path.join(bank,'.env'),original,{mode:0o600});
      compose(bank,['up','-d','--wait','bank-api']);
      compose(layer,['restart','backend']);
      await wait(12000);
      if (initial && cleanupOK) assert.deepEqual(snapshot(),initial,'Presentation datasets AND audits must be restored exactly');
      report.cleanup_complete = cleanupOK;
      fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2),{mode:0o600});
      if (cleanupOK) for (const file of ['bank.env.backup','integration.json']) {
        const name=path.join(output,file); if(fs.existsSync(name)) fs.unlinkSync(name);
      }
      console.log('Evidence and cleanup manifest:',output);
    }
  }
  check('QA tenants/events/incidents/sessions/audits removed; original bank credential and all presentation fingerprints restored');
})().catch(error=>{console.error(error);process.exitCode=1;});
