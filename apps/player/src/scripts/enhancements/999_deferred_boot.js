/* Final boot after all render enhancers are installed. */
(function(){
  'use strict';
  if(window.__LEARNIT_BOOT_DONE__)return;
  window.__LEARNIT_BOOT_DONE__=true;
  if(typeof window.__LEARNIT_DEFERRED_BOOT__==='function'){
    window.__LEARNIT_DEFERRED_BOOT__();
  }
})();
