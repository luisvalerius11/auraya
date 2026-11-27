/* ============================================================
   AURAYA VILLAS — analytics and cookie consent, shared by every page
   (landing page, /brochure/ and /roi/ all load this one file).

   Paste your IDs between the quotes. While an ID is empty, that
   tracker is not loaded at all; with both empty, no cookie banner
   is shown either, because nothing would be tracked.
     GA_ID    = Google Analytics 4 measurement ID, e.g. "G-XXXXXXXXXX"
     PIXEL_ID = Meta (Facebook) Pixel ID, e.g. "123456789012345"

   Consent: nothing is loaded and no cookie is set until the visitor
   agrees in the banner. "Analytics" loads Google Analytics;
   "Marketing" loads the Meta Pixel and lets Google use ad signals.
   The choice is kept in this browser (localStorage "auraya_consent")
   for 6 months; any element with data-cookie-settings reopens it.
   Google Consent Mode v2 is set to "denied" until the visitor agrees.

   What is tracked once allowed:
     - every page view, visitors, sessions, scrolling and outbound
       clicks (GA4 does this by itself)
     - contact:            WhatsApp and email links, on any page
     - section_view:       landing page sections scrolled into view
     - brochure_page_view: each brochure page shown, and how the reader got there
     - brochure_page_time: seconds spent on each brochure page
     - brochure_complete:  reader reached the last brochure page
     - roi_line_explain:   ROI table line opened for its explanation
     - roi_model_open:     "See the full calculation" clicked
     - roi_model_change:   an input changed on the ROI model page
     - plan_open / plan_view: simulator opened from a link / simulator page shown
     - plan_change:        an input changed in the payment plan simulator
     - plan_built:         the plan a visitor settled on (sent after a pause in changes)
     - lifestyle_filter / lifestyle_place_open / lifestyle_map_open:
                           the Island Lifestyle page in the brochure

   CRM activity (CRM_URL): with the visitor's "Follow-up" consent, key moments
   are sent to your own n8n webhook, which adds them to the Google Sheet. Only
   for visitors we can name (a lead ID from the investor-pack form) or who came
   through an agent link (see /assets/ref.js); anonymous visitors send nothing.
   Events sent: brochure_open, brochure_key_page (Price List, Payment Timeline,
   ROI Projection, Floorplan), brochure_complete, roi_model_open, plan_open,
   plan_built (the plan they settled on), plan_print, contact.
   Setup and the fields sent: _notes/crm-activity.md
   ============================================================ */
(function(){
  var GA_ID = "";
  var PIXEL_ID = "";
  /* n8n production webhook for activity, e.g. "https://valenira.app.n8n.cloud/webhook/...".
     Use a NEW webhook, not the investor-pack one, or every event would be treated as a new lead. */
  var CRM_URL = "";

  var KEY = 'auraya_consent', VERSION = 2, MAX_AGE = 182 * 24 * 3600 * 1000;
  var configured = !!(GA_ID || PIXEL_ID || CRM_URL);

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function(){ window.dataLayer.push(arguments); };
  /* Consent Mode v2: everything denied until the visitor chooses */
  gtag('consent', 'default', { analytics_storage:'denied', ad_storage:'denied', ad_user_data:'denied', ad_personalization:'denied' });

  var gaLoaded = false, pixelLoaded = false, consent = { analytics:false, marketing:false, followup:false };
  /* events from before the visitor chose: held in memory, sent only if they agree, dropped otherwise */
  var decided = false, pending = [];

  function loadGA(){
    if (gaLoaded || !GA_ID) return;
    gaLoaded = true;
    var g = document.createElement('script');
    g.async = true; g.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(g);
    gtag('js', new Date());
    gtag('config', GA_ID);
  }
  function loadPixel(){
    if (pixelLoaded || !PIXEL_ID) return;
    pixelLoaded = true;
    !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
    n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
    n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
    t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,
    document,'script','https://connect.facebook.net/en_US/fbevents.js');
    fbq('consent', 'grant');
    fbq('init', PIXEL_ID); fbq('track', 'PageView');
  }
  /* remove Google Analytics cookies after a visitor withdraws consent */
  function clearGACookies(){
    var host = location.hostname, parts = host.split('.'), domains = ['', host];
    for (var i = 1; i < parts.length - 1; i++) domains.push('.' + parts.slice(i).join('.'));
    document.cookie.split(';').forEach(function(c){
      var name = c.split('=')[0].trim();
      if (!/^_ga(_|$)|^_gid$|^_gat/.test(name)) return;
      domains.forEach(function(d){ document.cookie = name + '=; Max-Age=0; path=/' + (d ? '; domain=' + d : ''); });
    });
  }

  function apply(c){
    consent = { analytics:!!c.analytics, marketing:!!c.marketing, followup:!!c.followup };
    gtag('consent', 'update', {
      analytics_storage: consent.analytics ? 'granted' : 'denied',
      ad_storage:         consent.marketing ? 'granted' : 'denied',
      ad_user_data:       consent.marketing ? 'granted' : 'denied',
      ad_personalization: consent.marketing ? 'granted' : 'denied'
    });
    if (consent.analytics) loadGA(); else clearGACookies();
    if (consent.marketing) loadPixel();
    else if (pixelLoaded && window.fbq) fbq('consent', 'revoke');
    decided = true;
    var held = pending; pending = [];
    held.forEach(function(e){ window.track(e[0], e[1], e[2]); });
  }
  function saved(){
    try{
      var c = JSON.parse(localStorage.getItem(KEY) || 'null');
      if (c && c.v === VERSION && Date.now() - c.at < MAX_AGE) return c;
    }catch(e){}
    return null;
  }
  function save(c){
    try{ localStorage.setItem(KEY, JSON.stringify({ v:VERSION, at:Date.now(), analytics:!!c.analytics, marketing:!!c.marketing, followup:!!c.followup })); }catch(e){}
    apply(c);
  }

  /* Which part of the site this is: "landing", "brochure", "roi" or "plan" */
  var area = (location.pathname.match(/\/(brochure|roi|plan)(\/|$)/) || [, 'landing'])[1];

  /* track(gaEvent, pixelEvent, params): one call reports to whichever trackers the visitor allowed.
     pixelEvent may be null for events the Pixel does not need. */
  window.track = function(gaEvent, pixelEvent, params){
    params = params || {};
    if (!('site_area' in params)) params.site_area = area;
    if (!decided && configured){ if (pending.length < 100) pending.push([gaEvent, pixelEvent, params]); return; }
    if (GA_ID && consent.analytics) gtag('event', gaEvent, params);
    if (PIXEL_ID && consent.marketing && pixelEvent && window.fbq) fbq('track', pixelEvent, params);
    if (CRM_URL && consent.followup) toCRM(gaEvent, params);
  };

  /* ---------------- CRM activity ---------------- */
  var KEY_PAGES = { 'Price List':1, 'Payment Timeline':1, 'ROI Projection':1, 'Floorplan':1 };
  var crmOnce = {};
  function toCRM(ev, params){
    var ref = window.AurayaRef;
    if (!ref || !(ref.lid || ref.agentId)) return;          /* only leads we know, or agent links */
    var name = ev, d = {};
    if (ev === 'brochure_page_view'){
      if (!crmOnce.open){ crmOnce.open = 1; send('brochure_open', {}); }
      if (!KEY_PAGES[params.page_name] || crmOnce['p' + params.page_name]) return;
      crmOnce['p' + params.page_name] = 1; name = 'brochure_key_page'; d.detail = params.page_name;
    }
    else if (ev === 'plan_view'){ if (crmOnce.plan) return; crmOnce.plan = 1; name = 'plan_open'; }
    else if (ev === 'brochure_complete' || ev === 'roi_model_open' || ev === 'plan_print'){ if (crmOnce[ev]) return; crmOnce[ev] = 1; }
    else if (ev === 'contact') d.detail = params.method;
    else if (ev === 'plan_built'){ for (var k in params) if (k !== 'site_area') d[k] = params[k]; }
    else return;
    send(name, d);
  }
  function send(name, d){
    var ref = window.AurayaRef, body = new URLSearchParams();
    var row = { event:name, lid:ref.lid, agent:ref.agentId, session:ref.sid, area:area,
      page:location.pathname, sent_at:new Date().toISOString() };
    for (var k in d) row[k] = d[k];
    for (var j in row) body.append(j, row[j] == null ? '' : String(row[j]));
    try { if (navigator.sendBeacon && navigator.sendBeacon(CRM_URL, body)) return; } catch(e){}
    try { fetch(CRM_URL, { method:'POST', mode:'no-cors', body:body, keepalive:true }); } catch(e){}
  }

  /* Contact links anywhere on the site */
  document.addEventListener('click', function(e){
    var a = e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var h = a.getAttribute('href') || '';
    if (/api\.whatsapp\.com|wa\.me\//.test(h)) window.track('contact', 'Contact', { method:'whatsapp' });
    else if (/^mailto:/i.test(h)) window.track('contact', 'Contact', { method:'email' });
  }, true);

  /* ---------------- cookie banner ---------------- */
  var CSS = [
    '.ck{position:fixed;z-index:2147483000;left:20px;bottom:20px;width:min(420px,calc(100vw - 40px));box-sizing:border-box;',
    'background:#2f2820;color:#efe9d9;border-radius:6px;padding:22px 22px 18px;box-shadow:0 18px 50px -12px rgba(20,14,6,.55);',
    "font:300 14px/1.55 'Jost','Helvetica Neue',Arial,sans-serif;-webkit-font-smoothing:antialiased;}",
    '.ck *{box-sizing:border-box;}',
    ".ck h2{margin:0 0 8px;font:500 13px/1.3 'Cinzel',Georgia,serif;letter-spacing:.16em;text-transform:uppercase;color:#fff;}",
    '.ck p{margin:0;color:#d9d1bb;}',
    '.ck p a{color:#efe9d9;text-decoration:underline;text-underline-offset:3px;}',
    '.ck-btns{display:flex;gap:8px;margin-top:16px;flex-wrap:wrap;}',
    '.ck-btn{flex:1 1 0;min-width:110px;min-height:44px;padding:0 14px;border-radius:3px;cursor:pointer;font-family:inherit;font-weight:500;font-size:11.5px;line-height:1;',
    'letter-spacing:.16em;text-transform:uppercase;border:1px solid rgba(239,233,217,.6);background:transparent;color:#efe9d9;transition:background .2s,color .2s;}',
    '.ck-btn:hover{background:rgba(239,233,217,.12);}',
    '.ck-btn.solid{background:#efe9d9;color:#2b2218;border-color:#efe9d9;}',
    '.ck-btn.solid:hover{background:#fff;}',
    '.ck-link{display:inline-block;margin-top:12px;padding:6px 0;background:none;border:0;cursor:pointer;color:#cfc7b3;font:inherit;font-size:13px;',
    'text-decoration:underline;text-underline-offset:3px;}',
    '.ck-link:hover{color:#fff;}',
    '.ck-opts{margin-top:14px;border-top:1px solid rgba(239,233,217,.2);}',
    '.ck-opt{display:flex;gap:12px;align-items:flex-start;padding:12px 0;border-bottom:1px solid rgba(239,233,217,.2);cursor:pointer;}',
    '.ck-opt input{width:18px;height:18px;margin:2px 0 0;flex:none;accent-color:#b6c26a;}',
    '.ck-opt b{display:block;font-weight:500;color:#fff;}',
    '.ck-opt small{display:block;font-size:12.5px;color:#cfc7b3;}',
    '.ck-opt.fixed{cursor:default;opacity:.8;}',
    '.ck [hidden]{display:none!important;}',
    '.ck button:focus-visible,.ck input:focus-visible{outline:2px solid #b6c26a;outline-offset:2px;}',
    '@media (max-width:520px){.ck{left:12px;right:12px;bottom:12px;width:auto;padding:18px 16px 14px;}}'
  ].join('');

  var box = null;
  function el(tag, cls, text){ var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function close(){ if (box){ box.remove(); box = null; } }
  function open(showOptions){
    if (!configured) return;
    close();
    if (!document.getElementById('ck-css')){ var st = el('style'); st.id = 'ck-css'; st.textContent = CSS; document.head.appendChild(st); }
    var cur = saved() || { analytics:false, marketing:false, followup:false };
    box = el('section', 'ck'); box.setAttribute('role', 'dialog'); box.setAttribute('aria-label', 'Cookie choices');
    box.appendChild(el('h2', null, 'Cookies'));
    var intro = el('p', null, 'We would like to use cookies to see how visitors use this site and to measure our advertising. Nothing is tracked unless you agree. ');
    var pol = el('a', null, 'Privacy policy'); pol.href = '/privacy/#cookies';
    intro.appendChild(pol);
    box.appendChild(intro);

    var opts = el('div', 'ck-opts'); opts.hidden = !showOptions;
    function opt(label, desc, checked, fixed){
      var l = el('label', 'ck-opt' + (fixed ? ' fixed' : ''));
      var i = el('input'); i.type = 'checkbox'; i.checked = checked; i.disabled = !!fixed;
      var t = el('span'); t.appendChild(el('b', null, label)); t.appendChild(el('small', null, desc));
      l.appendChild(i); l.appendChild(t); opts.appendChild(l);
      return i;
    }
    opt('Essential', 'Remembers this choice. Always on.', true, true);
    var an = GA_ID ? opt('Analytics', 'Google Analytics: visits, pages viewed and how the site is used.', cur.analytics) : null;
    var mk = PIXEL_ID ? opt('Marketing', 'Meta Pixel and Google ad signals: measure and improve our ads.', cur.marketing) : null;
    var fu = CRM_URL ? opt('Follow-up', 'If you came through your agent or our investor pack: share which brochure pages and payment plans you look at with them, so they can follow up on what matters to you.', cur.followup) : null;
    box.appendChild(opts);

    var btns = el('div', 'ck-btns');
    var reject = el('button', 'ck-btn', 'Reject all'); reject.type = 'button';
    var accept = el('button', 'ck-btn solid', 'Accept all'); accept.type = 'button';
    var saveBtn = el('button', 'ck-btn solid', 'Save choices'); saveBtn.type = 'button'; saveBtn.hidden = !showOptions;
    if (showOptions) accept.hidden = true;
    reject.addEventListener('click', function(){ save({ analytics:false, marketing:false, followup:false }); close(); });
    accept.addEventListener('click', function(){ save({ analytics:true, marketing:true, followup:true }); close(); });
    saveBtn.addEventListener('click', function(){ save({ analytics:an ? an.checked : false, marketing:mk ? mk.checked : false, followup:fu ? fu.checked : false }); close(); });
    btns.appendChild(reject); btns.appendChild(accept); btns.appendChild(saveBtn);
    box.appendChild(btns);

    if (!showOptions){
      var choose = el('button', 'ck-link', 'Choose which cookies'); choose.type = 'button';
      choose.addEventListener('click', function(){ opts.hidden = false; choose.remove(); accept.hidden = true; saveBtn.hidden = false; (an || mk || fu || saveBtn).focus(); });
      box.appendChild(choose);
    }
    document.body.appendChild(box);
  }

  /* any link or button marked data-cookie-settings reopens the choices */
  document.addEventListener('click', function(e){
    var t = e.target.closest ? e.target.closest('[data-cookie-settings]') : null;
    if (!t) return;
    e.preventDefault(); open(true);
  });
  window.aurayaConsent = { open:function(){ open(true); }, get:function(){ return { analytics:consent.analytics, marketing:consent.marketing, followup:consent.followup }; } };

  /* start: apply a saved choice, or ask */
  var s = saved();
  if (s) apply(s);
  else if (configured){
    if (document.body) open(false);
    else document.addEventListener('DOMContentLoaded', function(){ open(false); });
  }
  /* the cookie-settings links only make sense when something can be tracked */
  if (!configured){
    var hide = function(){ document.querySelectorAll('[data-cookie-settings]').forEach(function(x){ x.style.display = 'none'; }); };
    if (document.body) hide(); else document.addEventListener('DOMContentLoaded', hide);
  }
})();
