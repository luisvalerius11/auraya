/* ============================================================
   AURAYA VILLAS — analytics, shared by every page
   (landing page, /brochure/ and /roi/ all load this one file).

   Paste your IDs between the quotes. While an ID is empty, that
   tracker is not loaded at all and nothing is sent anywhere.
     GA_ID    = Google Analytics 4 measurement ID, e.g. "G-XXXXXXXXXX"
     PIXEL_ID = Meta (Facebook) Pixel ID, e.g. "123456789012345"

   What is tracked:
     - every page view, visitors, sessions, scrolling and outbound
       clicks (GA4 does this by itself once GA_ID is set)
     - contact:            WhatsApp and email links, on any page
     - section_view:       landing page sections scrolled into view
     - brochure_page_view: each brochure page shown, and how the reader got there
     - brochure_page_time: seconds spent on each brochure page
     - brochure_complete:  reader reached the last brochure page
     - roi_line_explain:   ROI table line opened for its explanation
     - roi_model_open:     "See the full calculation" clicked
     - roi_model_change:   an input changed on the ROI model page
     - lifestyle_filter / lifestyle_place_open / lifestyle_map_open:
                           the Island Lifestyle page in the brochure
   ============================================================ */
(function(){
  var GA_ID = "";
  var PIXEL_ID = "";

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function(){ window.dataLayer.push(arguments); };

  if (GA_ID){
    var g = document.createElement('script');
    g.async = true; g.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(g);
    gtag('js', new Date());
    gtag('config', GA_ID);
  }
  if (PIXEL_ID){
    !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
    n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
    n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
    t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,
    document,'script','https://connect.facebook.net/en_US/fbevents.js');
    fbq('init', PIXEL_ID); fbq('track', 'PageView');
  }

  /* Which part of the site this is: "landing", "brochure" or "roi" */
  var area = (location.pathname.match(/\/(brochure|roi)(\/|$)/) || [, 'landing'])[1];

  /* track(gaEvent, pixelEvent, params): one call reports to both trackers.
     pixelEvent may be null for events the Pixel does not need. Does nothing while no ID is set. */
  window.track = function(gaEvent, pixelEvent, params){
    params = params || {};
    if (!('site_area' in params)) params.site_area = area;
    if (GA_ID) gtag('event', gaEvent, params);
    if (PIXEL_ID && pixelEvent && window.fbq) fbq('track', pixelEvent, params);
  };

  /* Contact links anywhere on the site */
  document.addEventListener('click', function(e){
    var a = e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var h = a.getAttribute('href') || '';
    if (/api\.whatsapp\.com|wa\.me\//.test(h)) window.track('contact', 'Contact', { method:'whatsapp' });
    else if (/^mailto:/i.test(h)) window.track('contact', 'Contact', { method:'email' });
  }, true);
})();
