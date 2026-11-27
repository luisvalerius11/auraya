/* ============================================================
   AURAYA VILLAS — display currencies for the ROI model (/roi/) and the
   payment plan simulator (/plan/).

   All transactions are in rupiah; other currencies are indicative only.
   Rates are fixed here and updated by hand: IDR per one unit of each currency.
   USD matches the brochure price list. The others were worked out from that
   rate and the market rate of each currency against the US dollar on the
   AS_OF date (AUD 0.664, EUR 1.095, GBP 1.311 per USD).
   To update: change the numbers and the AS_OF date below.

   The visitor's choice is kept in this browser tab only (sessionStorage
   "auraya_cur"), so it carries between the ROI model and the simulator,
   and in the page link as ?cur=aud.
   ============================================================ */
(function(){
  var AS_OF = '27 November 2026';
  var LIST = [
    { code:'IDR', rate:1,     prefix:'Rp ', name:'Indonesian rupiah' },
    { code:'USD', rate:17800, prefix:'$',   name:'US dollar' },
    { code:'AUD', rate:11810, prefix:'A$',  name:'Australian dollar' },
    { code:'EUR', rate:19490, prefix:'€',   name:'Euro' },
    { code:'GBP', rate:23320, prefix:'£',   name:'British pound' }
  ];
  var KEY = 'auraya_cur';
  function find(code){ code = String(code || '').toUpperCase(); for (var i = 0; i < LIST.length; i++) if (LIST[i].code === code) return LIST[i]; return null; }
  function group(n, sep){ return Math.round(Math.abs(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, sep); }
  function dots(n){ return group(n, '.'); }

  window.AurayaFX = {
    asOf: AS_OF,
    list: LIST,
    find: find,
    /* the currency to start with: ?cur= in the link, then this tab's last choice, then the page default */
    initial: function(def){
      var q = null; try { q = new URLSearchParams(location.search).get('cur'); } catch(e){}
      var s = null; try { s = sessionStorage.getItem(KEY); } catch(e){}
      return (find(q) || find(s) || find(def) || LIST[0]).code;
    },
    remember: function(code){ try { sessionStorage.setItem(KEY, code); } catch(e){} },
    /* format an amount given in rupiah in the chosen currency */
    fromIDR: function(idr, code){
      var c = find(code) || LIST[0], v = idr / c.rate;
      return (v < 0 ? '−' : '') + c.prefix + (c.code === 'IDR' ? dots(v) : group(v, ','));
    },
    /* compact form for headline figures: Rp 5,31 B, Rp 576 M, $298,090 */
    short: function(idr, code){
      var c = find(code) || LIST[0];
      if (c.code !== 'IDR') return window.AurayaFX.fromIDR(idr, code);
      var a = Math.abs(idr), sign = idr < 0 ? '−' : '';
      if (a >= 1e9) return sign + 'Rp ' + (a/1e9).toFixed(2).replace('.', ',') + ' B';
      if (a >= 1e6) return sign + 'Rp ' + Math.round(a/1e6) + ' M';
      return window.AurayaFX.fromIDR(idr, 'IDR');
    },
    /* "IDR 17.800 per USD", for the notes under the figures */
    rateNote: function(code){
      var c = find(code); if (!c || c.code === 'IDR') return '';
      return 'IDR ' + dots(c.rate) + ' per ' + c.code;
    }
  };
})();
