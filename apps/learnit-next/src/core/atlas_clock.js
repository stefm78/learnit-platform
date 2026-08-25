'use strict';
const RX=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;
function fail(code){const e=new Error(code);e.code=code;throw e;}
function assertCanonicalTimestamp(value){
  if(typeof value!=='string'||!RX.test(value))fail('NON_CANONICAL_TIMESTAMP');
  const ms=Date.parse(value);if(!Number.isFinite(ms)||new Date(ms).toISOString()!==value)fail('NON_CANONICAL_TIMESTAMP');return value;
}
class ControlledAtlasClock{constructor(initial){this.current=assertCanonicalTimestamp(initial);}now(){return this.current;}set(value){this.current=assertCanonicalTimestamp(value);return this.current;}advance(milliseconds){if(!Number.isInteger(milliseconds))fail('INVALID_CLOCK_DELTA');this.current=new Date(Date.parse(this.current)+milliseconds).toISOString();return this.current;}}
class SystemAtlasClock{now(){return new Date().toISOString();}}
module.exports=Object.freeze({assertCanonicalTimestamp,ControlledAtlasClock,SystemAtlasClock});
