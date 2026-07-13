    /* RC713 — durable library persistence owner.
       localStorage remains the synchronous cache; IndexedDB is the durable source
       when file:// or browser privacy settings make localStorage ephemeral. */
    const LIBRARY_REVISION_KEY = 'learnit_library_revision_v1';
    const LIBRARY_PERSISTENCE_META_KEY = 'learnit_library_persistence_meta_v1';
    const DURABLE_LIBRARY_DB_NAME = 'learnit_durable_library_v1';
    const DURABLE_LIBRARY_STORE_NAME = 'snapshots';
    const DURABLE_LIBRARY_RECORD_ID = 'library';

    const durableLibraryStore = (()=>{
      let dbPromise = null;
      let last = {supported:typeof indexedDB!=='undefined',ok:null,operation:'idle',at:null,error:null,revision:0};
      const stamp=(operation,ok,extra={})=>{last={supported:typeof indexedDB!=='undefined',operation,ok:!!ok,at:nowIso(),error:extra.error||null,revision:Number(extra.revision||0)};return {...last};};
      function open(){
        if(typeof indexedDB==='undefined')return Promise.reject(new Error('IndexedDB indisponible'));
        if(dbPromise)return dbPromise;
        dbPromise=new Promise((resolve,reject)=>{
          const request=indexedDB.open(DURABLE_LIBRARY_DB_NAME,1);
          request.onupgradeneeded=()=>{const db=request.result;if(!db.objectStoreNames.contains(DURABLE_LIBRARY_STORE_NAME))db.createObjectStore(DURABLE_LIBRARY_STORE_NAME,{keyPath:'id'});};
          request.onsuccess=()=>resolve(request.result);
          request.onerror=()=>reject(request.error||new Error('Ouverture IndexedDB impossible'));
          request.onblocked=()=>reject(new Error('IndexedDB bloquée par un autre onglet'));
        }).catch(error=>{dbPromise=null;stamp('open',false,{error:String(error&&error.message||error)});throw error;});
        return dbPromise;
      }
      async function read(){
        try{
          const db=await open();
          const value=await new Promise((resolve,reject)=>{const tx=db.transaction(DURABLE_LIBRARY_STORE_NAME,'readonly');const request=tx.objectStore(DURABLE_LIBRARY_STORE_NAME).get(DURABLE_LIBRARY_RECORD_ID);request.onsuccess=()=>resolve(request.result||null);request.onerror=()=>reject(request.error||new Error('Lecture IndexedDB impossible'));});
          stamp('read',true,{revision:value&&value.revision});
          return value;
        }catch(error){stamp('read',false,{error:String(error&&error.message||error)});return null;}
      }
      async function write(snapshot){
        try{
          const db=await open();
          const record={...deepClone(snapshot||{}),id:DURABLE_LIBRARY_RECORD_ID};
          await new Promise((resolve,reject)=>{const tx=db.transaction(DURABLE_LIBRARY_STORE_NAME,'readwrite');tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error||new Error('Écriture IndexedDB impossible'));tx.onabort=()=>reject(tx.error||new Error('Écriture IndexedDB annulée'));tx.objectStore(DURABLE_LIBRARY_STORE_NAME).put(record);});
          return stamp('write',true,{revision:record.revision});
        }catch(error){return stamp('write',false,{error:String(error&&error.message||error),revision:snapshot&&snapshot.revision});}
      }
      async function clear(){
        try{
          const db=await open();
          await new Promise((resolve,reject)=>{const tx=db.transaction(DURABLE_LIBRARY_STORE_NAME,'readwrite');tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error||new Error('Suppression IndexedDB impossible'));tx.objectStore(DURABLE_LIBRARY_STORE_NAME).delete(DURABLE_LIBRARY_RECORD_ID);});
          return stamp('clear',true);
        }catch(error){return stamp('clear',false,{error:String(error&&error.message||error)});}
      }
      function report(){return Object.freeze({...last,db:DURABLE_LIBRARY_DB_NAME,store:DURABLE_LIBRARY_STORE_NAME});}
      return Object.freeze({read,write,clear,report});
    })();
