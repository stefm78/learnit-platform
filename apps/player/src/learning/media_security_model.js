(()=>{
  'use strict';

  const ALLOWED_TAGS=new Set([
    'svg','g','path','rect','circle','ellipse','line','polyline','polygon','text','tspan',
    'defs','lineargradient','radialgradient','stop','clippath','mask','title','desc'
  ]);
  const ALLOWED_ATTRS=new Set([
    'xmlns','viewbox','preserveaspectratio','width','height','x','y','x1','y1','x2','y2',
    'cx','cy','r','rx','ry','points','d','fill','stroke','stroke-width','stroke-linecap',
    'stroke-linejoin','stroke-dasharray','stroke-dashoffset','opacity','fill-opacity',
    'stroke-opacity','transform','font-size','font-family','font-weight','text-anchor',
    'dominant-baseline','offset','stop-color','stop-opacity','clip-path','mask',
    'gradientunits','gradienttransform','id'
  ]);
  const URL_VALUE_ATTRS=new Set(['fill','stroke','clip-path','mask']);
  const DATA_IMAGE=/^data:image\/(?:png|jpe?g|webp|gif);base64,[a-z0-9+/=\s]+$/i;
  const MAX_DATA_URL_CHARS=5_000_000;
  const MAX_REMOTE_URL_CHARS=4096;

  function text(value){return String(value==null?'':value);}
  function safeFragmentReference(value){return /^url\(\s*#[A-Za-z_][\w:.-]*\s*\)$/i.test(value);}
  function unsafeAttributeValue(name,value){
    const lower=text(value).trim().toLowerCase();
    if(/[\u0000-\u001f\u007f]/.test(lower))return true;
    if(/(?:javascript|vbscript|data|https?|file|blob)\s*:/i.test(lower))return true;
    if(/url\s*\(/i.test(lower))return !(URL_VALUE_ATTRS.has(name)&&safeFragmentReference(value));
    return false;
  }

  function sanitizeSvg(source,options={}){
    const raw=text(source).trim();
    const result={ok:false,svg:'',reason:'',removedElements:[],removedAttributes:[],changed:false};
    if(!/^<svg(?:\s|>)/i.test(raw)){result.reason='missing-svg-root';return Object.freeze(result);}
    if(typeof DOMParser!=='function'||typeof XMLSerializer!=='function'){result.reason='xml-parser-unavailable';return Object.freeze(result);}
    let doc;
    try{doc=new DOMParser().parseFromString(raw,'image/svg+xml');}
    catch(error){result.reason='svg-parse-failed';return Object.freeze(result);}
    if(!doc||doc.querySelector('parsererror')){result.reason='svg-parse-failed';return Object.freeze(result);}
    const root=doc.documentElement;
    if(!root||String(root.localName||'').toLowerCase()!=='svg'){result.reason='missing-svg-root';return Object.freeze(result);}

    const elements=[...root.querySelectorAll('*')];
    for(const element of elements){
      const tag=String(element.localName||'').toLowerCase();
      if(!ALLOWED_TAGS.has(tag)){
        result.removedElements.push(tag||'unknown');
        element.remove();
      }
    }
    for(const element of [root,...root.querySelectorAll('*')]){
      for(const attribute of [...element.attributes]){
        const name=String(attribute.name||'').toLowerCase();
        const value=text(attribute.value);
        const eventHandler=name.startsWith('on');
        const externalReference=name==='href'||name==='xlink:href'||name==='src';
        const style=name==='style';
        const allowed=ALLOWED_ATTRS.has(name)||name.startsWith('aria-')||name==='role'||name==='focusable';
        if(eventHandler||externalReference||style||!allowed||(name!=='xmlns'&&unsafeAttributeValue(name,value))){
          result.removedAttributes.push(`${String(element.localName||'svg').toLowerCase()}.${name}`);
          element.removeAttribute(attribute.name);
        }
      }
    }

    root.setAttribute('xmlns','http://www.w3.org/2000/svg');
    root.setAttribute('class','learnit-media-svg');
    root.setAttribute('data-learnit-media','svg');
    root.setAttribute('role','img');
    root.setAttribute('aria-label',text(options.alt||'Visuel pédagogique').slice(0,300));
    root.setAttribute('focusable','false');
    const serialized=new XMLSerializer().serializeToString(root);
    result.svg=serialized;
    result.changed=result.removedElements.length>0||result.removedAttributes.length>0;
    result.ok=!!serialized&&!result.changed;
    result.reason=result.ok?'safe-svg':(serialized?'unsafe-svg-content-removed':'svg-empty');
    return Object.freeze(result);
  }

  function safeImageSource(source){
    const raw=text(source).trim();
    if(!raw)return Object.freeze({ok:false,src:'',kind:'none',reason:'missing-source'});
    if(/^data:/i.test(raw)){
      if(raw.length>MAX_DATA_URL_CHARS)return Object.freeze({ok:false,src:'',kind:'data',reason:'data-url-too-large'});
      if(!DATA_IMAGE.test(raw))return Object.freeze({ok:false,src:'',kind:'data',reason:'data-image-type-or-encoding-rejected'});
      return Object.freeze({ok:true,src:raw,kind:'data-raster',reason:'safe-data-raster'});
    }
    if(raw.length>MAX_REMOTE_URL_CHARS)return Object.freeze({ok:false,src:'',kind:'remote',reason:'remote-url-too-long'});
    let url;
    try{url=new URL(raw,document.baseURI);}
    catch(error){return Object.freeze({ok:false,src:'',kind:'remote',reason:'invalid-url'});}
    if(url.protocol!=='https:')return Object.freeze({ok:false,src:'',kind:'remote',reason:'https-required'});
    if(url.username||url.password)return Object.freeze({ok:false,src:'',kind:'remote',reason:'credentials-forbidden'});
    return Object.freeze({ok:true,src:url.href,kind:'https',reason:'safe-https-image'});
  }

  function auditAsset(asset){
    const value=asset&&typeof asset==='object'?asset:{};
    const data=text(value.data||value.src||value.url||value.source_url||'').trim();
    const format=text(value.format).toLowerCase();
    if(format==='svg'||/^<svg(?:\s|>)/i.test(data)){
      const result=sanitizeSvg(data,{alt:value.alt||value.caption||'Visuel pédagogique'});
      return Object.freeze({ok:result.ok,kind:'svg',reason:result.reason,changed:result.changed,removedElements:result.removedElements,removedAttributes:result.removedAttributes});
    }
    const image=safeImageSource(data);
    return Object.freeze({ok:image.ok,kind:image.kind,reason:image.reason,changed:false,removedElements:[],removedAttributes:[]});
  }

  function selfTest(){
    const safe=sanitizeSvg('<svg viewBox="0 0 10 10"><rect width="10" height="10" fill="#fff"/></svg>',{alt:'test'});
    const unsafe=sanitizeSvg('<svg onload="alert(1)"><scr'+'ipt>alert(1)</scr'+'ipt><rect style="fill:red"/></svg>');
    const raster=safeImageSource('data:image/png;base64,iVBORw0KGgo=');
    const svgData=safeImageSource('data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=');
    return Object.freeze({ok:safe.ok&&!unsafe.ok&&unsafe.changed&&raster.ok&&!svgData.ok,safe,unsafe,raster,svgData});
  }

  window.LearnItMediaSecurityModel=Object.freeze({
    schema:'learnit.media_security.rc684.v1',
    policy:Object.freeze({svg:'allowlist-fail-closed',remoteImages:'https-only-no-credentials',dataImages:'base64-raster-only',maxDataUrlChars:MAX_DATA_URL_CHARS}),
    sanitizeSvg,safeImageSource,auditAsset,selfTest
  });
})();
