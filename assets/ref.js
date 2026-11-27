/* ============================================================
   AURAYA VILLAS — who sent this visitor: an agent, a known lead, or neither.
   Loaded on every page, before /assets/analytics.js.

   AGENT LINKS
     Give each agent their own link, e.g.
       https://auraya-villas.com/brochure/?agent=putu
       https://auraya-villas.com/plan/?agent=putu
     On that link every WhatsApp and email button goes to the agent, the
     brochure's last page shows the agent first (Auraya as a small developer
     line), and leads and activity sent to the CRM are tagged agent=putu.
     The link keeps working as the reader moves between brochure, ROI model
     and simulator. Agent links open the simulator (/plan/) directly; for
     everyone else it opens only for a known lead: a /plan/ link without
     ?lid= or ?agent= first shows the investor-pack form on the landing
     page, then opens the simulator once it is sent. An agent ID that is not in the list below is still tagged
     in the CRM, but the contact buttons stay Auraya's.

   KNOWN LEADS
     The investor-pack form gives each lead an ID (lid). Brochure links sent
     after the form carry ?lid=..., so the CRM can tie brochure and simulator
     activity to that lead's row.
   ============================================================ */
(function(){
  /* One line per agent. id: lowercase letters, digits and dashes (used in the link).
     wa: WhatsApp number, country code first, digits only. email and agency are optional. */
  var AGENTS = {
    /* 'putu': { name:'Putu Ayu', agency:'Bali Homes', wa:'6281234567890', email:'putu@balihomes.com' }, */
  };
  /* With an agent link, also show Auraya's own contact as a small line on the brochure's
     last page. Set to false to show the agent only. */
  var SHOW_DEVELOPER_WITH_AGENT = false;
  var DEVELOPER = { name:'Auraya Villas', wa:'6285899530004', email:'sales@auraya-villas.com' };

  var KEY = 'auraya_ref';
  var store = {};
  try { store = JSON.parse(sessionStorage.getItem(KEY) || '{}') || {}; } catch(e){}

  var q; try { q = new URLSearchParams(location.search); } catch(e){ q = null; }
  var agentId = q && q.get('agent'), lid = q && q.get('lid');
  if (agentId && /^[a-z0-9-]{1,40}$/i.test(agentId)) store.agent = agentId.toLowerCase();
  if (lid && /^[\w-]{6,64}$/.test(lid)) store.lid = lid;
  if (!store.sid) store.sid = Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
  function persist(){ try { sessionStorage.setItem(KEY, JSON.stringify(store)); } catch(e){} }
  persist();

  function agent(){ return store.agent && AGENTS[store.agent] ? Object.assign({ id:store.agent }, AGENTS[store.agent]) : null; }

  var Ref = window.AurayaRef = {
    developer: DEVELOPER,
    showDeveloper: SHOW_DEVELOPER_WITH_AGENT,
    get agentId(){ return store.agent || ''; },
    get lid(){ return store.lid || ''; },
    get sid(){ return store.sid; },
    get agent(){ return agent(); },
    /* the person to contact: the agent on an agent link, otherwise Auraya */
    get contact(){ return agent() || DEVELOPER; },
    /* the payment simulator opens for a known lead or anyone on an agent link; others fill in the form first */
    get canPlan(){ return !!(store.lid || store.agent); },
    setLead: function(id){ if (id){ store.lid = id; persist(); } },
    /* ?agent=..&lid=.. for links to other Auraya pages */
    params: function(){
      var p = [];
      if (store.agent) p.push('agent=' + encodeURIComponent(store.agent));
      if (store.lid) p.push('lid=' + encodeURIComponent(store.lid));
      return p.join('&');
    },
    withParams: function(url){
      var p = Ref.params(); if (!p) return url;
      var hash = '', i = url.indexOf('#');
      if (i >= 0){ hash = url.slice(i); url = url.slice(0, i); }
      return url + (url.indexOf('?') >= 0 ? '&' : '?') + p + hash;
    },
    wa: function(text, who){ who = who || Ref.contact; return 'https://api.whatsapp.com/send?phone=' + who.wa + (text ? '&text=' + encodeURIComponent(text) : ''); },
    mail: function(subject, body, who){
      who = who || Ref.contact; if (!who.email) who = DEVELOPER;
      var p = []; if (subject) p.push('subject=' + encodeURIComponent(subject)); if (body) p.push('body=' + encodeURIComponent(body));
      return 'mailto:' + who.email + (p.length ? '?' + p.join('&') : '');
    }
  };

  /* Once the page is ready: carry the agent / lead to links between Auraya pages, and point
     Auraya's contact links at the agent. Links marked data-developer always stay Auraya's. */
  var DEV_WA = new RegExp('(api\\.whatsapp\\.com/send\\?phone=|wa\\.me/)' + DEVELOPER.wa);
  var DEV_MAIL = new RegExp('^mailto:' + DEVELOPER.email.replace(/\./g, '\\.'), 'i');
  function rewrite(root){
    var a = agent(), p = Ref.params();
    (root || document).querySelectorAll('a[href]').forEach(function(el){
      var h = el.getAttribute('href');
      if (p && /^(\/|\.\.\/)?(brochure|plan|roi)\/?([?#].*)?$/.test(h) && h.indexOf('agent=') < 0 && h.indexOf('lid=') < 0) el.setAttribute('href', Ref.withParams(h));
      if (!a || el.hasAttribute('data-developer')) return;
      if (DEV_WA.test(h)) el.setAttribute('href', h.replace(DEVELOPER.wa, a.wa).replace('text=Hi%20Auraya%2C', 'text=Hi%20' + encodeURIComponent(a.name.split(' ')[0]) + '%2C'));
      else if (a.email && DEV_MAIL.test(h)) el.setAttribute('href', h.replace(DEV_MAIL, 'mailto:' + a.email));
    });
  }
  Ref.rewrite = rewrite;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ rewrite(); });
  else rewrite();
})();
