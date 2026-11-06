/**
 * Candidate V6 Parcours persistence adapter. A synthetic origin only until
 * integration/upgrade behaviour has been independently qualified.
 * Each commit is a single IndexedDB READWRITE transaction and only resolves
 * after transaction completion; stale revisions return false, never overwrite.
 */
export function createV6AssistanceIndexedDbCAS({ dbName, storeName='v6-assistance-journal' } = {}) {
  if (typeof dbName !== 'string' || !/^[a-zA-Z0-9._-]{3,80}$/.test(dbName))
    throw new TypeError('ISOLATED_DATABASE_NAME_REQUIRED');
  if (typeof indexedDB === 'undefined') throw new Error('INDEXEDDB_UNAVAILABLE');
  function connect() {
    return new Promise((resolve,reject) => {
      const request=indexedDB.open(dbName,1);
      request.onupgradeneeded=()=>{const db=request.result;if(!db.objectStoreNames.contains(storeName))db.createObjectStore(storeName)};
      request.onsuccess=()=>resolve(request.result);
      request.onerror=()=>reject(request.error||Error('IDB_OPEN_FAILED'));
      request.onblocked=()=>reject(Error('IDB_OPEN_BLOCKED'));
    });
  }
  async function read(key) {
    const db=await connect();
    try {
      return await new Promise((resolve,reject) => {
        const tx=db.transaction(storeName,'readonly'),q=tx.objectStore(storeName).get(key);
        let row;
        q.onsuccess=()=>{row=q.result};
        tx.oncomplete=()=>resolve(row??{version:0,state:null});
        tx.onerror=()=>reject(tx.error||Error('IDB_READ_FAILED'));
        tx.onabort=()=>reject(tx.error||Error('IDB_READ_ABORT'));
      });
    } finally {db.close()}
  }
  async function compareAndSwap(key, expectedVersion, state) {
    if (!Number.isSafeInteger(expectedVersion) || expectedVersion<0) throw new TypeError('INVALID_EXPECTED_VERSION');
    const db=await connect();
    try {
      return await new Promise((resolve,reject) => {
        const tx=db.transaction(storeName,'readwrite');
        const store=tx.objectStore(storeName);
        let applied=false;
        const q=store.get(key);
        q.onsuccess=()=>{
          const prior=q.result;
          if((prior?.version??0)!==expectedVersion) return;
          store.put({version:expectedVersion+1,state},key);
          applied=true;
        };
        tx.oncomplete=()=>resolve(applied);
        tx.onerror=()=>reject(tx.error||Error('IDB_COMMIT_FAILED'));
        tx.onabort=()=>reject(tx.error||Error('IDB_COMMIT_ABORT'));
      });
    } finally {db.close()}
  }
  return Object.freeze({read,compareAndSwap});
}
