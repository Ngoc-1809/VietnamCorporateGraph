(()=>{var Ks=Object.create;var zr=Object.defineProperty;var Zs=Object.getOwnPropertyDescriptor;var Qs=Object.getOwnPropertyNames;var Js=Object.getPrototypeOf,el=Object.prototype.hasOwnProperty;var Fe=(a,n)=>()=>(n||a((n={exports:{}}).exports,n),n.exports);var tl=(a,n,e,t)=>{if(n&&typeof n=="object"||typeof n=="function")for(let r of Qs(n))!el.call(a,r)&&r!==e&&zr(a,r,{get:()=>n[r],enumerable:!(t=Zs(n,r))||t.enumerable});return a};var tt=(a,n,e)=>(e=a!=null?Ks(Js(a)):{},tl(n||!a||!a.__esModule?zr(e,"default",{value:a,enumerable:!0}):e,a));var cn=Fe((xf,Ga)=>{"use strict";var Wt=typeof Reflect=="object"?Reflect:null,Nr=Wt&&typeof Wt.apply=="function"?Wt.apply:function(n,e,t){return Function.prototype.apply.call(n,e,t)},Hn;Wt&&typeof Wt.ownKeys=="function"?Hn=Wt.ownKeys:Object.getOwnPropertySymbols?Hn=function(n){return Object.getOwnPropertyNames(n).concat(Object.getOwnPropertySymbols(n))}:Hn=function(n){return Object.getOwnPropertyNames(n)};function nl(a){console&&console.warn&&console.warn(a)}var Wr=Number.isNaN||function(n){return n!==n};function ce(){ce.init.call(this)}Ga.exports=ce;Ga.exports.once=ol;ce.EventEmitter=ce;ce.prototype._events=void 0;ce.prototype._eventsCount=0;ce.prototype._maxListeners=void 0;var Mr=10;function $n(a){if(typeof a!="function")throw new TypeError('The "listener" argument must be of type Function. Received type '+typeof a)}Object.defineProperty(ce,"defaultMaxListeners",{enumerable:!0,get:function(){return Mr},set:function(a){if(typeof a!="number"||a<0||Wr(a))throw new RangeError('The value of "defaultMaxListeners" is out of range. It must be a non-negative number. Received '+a+".");Mr=a}});ce.init=function(){(this._events===void 0||this._events===Object.getPrototypeOf(this)._events)&&(this._events=Object.create(null),this._eventsCount=0),this._maxListeners=this._maxListeners||void 0};ce.prototype.setMaxListeners=function(n){if(typeof n!="number"||n<0||Wr(n))throw new RangeError('The value of "n" is out of range. It must be a non-negative number. Received '+n+".");return this._maxListeners=n,this};function Ur(a){return a._maxListeners===void 0?ce.defaultMaxListeners:a._maxListeners}ce.prototype.getMaxListeners=function(){return Ur(this)};ce.prototype.emit=function(n){for(var e=[],t=1;t<arguments.length;t++)e.push(arguments[t]);var r=n==="error",i=this._events;if(i!==void 0)r=r&&i.error===void 0;else if(!r)return!1;if(r){var o;if(e.length>0&&(o=e[0]),o instanceof Error)throw o;var s=new Error("Unhandled error."+(o?" ("+o.message+")":""));throw s.context=o,s}var l=i[n];if(l===void 0)return!1;if(typeof l=="function")Nr(l,this,e);else for(var u=l.length,d=Vr(l,u),t=0;t<u;++t)Nr(d[t],this,e);return!0};function Or(a,n,e,t){var r,i,o;if($n(e),i=a._events,i===void 0?(i=a._events=Object.create(null),a._eventsCount=0):(i.newListener!==void 0&&(a.emit("newListener",n,e.listener?e.listener:e),i=a._events),o=i[n]),o===void 0)o=i[n]=e,++a._eventsCount;else if(typeof o=="function"?o=i[n]=t?[e,o]:[o,e]:t?o.unshift(e):o.push(e),r=Ur(a),r>0&&o.length>r&&!o.warned){o.warned=!0;var s=new Error("Possible EventEmitter memory leak detected. "+o.length+" "+String(n)+" listeners added. Use emitter.setMaxListeners() to increase limit");s.name="MaxListenersExceededWarning",s.emitter=a,s.type=n,s.count=o.length,nl(s)}return a}ce.prototype.addListener=function(n,e){return Or(this,n,e,!1)};ce.prototype.on=ce.prototype.addListener;ce.prototype.prependListener=function(n,e){return Or(this,n,e,!0)};function al(){if(!this.fired)return this.target.removeListener(this.type,this.wrapFn),this.fired=!0,arguments.length===0?this.listener.call(this.target):this.listener.apply(this.target,arguments)}function Br(a,n,e){var t={fired:!1,wrapFn:void 0,target:a,type:n,listener:e},r=al.bind(t);return r.listener=e,t.wrapFn=r,r}ce.prototype.once=function(n,e){return $n(e),this.on(n,Br(this,n,e)),this};ce.prototype.prependOnceListener=function(n,e){return $n(e),this.prependListener(n,Br(this,n,e)),this};ce.prototype.removeListener=function(n,e){var t,r,i,o,s;if($n(e),r=this._events,r===void 0)return this;if(t=r[n],t===void 0)return this;if(t===e||t.listener===e)--this._eventsCount===0?this._events=Object.create(null):(delete r[n],r.removeListener&&this.emit("removeListener",n,t.listener||e));else if(typeof t!="function"){for(i=-1,o=t.length-1;o>=0;o--)if(t[o]===e||t[o].listener===e){s=t[o].listener,i=o;break}if(i<0)return this;i===0?t.shift():rl(t,i),t.length===1&&(r[n]=t[0]),r.removeListener!==void 0&&this.emit("removeListener",n,s||e)}return this};ce.prototype.off=ce.prototype.removeListener;ce.prototype.removeAllListeners=function(n){var e,t,r;if(t=this._events,t===void 0)return this;if(t.removeListener===void 0)return arguments.length===0?(this._events=Object.create(null),this._eventsCount=0):t[n]!==void 0&&(--this._eventsCount===0?this._events=Object.create(null):delete t[n]),this;if(arguments.length===0){var i=Object.keys(t),o;for(r=0;r<i.length;++r)o=i[r],o!=="removeListener"&&this.removeAllListeners(o);return this.removeAllListeners("removeListener"),this._events=Object.create(null),this._eventsCount=0,this}if(e=t[n],typeof e=="function")this.removeListener(n,e);else if(e!==void 0)for(r=e.length-1;r>=0;r--)this.removeListener(n,e[r]);return this};function Hr(a,n,e){var t=a._events;if(t===void 0)return[];var r=t[n];return r===void 0?[]:typeof r=="function"?e?[r.listener||r]:[r]:e?il(r):Vr(r,r.length)}ce.prototype.listeners=function(n){return Hr(this,n,!0)};ce.prototype.rawListeners=function(n){return Hr(this,n,!1)};ce.listenerCount=function(a,n){return typeof a.listenerCount=="function"?a.listenerCount(n):$r.call(a,n)};ce.prototype.listenerCount=$r;function $r(a){var n=this._events;if(n!==void 0){var e=n[a];if(typeof e=="function")return 1;if(e!==void 0)return e.length}return 0}ce.prototype.eventNames=function(){return this._eventsCount>0?Hn(this._events):[]};function Vr(a,n){for(var e=new Array(n),t=0;t<n;++t)e[t]=a[t];return e}function rl(a,n){for(;n+1<a.length;n++)a[n]=a[n+1];a.pop()}function il(a){for(var n=new Array(a.length),e=0;e<n.length;++e)n[e]=a[e].listener||a[e];return n}function ol(a,n){return new Promise(function(e,t){function r(o){a.removeListener(n,i),t(o)}function i(){typeof a.removeListener=="function"&&a.removeListener("error",r),e([].slice.call(arguments))}qr(a,n,i,{once:!0}),n!=="error"&&sl(a,r,{once:!0})})}function sl(a,n,e){typeof a.on=="function"&&qr(a,"error",n,e)}function qr(a,n,e,t){if(typeof a.on=="function")t.once?a.once(n,e):a.on(n,e);else if(typeof a.addEventListener=="function")a.addEventListener(n,function r(i){t.once&&a.removeEventListener(n,r),e(i)});else throw new TypeError('The "emitter" argument must be of type EventEmitter. Received type '+typeof a)}});var li=Fe((Ef,si)=>{function fu(a){return!a||typeof a!="object"||typeof a=="function"||Array.isArray(a)||a instanceof Set||a instanceof Map||a instanceof RegExp||a instanceof Date}function oi(a,n){a=a||{};var e={};for(var t in n){var r=a[t],i=n[t];if(!fu(i)){e[t]=oi(r,i);continue}r===void 0?e[t]=i:e[t]=r}return e}si.exports=oi});var qt=Fe((Sf,ui)=>{ui.exports=function(n){return n!==null&&typeof n=="object"&&typeof n.addUndirectedEdgeWithKey=="function"&&typeof n.dropNode=="function"&&typeof n.multi=="boolean"}});var fi=Fe((wf,ci)=>{function di(a){return function(n,e){return n+Math.floor(a()*(e-n+1))}}var hi=di(Math.random);hi.createRandom=di;ci.exports=hi});var mi=Fe((Af,pi)=>{var gu=fi().createRandom;function gi(a){var n=gu(a);return function(e){for(var t=e.length,r=t-1,i=-1;++i<t;){var o=n(i,r),s=e[o];e[o]=e[i],e[i]=s}}}var vi=gi(Math.random);vi.createShuffleInPlace=gi;pi.exports=vi});var Ri=Fe((Df,Di)=>{var vu=li(),pu=qt(),mu=mi(),yu={attributes:{x:"x",y:"y"},center:0,hierarchyAttributes:[],rng:Math.random,scale:1};function ke(a,n,e,t,r){this.wrappedCircle=r||null,this.children={},this.countChildren=0,this.id=a||null,this.next=null,this.previous=null,this.x=n||null,this.y=e||null,r?this.r=1010101:this.r=t||999}ke.prototype.hasChildren=function(){return this.countChildren>0};ke.prototype.addChild=function(a,n){this.children[a]=n,++this.countChildren};ke.prototype.getChild=function(a){if(!this.children.hasOwnProperty(a)){var n=new ke;this.children[a]=n,++this.countChildren}return this.children[a]};ke.prototype.applyPositionToChildren=function(){if(this.hasChildren()){var a=this;for(var n in a.children){var e=a.children[n];e.x+=a.x,e.y+=a.y,e.applyPositionToChildren()}}};function xi(a,n,e){for(var t in n.children){var r=n.children[t];r.hasChildren()?xi(a,r,e):e[r.id]={x:r.x,y:r.y}}}function Kn(a,n){var e=a.r-n.r,t=n.x-a.x,r=n.y-a.y;return e<0||e*e<t*t+r*r}function Ti(a,n){var e=a.r-n.r+1e-6,t=n.x-a.x,r=n.y-a.y;return e>0&&e*e>t*t+r*r}function Oa(a,n){for(var e=0;e<n.length;++e)if(!Ti(a,n[e]))return!1;return!0}function bu(a){return new ke(null,a.x,a.y,a.r)}function pn(a,n){var e=a.x,t=a.y,r=a.r,i=n.x,o=n.y,s=n.r,l=i-e,u=o-t,d=s-r,h=Math.sqrt(l*l+u*u);return new ke(null,(e+i+l/h*d)/2,(t+o+u/h*d)/2,(h+r+s)/2)}function Ei(a,n,e){var t=a.x,r=a.y,i=a.r,o=n.x,s=n.y,l=n.r,u=e.x,d=e.y,h=e.r,c=t-o,f=t-u,g=r-s,y=r-d,m=l-i,v=h-i,p=t*t+r*r-i*i,b=p-o*o-s*s+l*l,T=p-u*u-d*d+h*h,_=f*g-c*y,E=(g*T-y*b)/(_*2)-t,A=(y*m-g*v)/_,w=(f*b-c*T)/(_*2)-r,S=(c*v-f*m)/_,C=A*A+S*S-1,G=2*(i+E*A+w*S),L=E*E+w*w-i*i,N=-(C?(G+Math.sqrt(G*G-4*C*L))/(2*C):L/G);return new ke(null,t+E+A*N,r+w+S*N,N)}function _u(a){switch(a.length){case 1:return bu(a[0]);case 2:return pn(a[0],a[1]);case 3:return Ei(a[0],a[1],a[2]);default:throw new Error("graphology-layout/circlepack: Invalid basis length "+a.length)}}function xu(a,n){var e,t;if(Oa(n,a))return[n];for(e=0;e<a.length;++e)if(Kn(n,a[e])&&Oa(pn(a[e],n),a))return[a[e],n];for(e=0;e<a.length-1;++e)for(t=e+1;t<a.length;++t)if(Kn(pn(a[e],a[t]),n)&&Kn(pn(a[e],n),a[t])&&Kn(pn(a[t],n),a[e])&&Oa(Ei(a[e],a[t],n),a))return[a[e],a[t],n];throw new Error("graphology-layout/circlepack: extendBasis failure !")}function yi(a){var n=a.wrappedCircle,e=a.next.wrappedCircle,t=n.r+e.r,r=(n.x*e.r+e.x*n.r)/t,i=(n.y*e.r+e.y*n.r)/t;return r*r+i*i}function Tu(a,n){var e=0,t=a.slice(),r=a.length,i=[],o,s;for(n(t);e<r;)o=t[e],s&&Ti(s,o)?++e:(i=xu(i,o),s=_u(i),e=0);return s}function bi(a,n,e){var t=a.x-n.x,r,i,o=a.y-n.y,s,l,u=t*t+o*o;u?(i=n.r+e.r,i*=i,l=a.r+e.r,l*=l,i>l?(r=(u+l-i)/(2*u),s=Math.sqrt(Math.max(0,l/u-r*r)),e.x=a.x-r*t-s*o,e.y=a.y-r*o+s*t):(r=(u+i-l)/(2*u),s=Math.sqrt(Math.max(0,i/u-r*r)),e.x=n.x+r*t-s*o,e.y=n.y+r*o+s*t)):(e.x=n.x+e.r,e.y=n.y)}function _i(a,n){var e=a.r+n.r-1e-6,t=n.x-a.x,r=n.y-a.y;return e>0&&e*e>t*t+r*r}function Eu(a,n){var e=a.length;if(e===0)return 0;var t,r,i,o,s,l,u,d,h,c;if(t=a[0],t.x=0,t.y=0,e<=1)return t.r;if(r=a[1],t.x=-r.r,r.x=t.r,r.y=0,e<=2)return t.r+r.r;i=a[2],bi(r,t,i),t=new ke(null,null,null,null,t),r=new ke(null,null,null,null,r),i=new ke(null,null,null,null,i),t.next=i.previous=r,r.next=t.previous=i,i.next=r.previous=t;e:for(l=3;l<e;++l){i=a[l],bi(t.wrappedCircle,r.wrappedCircle,i),i=new ke(null,null,null,null,i),u=r.next,d=t.previous,h=r.wrappedCircle.r,c=t.wrappedCircle.r;do if(h<=c){if(_i(u.wrappedCircle,i.wrappedCircle)){r=u,t.next=r,r.previous=t,--l;continue e}h+=u.wrappedCircle.r,u=u.next}else{if(_i(d.wrappedCircle,i.wrappedCircle)){t=d,t.next=r,r.previous=t,--l;continue e}c+=d.wrappedCircle.r,d=d.previous}while(u!==d.next);for(i.previous=t,i.next=r,t.next=r.previous=r=i,o=yi(t);(i=i.next)!==r;)(s=yi(i))<o&&(t=i,o=s);r=t.next}t=[r.wrappedCircle],i=r;for(var f=1e4;(i=i.next)!==r&&--f!==0;)t.push(i.wrappedCircle);for(i=Tu(t,n),l=0;l<e;++l)t=a[l],t.x-=i.x,t.y-=i.y;return i.r}function Si(a,n){var e=0;if(a.hasChildren()){for(var t in a.children){var r=a.children[t];r.hasChildren()&&(r.r=Si(r,n))}e=Eu(Object.values(a.children),n)}return e}function Su(a,n){Si(a,n);for(var e in a.children){var t=a.children[e];t.applyPositionToChildren()}}function wi(a,n,e){if(!pu(n))throw new Error("graphology-layout/circlepack: the given graph is not a valid graphology instance.");e=vu(e,yu);var t={},r={},i=n.nodes(),o=e.center,s=e.hierarchyAttributes,l=mu.createShuffleInPlace(e.rng),u=e.scale,d=new ke;n.forEachNode(function(m,v){var p=v.size?v.size:1,b=new ke(m,null,null,p),T=d;s.forEach(function(_){var E=v[_];T=T.getChild(E)}),T.addChild(m,b)}),Su(d,l),xi(n,d,t);var h=i.length,c,f,g;for(g=0;g<h;g++){var y=i[g];c=o+u*t[y].x,f=o+u*t[y].y,r[y]={x:c,y:f},a&&(n.setNodeAttribute(y,e.attributes.x,c),n.setNodeAttribute(y,e.attributes.y,f))}return r}var Ai=wi.bind(null,!1);Ai.assign=wi.bind(null,!0);Di.exports=Ai});var Ba=Fe(Zn=>{function wu(a){return typeof a!="number"||isNaN(a)?1:a}function Au(a,n){var e={},t=function(o){return typeof o>"u"?n:o};typeof n=="function"&&(t=n);var r=function(o){return t(o[a])},i=function(){return t(void 0)};return typeof a=="string"?(e.fromAttributes=r,e.fromGraph=function(o,s){return r(o.getNodeAttributes(s))},e.fromEntry=function(o,s){return r(s)}):typeof a=="function"?(e.fromAttributes=function(){throw new Error("graphology-utils/getters/createNodeValueGetter: irrelevant usage.")},e.fromGraph=function(o,s){return t(a(s,o.getNodeAttributes(s)))},e.fromEntry=function(o,s){return t(a(o,s))}):(e.fromAttributes=i,e.fromGraph=i,e.fromEntry=i),e}function Ci(a,n){var e={},t=function(o){return typeof o>"u"?n:o};typeof n=="function"&&(t=n);var r=function(o){return t(o[a])},i=function(){return t(void 0)};return typeof a=="string"?(e.fromAttributes=r,e.fromGraph=function(o,s){return r(o.getEdgeAttributes(s))},e.fromEntry=function(o,s){return r(s)},e.fromPartialEntry=e.fromEntry,e.fromMinimalEntry=e.fromEntry):typeof a=="function"?(e.fromAttributes=function(){throw new Error("graphology-utils/getters/createEdgeValueGetter: irrelevant usage.")},e.fromGraph=function(o,s){var l=o.extremities(s);return t(a(s,o.getEdgeAttributes(s),l[0],l[1],o.getNodeAttributes(l[0]),o.getNodeAttributes(l[1]),o.isUndirected(s)))},e.fromEntry=function(o,s,l,u,d,h,c){return t(a(o,s,l,u,d,h,c))},e.fromPartialEntry=function(o,s,l,u){return t(a(o,s,l,u))},e.fromMinimalEntry=function(o,s){return t(a(o,s))}):(e.fromAttributes=i,e.fromGraph=i,e.fromEntry=i,e.fromMinimalEntry=i),e}Zn.createNodeValueGetter=Au;Zn.createEdgeValueGetter=Ci;Zn.createEdgeWeightGetter=function(a){return Ci(a,wu)}});var Ii=Fe((Cf,Fi)=>{var _e=0,pe=1,le=2,ue=3,rt=4,it=5,he=6,Li=7,Qn=8,ki=9,Du=0,Ru=1,Cu=2,we=0,Ue=1,Le=2,St=3,ut=4,be=5,Pe=6,Ze=7,Qe=8,Pi=3,Xe=10,Lu=3,Re=9,Ha=10;Fi.exports=function(n,e,t){var r,i,o,s,l,u,d,h,c,f,g=e.length,y=t.length,m=n.adjustSizes,v=n.barnesHutTheta*n.barnesHutTheta,p,b,T,_,E,A,w,S=[];for(o=0;o<g;o+=Xe)e[o+rt]=e[o+le],e[o+it]=e[o+ue],e[o+le]=0,e[o+ue]=0;if(n.outboundAttractionDistribution){for(p=0,o=0;o<g;o+=Xe)p+=e[o+he];p/=g/Xe}if(n.barnesHutOptimize){var C=1/0,G=-1/0,L=1/0,N=-1/0,k,I,W;for(o=0;o<g;o+=Xe)C=Math.min(C,e[o+_e]),G=Math.max(G,e[o+_e]),L=Math.min(L,e[o+pe]),N=Math.max(N,e[o+pe]);var F=G-C,x=N-L;for(F>x?(L-=(F-x)/2,N=L+F):(C-=(x-F)/2,G=C+x),S[0+we]=-1,S[0+Ue]=(C+G)/2,S[0+Le]=(L+N)/2,S[0+St]=Math.max(G-C,N-L),S[0+ut]=-1,S[0+be]=-1,S[0+Pe]=0,S[0+Ze]=0,S[0+Qe]=0,r=1,o=0;o<g;o+=Xe)for(i=0,W=Pi;;)if(S[i+be]>=0){e[o+_e]<S[i+Ue]?e[o+pe]<S[i+Le]?k=S[i+be]:k=S[i+be]+Re:e[o+pe]<S[i+Le]?k=S[i+be]+Re*2:k=S[i+be]+Re*3,S[i+Ze]=(S[i+Ze]*S[i+Pe]+e[o+_e]*e[o+he])/(S[i+Pe]+e[o+he]),S[i+Qe]=(S[i+Qe]*S[i+Pe]+e[o+pe]*e[o+he])/(S[i+Pe]+e[o+he]),S[i+Pe]+=e[o+he],i=k;continue}else if(S[i+we]<0){S[i+we]=o;break}else{if(S[i+be]=r*Re,h=S[i+St]/2,c=S[i+be],S[c+we]=-1,S[c+Ue]=S[i+Ue]-h,S[c+Le]=S[i+Le]-h,S[c+St]=h,S[c+ut]=c+Re,S[c+be]=-1,S[c+Pe]=0,S[c+Ze]=0,S[c+Qe]=0,c+=Re,S[c+we]=-1,S[c+Ue]=S[i+Ue]-h,S[c+Le]=S[i+Le]+h,S[c+St]=h,S[c+ut]=c+Re,S[c+be]=-1,S[c+Pe]=0,S[c+Ze]=0,S[c+Qe]=0,c+=Re,S[c+we]=-1,S[c+Ue]=S[i+Ue]+h,S[c+Le]=S[i+Le]-h,S[c+St]=h,S[c+ut]=c+Re,S[c+be]=-1,S[c+Pe]=0,S[c+Ze]=0,S[c+Qe]=0,c+=Re,S[c+we]=-1,S[c+Ue]=S[i+Ue]+h,S[c+Le]=S[i+Le]+h,S[c+St]=h,S[c+ut]=S[i+ut],S[c+be]=-1,S[c+Pe]=0,S[c+Ze]=0,S[c+Qe]=0,r+=4,e[S[i+we]+_e]<S[i+Ue]?e[S[i+we]+pe]<S[i+Le]?k=S[i+be]:k=S[i+be]+Re:e[S[i+we]+pe]<S[i+Le]?k=S[i+be]+Re*2:k=S[i+be]+Re*3,S[i+Pe]=e[S[i+we]+he],S[i+Ze]=e[S[i+we]+_e],S[i+Qe]=e[S[i+we]+pe],S[k+we]=S[i+we],S[i+we]=-1,e[o+_e]<S[i+Ue]?e[o+pe]<S[i+Le]?I=S[i+be]:I=S[i+be]+Re:e[o+pe]<S[i+Le]?I=S[i+be]+Re*2:I=S[i+be]+Re*3,k===I)if(W--){i=k;continue}else{W=Pi;break}S[I+we]=o;break}}if(n.barnesHutOptimize)for(b=n.scalingRatio,o=0;o<g;o+=Xe)for(i=0;;)if(S[i+be]>=0)if(A=Math.pow(e[o+_e]-S[i+Ze],2)+Math.pow(e[o+pe]-S[i+Qe],2),f=S[i+St],4*f*f/A<v){if(T=e[o+_e]-S[i+Ze],_=e[o+pe]-S[i+Qe],m===!0?A>0?(w=b*e[o+he]*S[i+Pe]/A,e[o+le]+=T*w,e[o+ue]+=_*w):A<0&&(w=-b*e[o+he]*S[i+Pe]/Math.sqrt(A),e[o+le]+=T*w,e[o+ue]+=_*w):A>0&&(w=b*e[o+he]*S[i+Pe]/A,e[o+le]+=T*w,e[o+ue]+=_*w),i=S[i+ut],i<0)break;continue}else{i=S[i+be];continue}else{if(u=S[i+we],u>=0&&u!==o&&(T=e[o+_e]-e[u+_e],_=e[o+pe]-e[u+pe],A=T*T+_*_,m===!0?A>0?(w=b*e[o+he]*e[u+he]/A,e[o+le]+=T*w,e[o+ue]+=_*w):A<0&&(w=-b*e[o+he]*e[u+he]/Math.sqrt(A),e[o+le]+=T*w,e[o+ue]+=_*w):A>0&&(w=b*e[o+he]*e[u+he]/A,e[o+le]+=T*w,e[o+ue]+=_*w)),i=S[i+ut],i<0)break;continue}else for(b=n.scalingRatio,s=0;s<g;s+=Xe)for(l=0;l<s;l+=Xe)T=e[s+_e]-e[l+_e],_=e[s+pe]-e[l+pe],m===!0?(A=Math.sqrt(T*T+_*_)-e[s+Qn]-e[l+Qn],A>0?(w=b*e[s+he]*e[l+he]/A/A,e[s+le]+=T*w,e[s+ue]+=_*w,e[l+le]-=T*w,e[l+ue]-=_*w):A<0&&(w=100*b*e[s+he]*e[l+he],e[s+le]+=T*w,e[s+ue]+=_*w,e[l+le]-=T*w,e[l+ue]-=_*w)):(A=Math.sqrt(T*T+_*_),A>0&&(w=b*e[s+he]*e[l+he]/A/A,e[s+le]+=T*w,e[s+ue]+=_*w,e[l+le]-=T*w,e[l+ue]-=_*w));for(c=n.gravity/n.scalingRatio,b=n.scalingRatio,o=0;o<g;o+=Xe)w=0,T=e[o+_e],_=e[o+pe],A=Math.sqrt(Math.pow(T,2)+Math.pow(_,2)),n.strongGravityMode?A>0&&(w=b*e[o+he]*c):A>0&&(w=b*e[o+he]*c/A),e[o+le]-=T*w,e[o+ue]-=_*w;for(b=1*(n.outboundAttractionDistribution?p:1),d=0;d<y;d+=Lu)s=t[d+Du],l=t[d+Ru],h=t[d+Cu],E=Math.pow(h,n.edgeWeightInfluence),T=e[s+_e]-e[l+_e],_=e[s+pe]-e[l+pe],m===!0?(A=Math.sqrt(T*T+_*_)-e[s+Qn]-e[l+Qn],n.linLogMode?n.outboundAttractionDistribution?A>0&&(w=-b*E*Math.log(1+A)/A/e[s+he]):A>0&&(w=-b*E*Math.log(1+A)/A):n.outboundAttractionDistribution?A>0&&(w=-b*E/e[s+he]):A>0&&(w=-b*E)):(A=Math.sqrt(Math.pow(T,2)+Math.pow(_,2)),n.linLogMode?n.outboundAttractionDistribution?A>0&&(w=-b*E*Math.log(1+A)/A/e[s+he]):A>0&&(w=-b*E*Math.log(1+A)/A):n.outboundAttractionDistribution?(A=1,w=-b*E/e[s+he]):(A=1,w=-b*E)),A>0&&(e[s+le]+=T*w,e[s+ue]+=_*w,e[l+le]-=T*w,e[l+ue]-=_*w);var P,U,z,R,j,q;if(m===!0)for(o=0;o<g;o+=Xe)e[o+ki]!==1&&(P=Math.sqrt(Math.pow(e[o+le],2)+Math.pow(e[o+ue],2)),P>Ha&&(e[o+le]=e[o+le]*Ha/P,e[o+ue]=e[o+ue]*Ha/P),U=e[o+he]*Math.sqrt((e[o+rt]-e[o+le])*(e[o+rt]-e[o+le])+(e[o+it]-e[o+ue])*(e[o+it]-e[o+ue])),z=Math.sqrt((e[o+rt]+e[o+le])*(e[o+rt]+e[o+le])+(e[o+it]+e[o+ue])*(e[o+it]+e[o+ue]))/2,R=.1*Math.log(1+z)/(1+Math.sqrt(U)),j=e[o+_e]+e[o+le]*(R/n.slowDown),e[o+_e]=j,q=e[o+pe]+e[o+ue]*(R/n.slowDown),e[o+pe]=q);else for(o=0;o<g;o+=Xe)e[o+ki]!==1&&(U=e[o+he]*Math.sqrt((e[o+rt]-e[o+le])*(e[o+rt]-e[o+le])+(e[o+it]-e[o+ue])*(e[o+it]-e[o+ue])),z=Math.sqrt((e[o+rt]+e[o+le])*(e[o+rt]+e[o+le])+(e[o+it]+e[o+ue])*(e[o+it]+e[o+ue]))/2,R=e[o+Li]*Math.log(1+z)/(1+Math.sqrt(U)),e[o+Li]=Math.min(1,Math.sqrt(R*(Math.pow(e[o+le],2)+Math.pow(e[o+ue],2))/(1+Math.sqrt(U)))),j=e[o+_e]+e[o+le]*(R/n.slowDown),e[o+_e]=j,q=e[o+pe]+e[o+ue]*(R/n.slowDown),e[o+pe]=q);return{}}});var $a=Fe(dt=>{var mn=10,Gi=3;dt.assign=function(a){a=a||{};var n=Array.prototype.slice.call(arguments).slice(1),e,t,r;for(e=0,r=n.length;e<r;e++)if(n[e])for(t in n[e])a[t]=n[e][t];return a};dt.validateSettings=function(a){return"linLogMode"in a&&typeof a.linLogMode!="boolean"?{message:"the `linLogMode` setting should be a boolean."}:"outboundAttractionDistribution"in a&&typeof a.outboundAttractionDistribution!="boolean"?{message:"the `outboundAttractionDistribution` setting should be a boolean."}:"adjustSizes"in a&&typeof a.adjustSizes!="boolean"?{message:"the `adjustSizes` setting should be a boolean."}:"edgeWeightInfluence"in a&&typeof a.edgeWeightInfluence!="number"?{message:"the `edgeWeightInfluence` setting should be a number."}:"scalingRatio"in a&&!(typeof a.scalingRatio=="number"&&a.scalingRatio>=0)?{message:"the `scalingRatio` setting should be a number >= 0."}:"strongGravityMode"in a&&typeof a.strongGravityMode!="boolean"?{message:"the `strongGravityMode` setting should be a boolean."}:"gravity"in a&&!(typeof a.gravity=="number"&&a.gravity>=0)?{message:"the `gravity` setting should be a number >= 0."}:"slowDown"in a&&!(typeof a.slowDown=="number"||a.slowDown>=0)?{message:"the `slowDown` setting should be a number >= 0."}:"barnesHutOptimize"in a&&typeof a.barnesHutOptimize!="boolean"?{message:"the `barnesHutOptimize` setting should be a boolean."}:"barnesHutTheta"in a&&!(typeof a.barnesHutTheta=="number"&&a.barnesHutTheta>=0)?{message:"the `barnesHutTheta` setting should be a number >= 0."}:null};dt.graphToByteArrays=function(a,n){var e=a.order,t=a.size,r={},i,o=new Float32Array(e*mn),s=new Float32Array(t*Gi);return i=0,a.forEachNode(function(l,u){r[l]=i,o[i]=u.x,o[i+1]=u.y,o[i+2]=0,o[i+3]=0,o[i+4]=0,o[i+5]=0,o[i+6]=1,o[i+7]=1,o[i+8]=u.size||1,o[i+9]=u.fixed?1:0,i+=mn}),i=0,a.forEachEdge(function(l,u,d,h,c,f,g){var y=r[d],m=r[h],v=n(l,u,d,h,c,f,g);o[y+6]+=v,o[m+6]+=v,s[i]=y,s[i+1]=m,s[i+2]=v,i+=Gi}),{nodes:o,edges:s}};dt.assignLayoutChanges=function(a,n,e){var t=0;a.updateEachNodeAttributes(function(r,i){return i.x=n[t],i.y=n[t+1],t+=mn,e?e(r,i):i})};dt.readGraphPositions=function(a,n){var e=0;a.forEachNode(function(t,r){n[e]=r.x,n[e+1]=r.y,e+=mn})};dt.collectLayoutChanges=function(a,n,e){for(var t=a.nodes(),r={},i=0,o=0,s=n.length;i<s;i+=mn){if(e){var l=Object.assign({},a.getNodeAttributes(t[o]));l.x=n[i],l.y=n[i+1],l=e(t[o],l),r[t[o]]={x:l.x,y:l.y}}else r[t[o]]={x:n[i],y:n[i+1]};o++}return r};dt.createWorker=function(n){var e=window.URL||window.webkitURL,t=n.toString(),r=e.createObjectURL(new Blob(["("+t+").call(this);"],{type:"text/javascript"})),i=new Worker(r);return e.revokeObjectURL(r),i}});var Va=Fe((kf,zi)=>{zi.exports={linLogMode:!1,outboundAttractionDistribution:!1,adjustSizes:!1,edgeWeightInfluence:1,scalingRatio:1,strongGravityMode:!1,gravity:1,slowDown:1,barnesHutOptimize:!1,barnesHutTheta:.5}});var Wi=Fe((Pf,Mi)=>{var ku=qt(),Pu=Ba().createEdgeWeightGetter,Fu=Ii(),yn=$a(),Iu=Va();function Ni(a,n,e){if(!ku(n))throw new Error("graphology-layout-forceatlas2: the given graph is not a valid graphology instance.");typeof e=="number"&&(e={iterations:e});var t=e.iterations;if(typeof t!="number")throw new Error("graphology-layout-forceatlas2: invalid number of iterations.");if(t<=0)throw new Error("graphology-layout-forceatlas2: you should provide a positive number of iterations.");var r=Pu("getEdgeWeight"in e?e.getEdgeWeight:"weight").fromEntry,i=typeof e.outputReducer=="function"?e.outputReducer:null,o=yn.assign({},Iu,e.settings),s=yn.validateSettings(o);if(s)throw new Error("graphology-layout-forceatlas2: "+s.message);var l=yn.graphToByteArrays(n,r),u;for(u=0;u<t;u++)Fu(o,l.nodes,l.edges);if(a){yn.assignLayoutChanges(n,l.nodes,i);return}return yn.collectLayoutChanges(n,l.nodes)}function Gu(a){var n=typeof a=="number"?a:a.order;return{barnesHutOptimize:n>2e3,strongGravityMode:!0,gravity:.05,scalingRatio:10,slowDown:1+Math.log(n)}}var qa=Ni.bind(null,!1);qa.assign=Ni.bind(null,!0);qa.inferSettings=Gu;Mi.exports=qa});var Oi=Fe((Ff,Ui)=>{Ui.exports=function(){var n,e,t={};(function(){var i=0,o=1,s=2,l=3,u=4,d=5,h=6,c=7,f=8,g=9,y=0,m=1,v=2,p=0,b=1,T=2,_=3,E=4,A=5,w=6,S=7,C=8,G=3,L=10,N=3,k=9,I=10;t.exports=function(F,x,P){var U,z,R,j,q,Z,Se,de,K,Ke,De=x.length,_t=P.length,Ve=F.adjustSizes,Fa=F.barnesHutTheta*F.barnesHutTheta,Gt,ge,oe,se,qe,ee,Y,M=[];for(R=0;R<De;R+=L)x[R+u]=x[R+s],x[R+d]=x[R+l],x[R+s]=0,x[R+l]=0;if(F.outboundAttractionDistribution){for(Gt=0,R=0;R<De;R+=L)Gt+=x[R+h];Gt/=De/L}if(F.barnesHutOptimize){var xt=1/0,zt=-1/0,Tt=1/0,Nt=-1/0,Ne,Mt,Ia;for(R=0;R<De;R+=L)xt=Math.min(xt,x[R+i]),zt=Math.max(zt,x[R+i]),Tt=Math.min(Tt,x[R+o]),Nt=Math.max(Nt,x[R+o]);var Nn=zt-xt,Mn=Nt-Tt;for(Nn>Mn?(Tt-=(Nn-Mn)/2,Nt=Tt+Nn):(xt-=(Mn-Nn)/2,zt=xt+Mn),M[0+p]=-1,M[0+b]=(xt+zt)/2,M[0+T]=(Tt+Nt)/2,M[0+_]=Math.max(zt-xt,Nt-Tt),M[0+E]=-1,M[0+A]=-1,M[0+w]=0,M[0+S]=0,M[0+C]=0,U=1,R=0;R<De;R+=L)for(z=0,Ia=G;;)if(M[z+A]>=0){x[R+i]<M[z+b]?x[R+o]<M[z+T]?Ne=M[z+A]:Ne=M[z+A]+k:x[R+o]<M[z+T]?Ne=M[z+A]+k*2:Ne=M[z+A]+k*3,M[z+S]=(M[z+S]*M[z+w]+x[R+i]*x[R+h])/(M[z+w]+x[R+h]),M[z+C]=(M[z+C]*M[z+w]+x[R+o]*x[R+h])/(M[z+w]+x[R+h]),M[z+w]+=x[R+h],z=Ne;continue}else if(M[z+p]<0){M[z+p]=R;break}else{if(M[z+A]=U*k,de=M[z+_]/2,K=M[z+A],M[K+p]=-1,M[K+b]=M[z+b]-de,M[K+T]=M[z+T]-de,M[K+_]=de,M[K+E]=K+k,M[K+A]=-1,M[K+w]=0,M[K+S]=0,M[K+C]=0,K+=k,M[K+p]=-1,M[K+b]=M[z+b]-de,M[K+T]=M[z+T]+de,M[K+_]=de,M[K+E]=K+k,M[K+A]=-1,M[K+w]=0,M[K+S]=0,M[K+C]=0,K+=k,M[K+p]=-1,M[K+b]=M[z+b]+de,M[K+T]=M[z+T]-de,M[K+_]=de,M[K+E]=K+k,M[K+A]=-1,M[K+w]=0,M[K+S]=0,M[K+C]=0,K+=k,M[K+p]=-1,M[K+b]=M[z+b]+de,M[K+T]=M[z+T]+de,M[K+_]=de,M[K+E]=M[z+E],M[K+A]=-1,M[K+w]=0,M[K+S]=0,M[K+C]=0,U+=4,x[M[z+p]+i]<M[z+b]?x[M[z+p]+o]<M[z+T]?Ne=M[z+A]:Ne=M[z+A]+k:x[M[z+p]+o]<M[z+T]?Ne=M[z+A]+k*2:Ne=M[z+A]+k*3,M[z+w]=x[M[z+p]+h],M[z+S]=x[M[z+p]+i],M[z+C]=x[M[z+p]+o],M[Ne+p]=M[z+p],M[z+p]=-1,x[R+i]<M[z+b]?x[R+o]<M[z+T]?Mt=M[z+A]:Mt=M[z+A]+k:x[R+o]<M[z+T]?Mt=M[z+A]+k*2:Mt=M[z+A]+k*3,Ne===Mt)if(Ia--){z=Ne;continue}else{Ia=G;break}M[Mt+p]=R;break}}if(F.barnesHutOptimize)for(ge=F.scalingRatio,R=0;R<De;R+=L)for(z=0;;)if(M[z+A]>=0)if(ee=Math.pow(x[R+i]-M[z+S],2)+Math.pow(x[R+o]-M[z+C],2),Ke=M[z+_],4*Ke*Ke/ee<Fa){if(oe=x[R+i]-M[z+S],se=x[R+o]-M[z+C],Ve===!0?ee>0?(Y=ge*x[R+h]*M[z+w]/ee,x[R+s]+=oe*Y,x[R+l]+=se*Y):ee<0&&(Y=-ge*x[R+h]*M[z+w]/Math.sqrt(ee),x[R+s]+=oe*Y,x[R+l]+=se*Y):ee>0&&(Y=ge*x[R+h]*M[z+w]/ee,x[R+s]+=oe*Y,x[R+l]+=se*Y),z=M[z+E],z<0)break;continue}else{z=M[z+A];continue}else{if(Z=M[z+p],Z>=0&&Z!==R&&(oe=x[R+i]-x[Z+i],se=x[R+o]-x[Z+o],ee=oe*oe+se*se,Ve===!0?ee>0?(Y=ge*x[R+h]*x[Z+h]/ee,x[R+s]+=oe*Y,x[R+l]+=se*Y):ee<0&&(Y=-ge*x[R+h]*x[Z+h]/Math.sqrt(ee),x[R+s]+=oe*Y,x[R+l]+=se*Y):ee>0&&(Y=ge*x[R+h]*x[Z+h]/ee,x[R+s]+=oe*Y,x[R+l]+=se*Y)),z=M[z+E],z<0)break;continue}else for(ge=F.scalingRatio,j=0;j<De;j+=L)for(q=0;q<j;q+=L)oe=x[j+i]-x[q+i],se=x[j+o]-x[q+o],Ve===!0?(ee=Math.sqrt(oe*oe+se*se)-x[j+f]-x[q+f],ee>0?(Y=ge*x[j+h]*x[q+h]/ee/ee,x[j+s]+=oe*Y,x[j+l]+=se*Y,x[q+s]-=oe*Y,x[q+l]-=se*Y):ee<0&&(Y=100*ge*x[j+h]*x[q+h],x[j+s]+=oe*Y,x[j+l]+=se*Y,x[q+s]-=oe*Y,x[q+l]-=se*Y)):(ee=Math.sqrt(oe*oe+se*se),ee>0&&(Y=ge*x[j+h]*x[q+h]/ee/ee,x[j+s]+=oe*Y,x[j+l]+=se*Y,x[q+s]-=oe*Y,x[q+l]-=se*Y));for(K=F.gravity/F.scalingRatio,ge=F.scalingRatio,R=0;R<De;R+=L)Y=0,oe=x[R+i],se=x[R+o],ee=Math.sqrt(Math.pow(oe,2)+Math.pow(se,2)),F.strongGravityMode?ee>0&&(Y=ge*x[R+h]*K):ee>0&&(Y=ge*x[R+h]*K/ee),x[R+s]-=oe*Y,x[R+l]-=se*Y;for(ge=1*(F.outboundAttractionDistribution?Gt:1),Se=0;Se<_t;Se+=N)j=P[Se+y],q=P[Se+m],de=P[Se+v],qe=Math.pow(de,F.edgeWeightInfluence),oe=x[j+i]-x[q+i],se=x[j+o]-x[q+o],Ve===!0?(ee=Math.sqrt(oe*oe+se*se)-x[j+f]-x[q+f],F.linLogMode?F.outboundAttractionDistribution?ee>0&&(Y=-ge*qe*Math.log(1+ee)/ee/x[j+h]):ee>0&&(Y=-ge*qe*Math.log(1+ee)/ee):F.outboundAttractionDistribution?ee>0&&(Y=-ge*qe/x[j+h]):ee>0&&(Y=-ge*qe)):(ee=Math.sqrt(Math.pow(oe,2)+Math.pow(se,2)),F.linLogMode?F.outboundAttractionDistribution?ee>0&&(Y=-ge*qe*Math.log(1+ee)/ee/x[j+h]):ee>0&&(Y=-ge*qe*Math.log(1+ee)/ee):F.outboundAttractionDistribution?(ee=1,Y=-ge*qe/x[j+h]):(ee=1,Y=-ge*qe)),ee>0&&(x[j+s]+=oe*Y,x[j+l]+=se*Y,x[q+s]-=oe*Y,x[q+l]-=se*Y);var Wn,hn,Un,Et,On,Bn;if(Ve===!0)for(R=0;R<De;R+=L)x[R+g]!==1&&(Wn=Math.sqrt(Math.pow(x[R+s],2)+Math.pow(x[R+l],2)),Wn>I&&(x[R+s]=x[R+s]*I/Wn,x[R+l]=x[R+l]*I/Wn),hn=x[R+h]*Math.sqrt((x[R+u]-x[R+s])*(x[R+u]-x[R+s])+(x[R+d]-x[R+l])*(x[R+d]-x[R+l])),Un=Math.sqrt((x[R+u]+x[R+s])*(x[R+u]+x[R+s])+(x[R+d]+x[R+l])*(x[R+d]+x[R+l]))/2,Et=.1*Math.log(1+Un)/(1+Math.sqrt(hn)),On=x[R+i]+x[R+s]*(Et/F.slowDown),x[R+i]=On,Bn=x[R+o]+x[R+l]*(Et/F.slowDown),x[R+o]=Bn);else for(R=0;R<De;R+=L)x[R+g]!==1&&(hn=x[R+h]*Math.sqrt((x[R+u]-x[R+s])*(x[R+u]-x[R+s])+(x[R+d]-x[R+l])*(x[R+d]-x[R+l])),Un=Math.sqrt((x[R+u]+x[R+s])*(x[R+u]+x[R+s])+(x[R+d]+x[R+l])*(x[R+d]+x[R+l]))/2,Et=x[R+c]*Math.log(1+Un)/(1+Math.sqrt(hn)),x[R+c]=Math.min(1,Math.sqrt(Et*(Math.pow(x[R+s],2)+Math.pow(x[R+l],2))/(1+Math.sqrt(hn)))),On=x[R+i]+x[R+s]*(Et/F.slowDown),x[R+i]=On,Bn=x[R+o]+x[R+l]*(Et/F.slowDown),x[R+o]=Bn);return{}}})();var r=t.exports;self.addEventListener("message",function(i){var o=i.data;n=new Float32Array(o.nodes),o.edges&&(e=new Float32Array(o.edges)),r(o.settings,n,e),self.postMessage({nodes:n.buffer},[n.buffer])})}});var Hi=Fe((If,Bi)=>{var zu=Oi(),Nu=qt(),Mu=Ba().createEdgeWeightGetter,jt=$a(),Wu=Va();function ht(a,n){if(n=n||{},!Nu(a))throw new Error("graphology-layout-forceatlas2/worker: the given graph is not a valid graphology instance.");var e=Mu("getEdgeWeight"in n?n.getEdgeWeight:"weight").fromEntry,t=jt.assign({},Wu,n.settings),r=jt.validateSettings(t);if(r)throw new Error("graphology-layout-forceatlas2/worker: "+r.message);this.worker=null,this.graph=a,this.settings=t,this.getEdgeWeight=e,this.matrices=null,this.running=!1,this.killed=!1,this.outputReducer=typeof n.outputReducer=="function"?n.outputReducer:null,this.handleMessage=this.handleMessage.bind(this);var i=void 0,o=this;this.handleGraphUpdate=function(){o.worker&&o.worker.terminate(),i&&clearTimeout(i),i=setTimeout(function(){i=void 0,o.spawnWorker()},0)},a.on("nodeAdded",this.handleGraphUpdate),a.on("edgeAdded",this.handleGraphUpdate),a.on("nodeDropped",this.handleGraphUpdate),a.on("edgeDropped",this.handleGraphUpdate),this.spawnWorker()}ht.prototype.isRunning=function(){return this.running};ht.prototype.spawnWorker=function(){this.worker&&this.worker.terminate(),this.worker=jt.createWorker(zu),this.worker.addEventListener("message",this.handleMessage),this.running&&(this.running=!1,this.start())};ht.prototype.handleMessage=function(a){if(this.running){var n=new Float32Array(a.data.nodes);jt.assignLayoutChanges(this.graph,n,this.outputReducer),this.outputReducer&&jt.readGraphPositions(this.graph,n),this.matrices.nodes=n,this.askForIterations()}};ht.prototype.askForIterations=function(a){var n=this.matrices,e={settings:this.settings,nodes:n.nodes.buffer},t=[n.nodes.buffer];return a&&(e.edges=n.edges.buffer,t.push(n.edges.buffer)),this.worker.postMessage(e,t),this};ht.prototype.start=function(){if(this.killed)throw new Error("graphology-layout-forceatlas2/worker.start: layout was killed.");return this.running?this:(this.matrices=jt.graphToByteArrays(this.graph,this.getEdgeWeight),this.running=!0,this.askForIterations(!0),this)};ht.prototype.stop=function(){return this.running=!1,this};ht.prototype.kill=function(){if(this.killed)return this;this.running=!1,this.killed=!0,this.matrices=null,this.worker.terminate(),this.graph.removeListener("nodeAdded",this.handleGraphUpdate),this.graph.removeListener("edgeAdded",this.handleGraphUpdate),this.graph.removeListener("nodeDropped",this.handleGraphUpdate),this.graph.removeListener("edgeDropped",this.handleGraphUpdate)};Bi.exports=ht});var Kr=tt(cn(),1);function ll(){let a=arguments[0];for(let n=1,e=arguments.length;n<e;n++)if(arguments[n])for(let t in arguments[n])a[t]=arguments[n][t];return a}var Te=ll;typeof Object.assign=="function"&&(Te=Object.assign);function We(a,n,e,t){let r=a._nodes.get(n),i=null;return r&&(t==="mixed"?i=r.out&&r.out[e]||r.undirected&&r.undirected[e]:t==="directed"?i=r.out&&r.out[e]:i=r.undirected&&r.undirected[e]),i}function Ae(a){return typeof a=="object"&&a!==null}function Zr(a){let n;for(n in a)return!1;return!0}function Me(a,n,e){Object.defineProperty(a,n,{enumerable:!1,configurable:!1,writable:!0,value:e})}function je(a,n,e){let t={enumerable:!0,configurable:!0};typeof e=="function"?t.get=e:(t.value=e,t.writable=!1),Object.defineProperty(a,n,t)}function jr(a){return!(!Ae(a)||a.attributes&&!Array.isArray(a.attributes))}function ul(){let a=Math.floor(Math.random()*256)&255;return()=>a++}function nt(){let a=arguments,n=null,e=-1;return{[Symbol.iterator](){return this},next(){let t=null;do{if(n===null){if(e++,e>=a.length)return{done:!0};n=a[e][Symbol.iterator]()}if(t=n.next(),t.done){n=null;continue}break}while(!0);return t}}}function Ht(){return{[Symbol.iterator](){return this},next(){return{done:!0}}}}var vn=class extends Error{constructor(n){super(),this.name="GraphError",this.message=n}},X=class a extends vn{constructor(n){super(n),this.name="InvalidArgumentsGraphError",typeof Error.captureStackTrace=="function"&&Error.captureStackTrace(this,a.prototype.constructor)}},$=class a extends vn{constructor(n){super(n),this.name="NotFoundGraphError",typeof Error.captureStackTrace=="function"&&Error.captureStackTrace(this,a.prototype.constructor)}},J=class a extends vn{constructor(n){super(n),this.name="UsageGraphError",typeof Error.captureStackTrace=="function"&&Error.captureStackTrace(this,a.prototype.constructor)}};function Qr(a,n){this.key=a,this.attributes=n,this.clear()}Qr.prototype.clear=function(){this.inDegree=0,this.outDegree=0,this.undirectedDegree=0,this.undirectedLoops=0,this.directedLoops=0,this.in={},this.out={},this.undirected={}};function Jr(a,n){this.key=a,this.attributes=n,this.clear()}Jr.prototype.clear=function(){this.inDegree=0,this.outDegree=0,this.directedLoops=0,this.in={},this.out={}};function ei(a,n){this.key=a,this.attributes=n,this.clear()}ei.prototype.clear=function(){this.undirectedDegree=0,this.undirectedLoops=0,this.undirected={}};function $t(a,n,e,t,r){this.key=n,this.attributes=r,this.undirected=a,this.source=e,this.target=t}$t.prototype.attach=function(){let a="out",n="in";this.undirected&&(a=n="undirected");let e=this.source.key,t=this.target.key;this.source[a][t]=this,!(this.undirected&&e===t)&&(this.target[n][e]=this)};$t.prototype.attachMulti=function(){let a="out",n="in",e=this.source.key,t=this.target.key;this.undirected&&(a=n="undirected");let r=this.source[a],i=r[t];if(typeof i>"u"){r[t]=this,this.undirected&&e===t||(this.target[n][e]=this);return}i.previous=this,this.next=i,r[t]=this,this.target[n][e]=this};$t.prototype.detach=function(){let a=this.source.key,n=this.target.key,e="out",t="in";this.undirected&&(e=t="undirected"),delete this.source[e][n],delete this.target[t][a]};$t.prototype.detachMulti=function(){let a=this.source.key,n=this.target.key,e="out",t="in";this.undirected&&(e=t="undirected"),this.previous===void 0?this.next===void 0?(delete this.source[e][n],delete this.target[t][a]):(this.next.previous=void 0,this.source[e][n]=this.next,this.target[t][a]=this.next):(this.previous.next=this.next,this.next!==void 0&&(this.next.previous=this.previous))};var ti=0,ni=1,dl=2,ai=3;function at(a,n,e,t,r,i,o){let s,l,u,d;if(t=""+t,e===ti){if(s=a._nodes.get(t),!s)throw new $(`Graph.${n}: could not find the "${t}" node in the graph.`);u=r,d=i}else if(e===ai){if(r=""+r,l=a._edges.get(r),!l)throw new $(`Graph.${n}: could not find the "${r}" edge in the graph.`);let h=l.source.key,c=l.target.key;if(t===h)s=l.target;else if(t===c)s=l.source;else throw new $(`Graph.${n}: the "${t}" node is not attached to the "${r}" edge (${h}, ${c}).`);u=i,d=o}else{if(l=a._edges.get(t),!l)throw new $(`Graph.${n}: could not find the "${t}" edge in the graph.`);e===ni?s=l.source:s=l.target,u=r,d=i}return[s,u,d]}function hl(a,n,e){a.prototype[n]=function(t,r,i){let[o,s]=at(this,n,e,t,r,i);return o.attributes[s]}}function cl(a,n,e){a.prototype[n]=function(t,r){let[i]=at(this,n,e,t,r);return i.attributes}}function fl(a,n,e){a.prototype[n]=function(t,r,i){let[o,s]=at(this,n,e,t,r,i);return o.attributes.hasOwnProperty(s)}}function gl(a,n,e){a.prototype[n]=function(t,r,i,o){let[s,l,u]=at(this,n,e,t,r,i,o);return s.attributes[l]=u,this.emit("nodeAttributesUpdated",{key:s.key,type:"set",attributes:s.attributes,name:l}),this}}function vl(a,n,e){a.prototype[n]=function(t,r,i,o){let[s,l,u]=at(this,n,e,t,r,i,o);if(typeof u!="function")throw new X(`Graph.${n}: updater should be a function.`);let d=s.attributes,h=u(d[l]);return d[l]=h,this.emit("nodeAttributesUpdated",{key:s.key,type:"set",attributes:s.attributes,name:l}),this}}function pl(a,n,e){a.prototype[n]=function(t,r,i){let[o,s]=at(this,n,e,t,r,i);return delete o.attributes[s],this.emit("nodeAttributesUpdated",{key:o.key,type:"remove",attributes:o.attributes,name:s}),this}}function ml(a,n,e){a.prototype[n]=function(t,r,i){let[o,s]=at(this,n,e,t,r,i);if(!Ae(s))throw new X(`Graph.${n}: provided attributes are not a plain object.`);return o.attributes=s,this.emit("nodeAttributesUpdated",{key:o.key,type:"replace",attributes:o.attributes}),this}}function yl(a,n,e){a.prototype[n]=function(t,r,i){let[o,s]=at(this,n,e,t,r,i);if(!Ae(s))throw new X(`Graph.${n}: provided attributes are not a plain object.`);return Te(o.attributes,s),this.emit("nodeAttributesUpdated",{key:o.key,type:"merge",attributes:o.attributes,data:s}),this}}function bl(a,n,e){a.prototype[n]=function(t,r,i){let[o,s]=at(this,n,e,t,r,i);if(typeof s!="function")throw new X(`Graph.${n}: provided updater is not a function.`);return o.attributes=s(o.attributes),this.emit("nodeAttributesUpdated",{key:o.key,type:"update",attributes:o.attributes}),this}}var _l=[{name:a=>`get${a}Attribute`,attacher:hl},{name:a=>`get${a}Attributes`,attacher:cl},{name:a=>`has${a}Attribute`,attacher:fl},{name:a=>`set${a}Attribute`,attacher:gl},{name:a=>`update${a}Attribute`,attacher:vl},{name:a=>`remove${a}Attribute`,attacher:pl},{name:a=>`replace${a}Attributes`,attacher:ml},{name:a=>`merge${a}Attributes`,attacher:yl},{name:a=>`update${a}Attributes`,attacher:bl}];function xl(a){_l.forEach(function({name:n,attacher:e}){e(a,n("Node"),ti),e(a,n("Source"),ni),e(a,n("Target"),dl),e(a,n("Opposite"),ai)})}function Tl(a,n,e){a.prototype[n]=function(t,r){let i;if(this.type!=="mixed"&&e!=="mixed"&&e!==this.type)throw new J(`Graph.${n}: cannot find this type of edges in your ${this.type} graph.`);if(arguments.length>2){if(this.multi)throw new J(`Graph.${n}: cannot use a {source,target} combo when asking about an edge's attributes in a MultiGraph since we cannot infer the one you want information about.`);let o=""+t,s=""+r;if(r=arguments[2],i=We(this,o,s,e),!i)throw new $(`Graph.${n}: could not find an edge for the given path ("${o}" - "${s}").`)}else{if(e!=="mixed")throw new J(`Graph.${n}: calling this method with only a key (vs. a source and target) does not make sense since an edge with this key could have the other type.`);if(t=""+t,i=this._edges.get(t),!i)throw new $(`Graph.${n}: could not find the "${t}" edge in the graph.`)}return i.attributes[r]}}function El(a,n,e){a.prototype[n]=function(t){let r;if(this.type!=="mixed"&&e!=="mixed"&&e!==this.type)throw new J(`Graph.${n}: cannot find this type of edges in your ${this.type} graph.`);if(arguments.length>1){if(this.multi)throw new J(`Graph.${n}: cannot use a {source,target} combo when asking about an edge's attributes in a MultiGraph since we cannot infer the one you want information about.`);let i=""+t,o=""+arguments[1];if(r=We(this,i,o,e),!r)throw new $(`Graph.${n}: could not find an edge for the given path ("${i}" - "${o}").`)}else{if(e!=="mixed")throw new J(`Graph.${n}: calling this method with only a key (vs. a source and target) does not make sense since an edge with this key could have the other type.`);if(t=""+t,r=this._edges.get(t),!r)throw new $(`Graph.${n}: could not find the "${t}" edge in the graph.`)}return r.attributes}}function Sl(a,n,e){a.prototype[n]=function(t,r){let i;if(this.type!=="mixed"&&e!=="mixed"&&e!==this.type)throw new J(`Graph.${n}: cannot find this type of edges in your ${this.type} graph.`);if(arguments.length>2){if(this.multi)throw new J(`Graph.${n}: cannot use a {source,target} combo when asking about an edge's attributes in a MultiGraph since we cannot infer the one you want information about.`);let o=""+t,s=""+r;if(r=arguments[2],i=We(this,o,s,e),!i)throw new $(`Graph.${n}: could not find an edge for the given path ("${o}" - "${s}").`)}else{if(e!=="mixed")throw new J(`Graph.${n}: calling this method with only a key (vs. a source and target) does not make sense since an edge with this key could have the other type.`);if(t=""+t,i=this._edges.get(t),!i)throw new $(`Graph.${n}: could not find the "${t}" edge in the graph.`)}return i.attributes.hasOwnProperty(r)}}function wl(a,n,e){a.prototype[n]=function(t,r,i){let o;if(this.type!=="mixed"&&e!=="mixed"&&e!==this.type)throw new J(`Graph.${n}: cannot find this type of edges in your ${this.type} graph.`);if(arguments.length>3){if(this.multi)throw new J(`Graph.${n}: cannot use a {source,target} combo when asking about an edge's attributes in a MultiGraph since we cannot infer the one you want information about.`);let s=""+t,l=""+r;if(r=arguments[2],i=arguments[3],o=We(this,s,l,e),!o)throw new $(`Graph.${n}: could not find an edge for the given path ("${s}" - "${l}").`)}else{if(e!=="mixed")throw new J(`Graph.${n}: calling this method with only a key (vs. a source and target) does not make sense since an edge with this key could have the other type.`);if(t=""+t,o=this._edges.get(t),!o)throw new $(`Graph.${n}: could not find the "${t}" edge in the graph.`)}return o.attributes[r]=i,this.emit("edgeAttributesUpdated",{key:o.key,type:"set",attributes:o.attributes,name:r}),this}}function Al(a,n,e){a.prototype[n]=function(t,r,i){let o;if(this.type!=="mixed"&&e!=="mixed"&&e!==this.type)throw new J(`Graph.${n}: cannot find this type of edges in your ${this.type} graph.`);if(arguments.length>3){if(this.multi)throw new J(`Graph.${n}: cannot use a {source,target} combo when asking about an edge's attributes in a MultiGraph since we cannot infer the one you want information about.`);let s=""+t,l=""+r;if(r=arguments[2],i=arguments[3],o=We(this,s,l,e),!o)throw new $(`Graph.${n}: could not find an edge for the given path ("${s}" - "${l}").`)}else{if(e!=="mixed")throw new J(`Graph.${n}: calling this method with only a key (vs. a source and target) does not make sense since an edge with this key could have the other type.`);if(t=""+t,o=this._edges.get(t),!o)throw new $(`Graph.${n}: could not find the "${t}" edge in the graph.`)}if(typeof i!="function")throw new X(`Graph.${n}: updater should be a function.`);return o.attributes[r]=i(o.attributes[r]),this.emit("edgeAttributesUpdated",{key:o.key,type:"set",attributes:o.attributes,name:r}),this}}function Dl(a,n,e){a.prototype[n]=function(t,r){let i;if(this.type!=="mixed"&&e!=="mixed"&&e!==this.type)throw new J(`Graph.${n}: cannot find this type of edges in your ${this.type} graph.`);if(arguments.length>2){if(this.multi)throw new J(`Graph.${n}: cannot use a {source,target} combo when asking about an edge's attributes in a MultiGraph since we cannot infer the one you want information about.`);let o=""+t,s=""+r;if(r=arguments[2],i=We(this,o,s,e),!i)throw new $(`Graph.${n}: could not find an edge for the given path ("${o}" - "${s}").`)}else{if(e!=="mixed")throw new J(`Graph.${n}: calling this method with only a key (vs. a source and target) does not make sense since an edge with this key could have the other type.`);if(t=""+t,i=this._edges.get(t),!i)throw new $(`Graph.${n}: could not find the "${t}" edge in the graph.`)}return delete i.attributes[r],this.emit("edgeAttributesUpdated",{key:i.key,type:"remove",attributes:i.attributes,name:r}),this}}function Rl(a,n,e){a.prototype[n]=function(t,r){let i;if(this.type!=="mixed"&&e!=="mixed"&&e!==this.type)throw new J(`Graph.${n}: cannot find this type of edges in your ${this.type} graph.`);if(arguments.length>2){if(this.multi)throw new J(`Graph.${n}: cannot use a {source,target} combo when asking about an edge's attributes in a MultiGraph since we cannot infer the one you want information about.`);let o=""+t,s=""+r;if(r=arguments[2],i=We(this,o,s,e),!i)throw new $(`Graph.${n}: could not find an edge for the given path ("${o}" - "${s}").`)}else{if(e!=="mixed")throw new J(`Graph.${n}: calling this method with only a key (vs. a source and target) does not make sense since an edge with this key could have the other type.`);if(t=""+t,i=this._edges.get(t),!i)throw new $(`Graph.${n}: could not find the "${t}" edge in the graph.`)}if(!Ae(r))throw new X(`Graph.${n}: provided attributes are not a plain object.`);return i.attributes=r,this.emit("edgeAttributesUpdated",{key:i.key,type:"replace",attributes:i.attributes}),this}}function Cl(a,n,e){a.prototype[n]=function(t,r){let i;if(this.type!=="mixed"&&e!=="mixed"&&e!==this.type)throw new J(`Graph.${n}: cannot find this type of edges in your ${this.type} graph.`);if(arguments.length>2){if(this.multi)throw new J(`Graph.${n}: cannot use a {source,target} combo when asking about an edge's attributes in a MultiGraph since we cannot infer the one you want information about.`);let o=""+t,s=""+r;if(r=arguments[2],i=We(this,o,s,e),!i)throw new $(`Graph.${n}: could not find an edge for the given path ("${o}" - "${s}").`)}else{if(e!=="mixed")throw new J(`Graph.${n}: calling this method with only a key (vs. a source and target) does not make sense since an edge with this key could have the other type.`);if(t=""+t,i=this._edges.get(t),!i)throw new $(`Graph.${n}: could not find the "${t}" edge in the graph.`)}if(!Ae(r))throw new X(`Graph.${n}: provided attributes are not a plain object.`);return Te(i.attributes,r),this.emit("edgeAttributesUpdated",{key:i.key,type:"merge",attributes:i.attributes,data:r}),this}}function Ll(a,n,e){a.prototype[n]=function(t,r){let i;if(this.type!=="mixed"&&e!=="mixed"&&e!==this.type)throw new J(`Graph.${n}: cannot find this type of edges in your ${this.type} graph.`);if(arguments.length>2){if(this.multi)throw new J(`Graph.${n}: cannot use a {source,target} combo when asking about an edge's attributes in a MultiGraph since we cannot infer the one you want information about.`);let o=""+t,s=""+r;if(r=arguments[2],i=We(this,o,s,e),!i)throw new $(`Graph.${n}: could not find an edge for the given path ("${o}" - "${s}").`)}else{if(e!=="mixed")throw new J(`Graph.${n}: calling this method with only a key (vs. a source and target) does not make sense since an edge with this key could have the other type.`);if(t=""+t,i=this._edges.get(t),!i)throw new $(`Graph.${n}: could not find the "${t}" edge in the graph.`)}if(typeof r!="function")throw new X(`Graph.${n}: provided updater is not a function.`);return i.attributes=r(i.attributes),this.emit("edgeAttributesUpdated",{key:i.key,type:"update",attributes:i.attributes}),this}}var kl=[{name:a=>`get${a}Attribute`,attacher:Tl},{name:a=>`get${a}Attributes`,attacher:El},{name:a=>`has${a}Attribute`,attacher:Sl},{name:a=>`set${a}Attribute`,attacher:wl},{name:a=>`update${a}Attribute`,attacher:Al},{name:a=>`remove${a}Attribute`,attacher:Dl},{name:a=>`replace${a}Attributes`,attacher:Rl},{name:a=>`merge${a}Attributes`,attacher:Cl},{name:a=>`update${a}Attributes`,attacher:Ll}];function Pl(a){kl.forEach(function({name:n,attacher:e}){e(a,n("Edge"),"mixed"),e(a,n("DirectedEdge"),"directed"),e(a,n("UndirectedEdge"),"undirected")})}var Fl=[{name:"edges",type:"mixed"},{name:"inEdges",type:"directed",direction:"in"},{name:"outEdges",type:"directed",direction:"out"},{name:"inboundEdges",type:"mixed",direction:"in"},{name:"outboundEdges",type:"mixed",direction:"out"},{name:"directedEdges",type:"directed"},{name:"undirectedEdges",type:"undirected"}];function Il(a,n,e,t){let r=!1;for(let i in n){if(i===t)continue;let o=n[i];if(r=e(o.key,o.attributes,o.source.key,o.target.key,o.source.attributes,o.target.attributes,o.undirected),a&&r)return o.key}}function Gl(a,n,e,t){let r,i,o,s=!1;for(let l in n)if(l!==t){r=n[l];do{if(i=r.source,o=r.target,s=e(r.key,r.attributes,i.key,o.key,i.attributes,o.attributes,r.undirected),a&&s)return r.key;r=r.next}while(r!==void 0)}}function za(a,n){let e=Object.keys(a),t=e.length,r,i=0;return{[Symbol.iterator](){return this},next(){do if(r)r=r.next;else{if(i>=t)return{done:!0};let o=e[i++];if(o===n){r=void 0;continue}r=a[o]}while(!r);return{done:!1,value:{edge:r.key,attributes:r.attributes,source:r.source.key,target:r.target.key,sourceAttributes:r.source.attributes,targetAttributes:r.target.attributes,undirected:r.undirected}}}}}function zl(a,n,e,t){let r=n[e];if(!r)return;let i=r.source,o=r.target;if(t(r.key,r.attributes,i.key,o.key,i.attributes,o.attributes,r.undirected)&&a)return r.key}function Nl(a,n,e,t){let r=n[e];if(!r)return;let i=!1;do{if(i=t(r.key,r.attributes,r.source.key,r.target.key,r.source.attributes,r.target.attributes,r.undirected),a&&i)return r.key;r=r.next}while(r!==void 0)}function Na(a,n){let e=a[n];if(e.next!==void 0)return{[Symbol.iterator](){return this},next(){if(!e)return{done:!0};let r={edge:e.key,attributes:e.attributes,source:e.source.key,target:e.target.key,sourceAttributes:e.source.attributes,targetAttributes:e.target.attributes,undirected:e.undirected};return e=e.next,{done:!1,value:r}}};let t=!1;return{[Symbol.iterator](){return this},next(){return t===!0?{done:!0}:(t=!0,{done:!1,value:{edge:e.key,attributes:e.attributes,source:e.source.key,target:e.target.key,sourceAttributes:e.source.attributes,targetAttributes:e.target.attributes,undirected:e.undirected}})}}}function Ml(a,n){if(a.size===0)return[];if(n==="mixed"||n===a.type)return Array.from(a._edges.keys());let e=n==="undirected"?a.undirectedSize:a.directedSize,t=new Array(e),r=n==="undirected",i=a._edges.values(),o=0,s,l;for(;s=i.next(),s.done!==!0;)l=s.value,l.undirected===r&&(t[o++]=l.key);return t}function ri(a,n,e,t){if(n.size===0)return;let r=e!=="mixed"&&e!==n.type,i=e==="undirected",o,s,l=!1,u=n._edges.values();for(;o=u.next(),o.done!==!0;){if(s=o.value,r&&s.undirected!==i)continue;let{key:d,attributes:h,source:c,target:f}=s;if(l=t(d,h,c.key,f.key,c.attributes,f.attributes,s.undirected),a&&l)return d}}function Wl(a,n){if(a.size===0)return Ht();let e=n!=="mixed"&&n!==a.type,t=n==="undirected",r=a._edges.values();return{[Symbol.iterator](){return this},next(){let i,o;for(;;){if(i=r.next(),i.done)return i;if(o=i.value,!(e&&o.undirected!==t))break}return{value:{edge:o.key,attributes:o.attributes,source:o.source.key,target:o.target.key,sourceAttributes:o.source.attributes,targetAttributes:o.target.attributes,undirected:o.undirected},done:!1}}}}function Ma(a,n,e,t,r,i){let o=n?Gl:Il,s;if(e!=="undirected"&&(t!=="out"&&(s=o(a,r.in,i),a&&s)||t!=="in"&&(s=o(a,r.out,i,t?void 0:r.key),a&&s))||e!=="directed"&&(s=o(a,r.undirected,i),a&&s))return s}function Ul(a,n,e,t){let r=[];return Ma(!1,a,n,e,t,function(i){r.push(i)}),r}function Ol(a,n,e){let t=Ht();return a!=="undirected"&&(n!=="out"&&typeof e.in<"u"&&(t=nt(t,za(e.in))),n!=="in"&&typeof e.out<"u"&&(t=nt(t,za(e.out,n?void 0:e.key)))),a!=="directed"&&typeof e.undirected<"u"&&(t=nt(t,za(e.undirected))),t}function Wa(a,n,e,t,r,i,o){let s=e?Nl:zl,l;if(n!=="undirected"&&(typeof r.in<"u"&&t!=="out"&&(l=s(a,r.in,i,o),a&&l)||typeof r.out<"u"&&t!=="in"&&(t||r.key!==i)&&(l=s(a,r.out,i,o),a&&l))||n!=="directed"&&typeof r.undirected<"u"&&(l=s(a,r.undirected,i,o),a&&l))return l}function Bl(a,n,e,t,r){let i=[];return Wa(!1,a,n,e,t,r,function(o){i.push(o)}),i}function Hl(a,n,e,t){let r=Ht();return a!=="undirected"&&(typeof e.in<"u"&&n!=="out"&&t in e.in&&(r=nt(r,Na(e.in,t))),typeof e.out<"u"&&n!=="in"&&t in e.out&&(n||e.key!==t)&&(r=nt(r,Na(e.out,t)))),a!=="directed"&&typeof e.undirected<"u"&&t in e.undirected&&(r=nt(r,Na(e.undirected,t))),r}function $l(a,n){let{name:e,type:t,direction:r}=n;a.prototype[e]=function(i,o){if(t!=="mixed"&&this.type!=="mixed"&&t!==this.type)return[];if(!arguments.length)return Ml(this,t);if(arguments.length===1){i=""+i;let s=this._nodes.get(i);if(typeof s>"u")throw new $(`Graph.${e}: could not find the "${i}" node in the graph.`);return Ul(this.multi,t==="mixed"?this.type:t,r,s)}if(arguments.length===2){i=""+i,o=""+o;let s=this._nodes.get(i);if(!s)throw new $(`Graph.${e}:  could not find the "${i}" source node in the graph.`);if(!this._nodes.has(o))throw new $(`Graph.${e}:  could not find the "${o}" target node in the graph.`);return Bl(t,this.multi,r,s,o)}throw new X(`Graph.${e}: too many arguments (expecting 0, 1 or 2 and got ${arguments.length}).`)}}function Vl(a,n){let{name:e,type:t,direction:r}=n,i="forEach"+e[0].toUpperCase()+e.slice(1,-1);a.prototype[i]=function(u,d,h){if(!(t!=="mixed"&&this.type!=="mixed"&&t!==this.type)){if(arguments.length===1)return h=u,ri(!1,this,t,h);if(arguments.length===2){u=""+u,h=d;let c=this._nodes.get(u);if(typeof c>"u")throw new $(`Graph.${i}: could not find the "${u}" node in the graph.`);return Ma(!1,this.multi,t==="mixed"?this.type:t,r,c,h)}if(arguments.length===3){u=""+u,d=""+d;let c=this._nodes.get(u);if(!c)throw new $(`Graph.${i}:  could not find the "${u}" source node in the graph.`);if(!this._nodes.has(d))throw new $(`Graph.${i}:  could not find the "${d}" target node in the graph.`);return Wa(!1,t,this.multi,r,c,d,h)}throw new X(`Graph.${i}: too many arguments (expecting 1, 2 or 3 and got ${arguments.length}).`)}};let o="map"+e[0].toUpperCase()+e.slice(1);a.prototype[o]=function(){let u=Array.prototype.slice.call(arguments),d=u.pop(),h;if(u.length===0){let c=0;t!=="directed"&&(c+=this.undirectedSize),t!=="undirected"&&(c+=this.directedSize),h=new Array(c);let f=0;u.push((g,y,m,v,p,b,T)=>{h[f++]=d(g,y,m,v,p,b,T)})}else h=[],u.push((c,f,g,y,m,v,p)=>{h.push(d(c,f,g,y,m,v,p))});return this[i].apply(this,u),h};let s="filter"+e[0].toUpperCase()+e.slice(1);a.prototype[s]=function(){let u=Array.prototype.slice.call(arguments),d=u.pop(),h=[];return u.push((c,f,g,y,m,v,p)=>{d(c,f,g,y,m,v,p)&&h.push(c)}),this[i].apply(this,u),h};let l="reduce"+e[0].toUpperCase()+e.slice(1);a.prototype[l]=function(){let u=Array.prototype.slice.call(arguments);if(u.length<2||u.length>4)throw new X(`Graph.${l}: invalid number of arguments (expecting 2, 3 or 4 and got ${u.length}).`);if(typeof u[u.length-1]=="function"&&typeof u[u.length-2]!="function")throw new X(`Graph.${l}: missing initial value. You must provide it because the callback takes more than one argument and we cannot infer the initial value from the first iteration, as you could with a simple array.`);let d,h;u.length===2?(d=u[0],h=u[1],u=[]):u.length===3?(d=u[1],h=u[2],u=[u[0]]):u.length===4&&(d=u[2],h=u[3],u=[u[0],u[1]]);let c=h;return u.push((f,g,y,m,v,p,b)=>{c=d(c,f,g,y,m,v,p,b)}),this[i].apply(this,u),c}}function ql(a,n){let{name:e,type:t,direction:r}=n,i="find"+e[0].toUpperCase()+e.slice(1,-1);a.prototype[i]=function(l,u,d){if(t!=="mixed"&&this.type!=="mixed"&&t!==this.type)return!1;if(arguments.length===1)return d=l,ri(!0,this,t,d);if(arguments.length===2){l=""+l,d=u;let h=this._nodes.get(l);if(typeof h>"u")throw new $(`Graph.${i}: could not find the "${l}" node in the graph.`);return Ma(!0,this.multi,t==="mixed"?this.type:t,r,h,d)}if(arguments.length===3){l=""+l,u=""+u;let h=this._nodes.get(l);if(!h)throw new $(`Graph.${i}:  could not find the "${l}" source node in the graph.`);if(!this._nodes.has(u))throw new $(`Graph.${i}:  could not find the "${u}" target node in the graph.`);return Wa(!0,t,this.multi,r,h,u,d)}throw new X(`Graph.${i}: too many arguments (expecting 1, 2 or 3 and got ${arguments.length}).`)};let o="some"+e[0].toUpperCase()+e.slice(1,-1);a.prototype[o]=function(){let l=Array.prototype.slice.call(arguments),u=l.pop();return l.push((h,c,f,g,y,m,v)=>u(h,c,f,g,y,m,v)),!!this[i].apply(this,l)};let s="every"+e[0].toUpperCase()+e.slice(1,-1);a.prototype[s]=function(){let l=Array.prototype.slice.call(arguments),u=l.pop();return l.push((h,c,f,g,y,m,v)=>!u(h,c,f,g,y,m,v)),!this[i].apply(this,l)}}function jl(a,n){let{name:e,type:t,direction:r}=n,i=e.slice(0,-1)+"Entries";a.prototype[i]=function(o,s){if(t!=="mixed"&&this.type!=="mixed"&&t!==this.type)return Ht();if(!arguments.length)return Wl(this,t);if(arguments.length===1){o=""+o;let l=this._nodes.get(o);if(!l)throw new $(`Graph.${i}: could not find the "${o}" node in the graph.`);return Ol(t,r,l)}if(arguments.length===2){o=""+o,s=""+s;let l=this._nodes.get(o);if(!l)throw new $(`Graph.${i}:  could not find the "${o}" source node in the graph.`);if(!this._nodes.has(s))throw new $(`Graph.${i}:  could not find the "${s}" target node in the graph.`);return Hl(t,r,l,s)}throw new X(`Graph.${i}: too many arguments (expecting 0, 1 or 2 and got ${arguments.length}).`)}}function Xl(a){Fl.forEach(n=>{$l(a,n),Vl(a,n),ql(a,n),jl(a,n)})}var Yl=[{name:"neighbors",type:"mixed"},{name:"inNeighbors",type:"directed",direction:"in"},{name:"outNeighbors",type:"directed",direction:"out"},{name:"inboundNeighbors",type:"mixed",direction:"in"},{name:"outboundNeighbors",type:"mixed",direction:"out"},{name:"directedNeighbors",type:"directed"},{name:"undirectedNeighbors",type:"undirected"}];function Yn(){this.A=null,this.B=null}Yn.prototype.wrap=function(a){this.A===null?this.A=a:this.B===null&&(this.B=a)};Yn.prototype.has=function(a){return this.A!==null&&a in this.A||this.B!==null&&a in this.B};function fn(a,n,e,t,r){for(let i in t){let o=t[i],s=o.source,l=o.target,u=s===e?l:s;if(n&&n.has(u.key))continue;let d=r(u.key,u.attributes);if(a&&d)return u.key}}function Ua(a,n,e,t,r){if(n!=="mixed"){if(n==="undirected")return fn(a,null,t,t.undirected,r);if(typeof e=="string")return fn(a,null,t,t[e],r)}let i=new Yn,o;if(n!=="undirected"){if(e!=="out"){if(o=fn(a,null,t,t.in,r),a&&o)return o;i.wrap(t.in)}if(e!=="in"){if(o=fn(a,i,t,t.out,r),a&&o)return o;i.wrap(t.out)}}if(n!=="directed"&&(o=fn(a,i,t,t.undirected,r),a&&o))return o}function Kl(a,n,e){if(a!=="mixed"){if(a==="undirected")return Object.keys(e.undirected);if(typeof n=="string")return Object.keys(e[n])}let t=[];return Ua(!1,a,n,e,function(r){t.push(r)}),t}function gn(a,n,e){let t=Object.keys(e),r=t.length,i=0;return{[Symbol.iterator](){return this},next(){let o=null;do{if(i>=r)return a&&a.wrap(e),{done:!0};let s=e[t[i++]],l=s.source,u=s.target;if(o=l===n?u:l,a&&a.has(o.key)){o=null;continue}}while(o===null);return{done:!1,value:{neighbor:o.key,attributes:o.attributes}}}}}function Zl(a,n,e){if(a!=="mixed"){if(a==="undirected")return gn(null,e,e.undirected);if(typeof n=="string")return gn(null,e,e[n])}let t=Ht(),r=new Yn;return a!=="undirected"&&(n!=="out"&&(t=nt(t,gn(r,e,e.in))),n!=="in"&&(t=nt(t,gn(r,e,e.out)))),a!=="directed"&&(t=nt(t,gn(r,e,e.undirected))),t}function Ql(a,n){let{name:e,type:t,direction:r}=n;a.prototype[e]=function(i){if(t!=="mixed"&&this.type!=="mixed"&&t!==this.type)return[];i=""+i;let o=this._nodes.get(i);if(typeof o>"u")throw new $(`Graph.${e}: could not find the "${i}" node in the graph.`);return Kl(t==="mixed"?this.type:t,r,o)}}function Jl(a,n){let{name:e,type:t,direction:r}=n,i="forEach"+e[0].toUpperCase()+e.slice(1,-1);a.prototype[i]=function(u,d){if(t!=="mixed"&&this.type!=="mixed"&&t!==this.type)return;u=""+u;let h=this._nodes.get(u);if(typeof h>"u")throw new $(`Graph.${i}: could not find the "${u}" node in the graph.`);Ua(!1,t==="mixed"?this.type:t,r,h,d)};let o="map"+e[0].toUpperCase()+e.slice(1);a.prototype[o]=function(u,d){let h=[];return this[i](u,(c,f)=>{h.push(d(c,f))}),h};let s="filter"+e[0].toUpperCase()+e.slice(1);a.prototype[s]=function(u,d){let h=[];return this[i](u,(c,f)=>{d(c,f)&&h.push(c)}),h};let l="reduce"+e[0].toUpperCase()+e.slice(1);a.prototype[l]=function(u,d,h){if(arguments.length<3)throw new X(`Graph.${l}: missing initial value. You must provide it because the callback takes more than one argument and we cannot infer the initial value from the first iteration, as you could with a simple array.`);let c=h;return this[i](u,(f,g)=>{c=d(c,f,g)}),c}}function eu(a,n){let{name:e,type:t,direction:r}=n,i=e[0].toUpperCase()+e.slice(1,-1),o="find"+i;a.prototype[o]=function(u,d){if(t!=="mixed"&&this.type!=="mixed"&&t!==this.type)return;u=""+u;let h=this._nodes.get(u);if(typeof h>"u")throw new $(`Graph.${o}: could not find the "${u}" node in the graph.`);return Ua(!0,t==="mixed"?this.type:t,r,h,d)};let s="some"+i;a.prototype[s]=function(u,d){return!!this[o](u,d)};let l="every"+i;a.prototype[l]=function(u,d){return!this[o](u,(c,f)=>!d(c,f))}}function tu(a,n){let{name:e,type:t,direction:r}=n,i=e.slice(0,-1)+"Entries";a.prototype[i]=function(o){if(t!=="mixed"&&this.type!=="mixed"&&t!==this.type)return Ht();o=""+o;let s=this._nodes.get(o);if(typeof s>"u")throw new $(`Graph.${i}: could not find the "${o}" node in the graph.`);return Zl(t==="mixed"?this.type:t,r,s)}}function nu(a){Yl.forEach(n=>{Ql(a,n),Jl(a,n),eu(a,n),tu(a,n)})}function Vn(a,n,e,t,r){let i=t._nodes.values(),o=t.type,s,l,u,d,h,c,f;for(;s=i.next(),s.done!==!0;){let g=!1;if(l=s.value,o!=="undirected"){d=l.out;for(u in d){h=d[u];do{if(c=h.target,g=!0,f=r(l.key,c.key,l.attributes,c.attributes,h.key,h.attributes,h.undirected),a&&f)return h;h=h.next}while(h)}}if(o!=="directed"){d=l.undirected;for(u in d)if(!(n&&l.key>u)){h=d[u];do{if(c=h.target,c.key!==u&&(c=h.source),g=!0,f=r(l.key,c.key,l.attributes,c.attributes,h.key,h.attributes,h.undirected),a&&f)return h;h=h.next}while(h)}}if(e&&!g&&(f=r(l.key,null,l.attributes,null,null,null,null),a&&f))return null}}function au(a,n){let e={key:a};return Zr(n.attributes)||(e.attributes=Te({},n.attributes)),e}function ru(a,n,e){let t={key:n,source:e.source.key,target:e.target.key};return Zr(e.attributes)||(t.attributes=Te({},e.attributes)),a==="mixed"&&e.undirected&&(t.undirected=!0),t}function iu(a){if(!Ae(a))throw new X('Graph.import: invalid serialized node. A serialized node should be a plain object with at least a "key" property.');if(!("key"in a))throw new X("Graph.import: serialized node is missing its key.");if("attributes"in a&&(!Ae(a.attributes)||a.attributes===null))throw new X("Graph.import: invalid attributes. Attributes should be a plain object, null or omitted.")}function ou(a){if(!Ae(a))throw new X('Graph.import: invalid serialized edge. A serialized edge should be a plain object with at least a "source" & "target" property.');if(!("source"in a))throw new X("Graph.import: serialized edge is missing its source.");if(!("target"in a))throw new X("Graph.import: serialized edge is missing its target.");if("attributes"in a&&(!Ae(a.attributes)||a.attributes===null))throw new X("Graph.import: invalid attributes. Attributes should be a plain object, null or omitted.");if("undirected"in a&&typeof a.undirected!="boolean")throw new X("Graph.import: invalid undirectedness information. Undirected should be boolean or omitted.")}var su=ul(),lu=new Set(["directed","undirected","mixed"]),Xr=new Set(["domain","_events","_eventsCount","_maxListeners"]),uu=[{name:a=>`${a}Edge`,generateKey:!0},{name:a=>`${a}DirectedEdge`,generateKey:!0,type:"directed"},{name:a=>`${a}UndirectedEdge`,generateKey:!0,type:"undirected"},{name:a=>`${a}EdgeWithKey`},{name:a=>`${a}DirectedEdgeWithKey`,type:"directed"},{name:a=>`${a}UndirectedEdgeWithKey`,type:"undirected"}],du={allowSelfLoops:!0,multi:!1,type:"mixed"};function hu(a,n,e){if(e&&!Ae(e))throw new X(`Graph.addNode: invalid attributes. Expecting an object but got "${e}"`);if(n=""+n,e=e||{},a._nodes.has(n))throw new J(`Graph.addNode: the "${n}" node already exist in the graph.`);let t=new a.NodeDataClass(n,e);return a._nodes.set(n,t),a.emit("nodeAdded",{key:n,attributes:e}),t}function Yr(a,n,e){let t=new a.NodeDataClass(n,e);return a._nodes.set(n,t),a.emit("nodeAdded",{key:n,attributes:e}),t}function ii(a,n,e,t,r,i,o,s){if(!t&&a.type==="undirected")throw new J(`Graph.${n}: you cannot add a directed edge to an undirected graph. Use the #.addEdge or #.addUndirectedEdge instead.`);if(t&&a.type==="directed")throw new J(`Graph.${n}: you cannot add an undirected edge to a directed graph. Use the #.addEdge or #.addDirectedEdge instead.`);if(s&&!Ae(s))throw new X(`Graph.${n}: invalid attributes. Expecting an object but got "${s}"`);if(i=""+i,o=""+o,s=s||{},!a.allowSelfLoops&&i===o)throw new J(`Graph.${n}: source & target are the same ("${i}"), thus creating a loop explicitly forbidden by this graph 'allowSelfLoops' option set to false.`);let l=a._nodes.get(i),u=a._nodes.get(o);if(!l)throw new $(`Graph.${n}: source node "${i}" not found.`);if(!u)throw new $(`Graph.${n}: target node "${o}" not found.`);let d={key:null,undirected:t,source:i,target:o,attributes:s};if(e)r=a._edgeKeyGenerator();else if(r=""+r,a._edges.has(r))throw new J(`Graph.${n}: the "${r}" edge already exists in the graph.`);if(!a.multi&&(t?typeof l.undirected[o]<"u":typeof l.out[o]<"u"))throw new J(`Graph.${n}: an edge linking "${i}" to "${o}" already exists. If you really want to add multiple edges linking those nodes, you should create a multi graph by using the 'multi' option.`);let h=new $t(t,r,l,u,s);a._edges.set(r,h);let c=i===o;return t?(l.undirectedDegree++,u.undirectedDegree++,c&&(l.undirectedLoops++,a._undirectedSelfLoopCount++)):(l.outDegree++,u.inDegree++,c&&(l.directedLoops++,a._directedSelfLoopCount++)),a.multi?h.attachMulti():h.attach(),t?a._undirectedSize++:a._directedSize++,d.key=r,a.emit("edgeAdded",d),r}function cu(a,n,e,t,r,i,o,s,l){if(!t&&a.type==="undirected")throw new J(`Graph.${n}: you cannot merge/update a directed edge to an undirected graph. Use the #.mergeEdge/#.updateEdge or #.addUndirectedEdge instead.`);if(t&&a.type==="directed")throw new J(`Graph.${n}: you cannot merge/update an undirected edge to a directed graph. Use the #.mergeEdge/#.updateEdge or #.addDirectedEdge instead.`);if(s){if(l){if(typeof s!="function")throw new X(`Graph.${n}: invalid updater function. Expecting a function but got "${s}"`)}else if(!Ae(s))throw new X(`Graph.${n}: invalid attributes. Expecting an object but got "${s}"`)}i=""+i,o=""+o;let u;if(l&&(u=s,s=void 0),!a.allowSelfLoops&&i===o)throw new J(`Graph.${n}: source & target are the same ("${i}"), thus creating a loop explicitly forbidden by this graph 'allowSelfLoops' option set to false.`);let d=a._nodes.get(i),h=a._nodes.get(o),c,f;if(!e&&(c=a._edges.get(r),c)){if((c.source.key!==i||c.target.key!==o)&&(!t||c.source.key!==o||c.target.key!==i))throw new J(`Graph.${n}: inconsistency detected when attempting to merge the "${r}" edge with "${i}" source & "${o}" target vs. ("${c.source.key}", "${c.target.key}").`);f=c}if(!f&&!a.multi&&d&&(f=t?d.undirected[o]:d.out[o]),f){let p=[f.key,!1,!1,!1];if(l?!u:!s)return p;if(l){let b=f.attributes;f.attributes=u(b),a.emit("edgeAttributesUpdated",{type:"replace",key:f.key,attributes:f.attributes})}else Te(f.attributes,s),a.emit("edgeAttributesUpdated",{type:"merge",key:f.key,attributes:f.attributes,data:s});return p}s=s||{},l&&u&&(s=u(s));let g={key:null,undirected:t,source:i,target:o,attributes:s};if(e)r=a._edgeKeyGenerator();else if(r=""+r,a._edges.has(r))throw new J(`Graph.${n}: the "${r}" edge already exists in the graph.`);let y=!1,m=!1;d||(d=Yr(a,i,{}),y=!0,i===o&&(h=d,m=!0)),h||(h=Yr(a,o,{}),m=!0),c=new $t(t,r,d,h,s),a._edges.set(r,c);let v=i===o;return t?(d.undirectedDegree++,h.undirectedDegree++,v&&(d.undirectedLoops++,a._undirectedSelfLoopCount++)):(d.outDegree++,h.inDegree++,v&&(d.directedLoops++,a._directedSelfLoopCount++)),a.multi?c.attachMulti():c.attach(),t?a._undirectedSize++:a._directedSize++,g.key=r,a.emit("edgeAdded",g),[r,!0,y,m]}function Ut(a,n){a._edges.delete(n.key);let{source:e,target:t,attributes:r}=n,i=n.undirected,o=e===t;i?(e.undirectedDegree--,t.undirectedDegree--,o&&(e.undirectedLoops--,a._undirectedSelfLoopCount--)):(e.outDegree--,t.inDegree--,o&&(e.directedLoops--,a._directedSelfLoopCount--)),a.multi?n.detachMulti():n.detach(),i?a._undirectedSize--:a._directedSize--,a.emit("edgeDropped",{key:n.key,attributes:r,source:e.key,target:t.key,undirected:i})}var fe=class a extends Kr.EventEmitter{constructor(n){if(super(),n=Te({},du,n),typeof n.multi!="boolean")throw new X(`Graph.constructor: invalid 'multi' option. Expecting a boolean but got "${n.multi}".`);if(!lu.has(n.type))throw new X(`Graph.constructor: invalid 'type' option. Should be one of "mixed", "directed" or "undirected" but got "${n.type}".`);if(typeof n.allowSelfLoops!="boolean")throw new X(`Graph.constructor: invalid 'allowSelfLoops' option. Expecting a boolean but got "${n.allowSelfLoops}".`);let e=n.type==="mixed"?Qr:n.type==="directed"?Jr:ei;Me(this,"NodeDataClass",e);let t="geid_"+su()+"_",r=0,i=()=>{let o;do o=t+r++;while(this._edges.has(o));return o};Me(this,"_attributes",{}),Me(this,"_nodes",new Map),Me(this,"_edges",new Map),Me(this,"_directedSize",0),Me(this,"_undirectedSize",0),Me(this,"_directedSelfLoopCount",0),Me(this,"_undirectedSelfLoopCount",0),Me(this,"_edgeKeyGenerator",i),Me(this,"_options",n),Xr.forEach(o=>Me(this,o,this[o])),je(this,"order",()=>this._nodes.size),je(this,"size",()=>this._edges.size),je(this,"directedSize",()=>this._directedSize),je(this,"undirectedSize",()=>this._undirectedSize),je(this,"selfLoopCount",()=>this._directedSelfLoopCount+this._undirectedSelfLoopCount),je(this,"directedSelfLoopCount",()=>this._directedSelfLoopCount),je(this,"undirectedSelfLoopCount",()=>this._undirectedSelfLoopCount),je(this,"multi",this._options.multi),je(this,"type",this._options.type),je(this,"allowSelfLoops",this._options.allowSelfLoops),je(this,"implementation",()=>"graphology")}_resetInstanceCounters(){this._directedSize=0,this._undirectedSize=0,this._directedSelfLoopCount=0,this._undirectedSelfLoopCount=0}hasNode(n){return this._nodes.has(""+n)}hasDirectedEdge(n,e){if(this.type==="undirected")return!1;if(arguments.length===1){let t=""+n,r=this._edges.get(t);return!!r&&!r.undirected}else if(arguments.length===2){n=""+n,e=""+e;let t=this._nodes.get(n);return t?t.out.hasOwnProperty(e):!1}throw new X(`Graph.hasDirectedEdge: invalid arity (${arguments.length}, instead of 1 or 2). You can either ask for an edge id or for the existence of an edge between a source & a target.`)}hasUndirectedEdge(n,e){if(this.type==="directed")return!1;if(arguments.length===1){let t=""+n,r=this._edges.get(t);return!!r&&r.undirected}else if(arguments.length===2){n=""+n,e=""+e;let t=this._nodes.get(n);return t?t.undirected.hasOwnProperty(e):!1}throw new X(`Graph.hasDirectedEdge: invalid arity (${arguments.length}, instead of 1 or 2). You can either ask for an edge id or for the existence of an edge between a source & a target.`)}hasEdge(n,e){if(arguments.length===1){let t=""+n;return this._edges.has(t)}else if(arguments.length===2){n=""+n,e=""+e;let t=this._nodes.get(n);return t?typeof t.out<"u"&&t.out.hasOwnProperty(e)||typeof t.undirected<"u"&&t.undirected.hasOwnProperty(e):!1}throw new X(`Graph.hasEdge: invalid arity (${arguments.length}, instead of 1 or 2). You can either ask for an edge id or for the existence of an edge between a source & a target.`)}directedEdge(n,e){if(this.type==="undirected")return;if(n=""+n,e=""+e,this.multi)throw new J("Graph.directedEdge: this method is irrelevant with multigraphs since there might be multiple edges between source & target. See #.directedEdges instead.");let t=this._nodes.get(n);if(!t)throw new $(`Graph.directedEdge: could not find the "${n}" source node in the graph.`);if(!this._nodes.has(e))throw new $(`Graph.directedEdge: could not find the "${e}" target node in the graph.`);let r=t.out&&t.out[e]||void 0;if(r)return r.key}undirectedEdge(n,e){if(this.type==="directed")return;if(n=""+n,e=""+e,this.multi)throw new J("Graph.undirectedEdge: this method is irrelevant with multigraphs since there might be multiple edges between source & target. See #.undirectedEdges instead.");let t=this._nodes.get(n);if(!t)throw new $(`Graph.undirectedEdge: could not find the "${n}" source node in the graph.`);if(!this._nodes.has(e))throw new $(`Graph.undirectedEdge: could not find the "${e}" target node in the graph.`);let r=t.undirected&&t.undirected[e]||void 0;if(r)return r.key}edge(n,e){if(this.multi)throw new J("Graph.edge: this method is irrelevant with multigraphs since there might be multiple edges between source & target. See #.edges instead.");n=""+n,e=""+e;let t=this._nodes.get(n);if(!t)throw new $(`Graph.edge: could not find the "${n}" source node in the graph.`);if(!this._nodes.has(e))throw new $(`Graph.edge: could not find the "${e}" target node in the graph.`);let r=t.out&&t.out[e]||t.undirected&&t.undirected[e]||void 0;if(r)return r.key}areDirectedNeighbors(n,e){n=""+n,e=""+e;let t=this._nodes.get(n);if(!t)throw new $(`Graph.areDirectedNeighbors: could not find the "${n}" node in the graph.`);return this.type==="undirected"?!1:e in t.in||e in t.out}areOutNeighbors(n,e){n=""+n,e=""+e;let t=this._nodes.get(n);if(!t)throw new $(`Graph.areOutNeighbors: could not find the "${n}" node in the graph.`);return this.type==="undirected"?!1:e in t.out}areInNeighbors(n,e){n=""+n,e=""+e;let t=this._nodes.get(n);if(!t)throw new $(`Graph.areInNeighbors: could not find the "${n}" node in the graph.`);return this.type==="undirected"?!1:e in t.in}areUndirectedNeighbors(n,e){n=""+n,e=""+e;let t=this._nodes.get(n);if(!t)throw new $(`Graph.areUndirectedNeighbors: could not find the "${n}" node in the graph.`);return this.type==="directed"?!1:e in t.undirected}areNeighbors(n,e){n=""+n,e=""+e;let t=this._nodes.get(n);if(!t)throw new $(`Graph.areNeighbors: could not find the "${n}" node in the graph.`);return this.type!=="undirected"&&(e in t.in||e in t.out)||this.type!=="directed"&&e in t.undirected}areInboundNeighbors(n,e){n=""+n,e=""+e;let t=this._nodes.get(n);if(!t)throw new $(`Graph.areInboundNeighbors: could not find the "${n}" node in the graph.`);return this.type!=="undirected"&&e in t.in||this.type!=="directed"&&e in t.undirected}areOutboundNeighbors(n,e){n=""+n,e=""+e;let t=this._nodes.get(n);if(!t)throw new $(`Graph.areOutboundNeighbors: could not find the "${n}" node in the graph.`);return this.type!=="undirected"&&e in t.out||this.type!=="directed"&&e in t.undirected}inDegree(n){n=""+n;let e=this._nodes.get(n);if(!e)throw new $(`Graph.inDegree: could not find the "${n}" node in the graph.`);return this.type==="undirected"?0:e.inDegree}outDegree(n){n=""+n;let e=this._nodes.get(n);if(!e)throw new $(`Graph.outDegree: could not find the "${n}" node in the graph.`);return this.type==="undirected"?0:e.outDegree}directedDegree(n){n=""+n;let e=this._nodes.get(n);if(!e)throw new $(`Graph.directedDegree: could not find the "${n}" node in the graph.`);return this.type==="undirected"?0:e.inDegree+e.outDegree}undirectedDegree(n){n=""+n;let e=this._nodes.get(n);if(!e)throw new $(`Graph.undirectedDegree: could not find the "${n}" node in the graph.`);return this.type==="directed"?0:e.undirectedDegree}inboundDegree(n){n=""+n;let e=this._nodes.get(n);if(!e)throw new $(`Graph.inboundDegree: could not find the "${n}" node in the graph.`);let t=0;return this.type!=="directed"&&(t+=e.undirectedDegree),this.type!=="undirected"&&(t+=e.inDegree),t}outboundDegree(n){n=""+n;let e=this._nodes.get(n);if(!e)throw new $(`Graph.outboundDegree: could not find the "${n}" node in the graph.`);let t=0;return this.type!=="directed"&&(t+=e.undirectedDegree),this.type!=="undirected"&&(t+=e.outDegree),t}degree(n){n=""+n;let e=this._nodes.get(n);if(!e)throw new $(`Graph.degree: could not find the "${n}" node in the graph.`);let t=0;return this.type!=="directed"&&(t+=e.undirectedDegree),this.type!=="undirected"&&(t+=e.inDegree+e.outDegree),t}inDegreeWithoutSelfLoops(n){n=""+n;let e=this._nodes.get(n);if(!e)throw new $(`Graph.inDegreeWithoutSelfLoops: could not find the "${n}" node in the graph.`);return this.type==="undirected"?0:e.inDegree-e.directedLoops}outDegreeWithoutSelfLoops(n){n=""+n;let e=this._nodes.get(n);if(!e)throw new $(`Graph.outDegreeWithoutSelfLoops: could not find the "${n}" node in the graph.`);return this.type==="undirected"?0:e.outDegree-e.directedLoops}directedDegreeWithoutSelfLoops(n){n=""+n;let e=this._nodes.get(n);if(!e)throw new $(`Graph.directedDegreeWithoutSelfLoops: could not find the "${n}" node in the graph.`);return this.type==="undirected"?0:e.inDegree+e.outDegree-e.directedLoops*2}undirectedDegreeWithoutSelfLoops(n){n=""+n;let e=this._nodes.get(n);if(!e)throw new $(`Graph.undirectedDegreeWithoutSelfLoops: could not find the "${n}" node in the graph.`);return this.type==="directed"?0:e.undirectedDegree-e.undirectedLoops*2}inboundDegreeWithoutSelfLoops(n){n=""+n;let e=this._nodes.get(n);if(!e)throw new $(`Graph.inboundDegreeWithoutSelfLoops: could not find the "${n}" node in the graph.`);let t=0,r=0;return this.type!=="directed"&&(t+=e.undirectedDegree,r+=e.undirectedLoops*2),this.type!=="undirected"&&(t+=e.inDegree,r+=e.directedLoops),t-r}outboundDegreeWithoutSelfLoops(n){n=""+n;let e=this._nodes.get(n);if(!e)throw new $(`Graph.outboundDegreeWithoutSelfLoops: could not find the "${n}" node in the graph.`);let t=0,r=0;return this.type!=="directed"&&(t+=e.undirectedDegree,r+=e.undirectedLoops*2),this.type!=="undirected"&&(t+=e.outDegree,r+=e.directedLoops),t-r}degreeWithoutSelfLoops(n){n=""+n;let e=this._nodes.get(n);if(!e)throw new $(`Graph.degreeWithoutSelfLoops: could not find the "${n}" node in the graph.`);let t=0,r=0;return this.type!=="directed"&&(t+=e.undirectedDegree,r+=e.undirectedLoops*2),this.type!=="undirected"&&(t+=e.inDegree+e.outDegree,r+=e.directedLoops*2),t-r}source(n){n=""+n;let e=this._edges.get(n);if(!e)throw new $(`Graph.source: could not find the "${n}" edge in the graph.`);return e.source.key}target(n){n=""+n;let e=this._edges.get(n);if(!e)throw new $(`Graph.target: could not find the "${n}" edge in the graph.`);return e.target.key}extremities(n){n=""+n;let e=this._edges.get(n);if(!e)throw new $(`Graph.extremities: could not find the "${n}" edge in the graph.`);return[e.source.key,e.target.key]}opposite(n,e){n=""+n,e=""+e;let t=this._edges.get(e);if(!t)throw new $(`Graph.opposite: could not find the "${e}" edge in the graph.`);let r=t.source.key,i=t.target.key;if(n===r)return i;if(n===i)return r;throw new $(`Graph.opposite: the "${n}" node is not attached to the "${e}" edge (${r}, ${i}).`)}hasExtremity(n,e){n=""+n,e=""+e;let t=this._edges.get(n);if(!t)throw new $(`Graph.hasExtremity: could not find the "${n}" edge in the graph.`);return t.source.key===e||t.target.key===e}isUndirected(n){n=""+n;let e=this._edges.get(n);if(!e)throw new $(`Graph.isUndirected: could not find the "${n}" edge in the graph.`);return e.undirected}isDirected(n){n=""+n;let e=this._edges.get(n);if(!e)throw new $(`Graph.isDirected: could not find the "${n}" edge in the graph.`);return!e.undirected}isSelfLoop(n){n=""+n;let e=this._edges.get(n);if(!e)throw new $(`Graph.isSelfLoop: could not find the "${n}" edge in the graph.`);return e.source===e.target}addNode(n,e){return hu(this,n,e).key}mergeNode(n,e){if(e&&!Ae(e))throw new X(`Graph.mergeNode: invalid attributes. Expecting an object but got "${e}"`);n=""+n,e=e||{};let t=this._nodes.get(n);return t?(e&&(Te(t.attributes,e),this.emit("nodeAttributesUpdated",{type:"merge",key:n,attributes:t.attributes,data:e})),[n,!1]):(t=new this.NodeDataClass(n,e),this._nodes.set(n,t),this.emit("nodeAdded",{key:n,attributes:e}),[n,!0])}updateNode(n,e){if(e&&typeof e!="function")throw new X(`Graph.updateNode: invalid updater function. Expecting a function but got "${e}"`);n=""+n;let t=this._nodes.get(n);if(t){if(e){let i=t.attributes;t.attributes=e(i),this.emit("nodeAttributesUpdated",{type:"replace",key:n,attributes:t.attributes})}return[n,!1]}let r=e?e({}):{};return t=new this.NodeDataClass(n,r),this._nodes.set(n,t),this.emit("nodeAdded",{key:n,attributes:r}),[n,!0]}dropNode(n){n=""+n;let e=this._nodes.get(n);if(!e)throw new $(`Graph.dropNode: could not find the "${n}" node in the graph.`);let t;if(this.type!=="undirected"){for(let r in e.out){t=e.out[r];do Ut(this,t),t=t.next;while(t)}for(let r in e.in){t=e.in[r];do Ut(this,t),t=t.next;while(t)}}if(this.type!=="directed")for(let r in e.undirected){t=e.undirected[r];do Ut(this,t),t=t.next;while(t)}this._nodes.delete(n),this.emit("nodeDropped",{key:n,attributes:e.attributes})}dropEdge(n){let e;if(arguments.length>1){let t=""+arguments[0],r=""+arguments[1];if(e=We(this,t,r,this.type),!e)throw new $(`Graph.dropEdge: could not find the "${t}" -> "${r}" edge in the graph.`)}else if(n=""+n,e=this._edges.get(n),!e)throw new $(`Graph.dropEdge: could not find the "${n}" edge in the graph.`);return Ut(this,e),this}dropDirectedEdge(n,e){if(arguments.length<2)throw new J("Graph.dropDirectedEdge: it does not make sense to try and drop a directed edge by key. What if the edge with this key is undirected? Use #.dropEdge for this purpose instead.");if(this.multi)throw new J("Graph.dropDirectedEdge: cannot use a {source,target} combo when dropping an edge in a MultiGraph since we cannot infer the one you want to delete as there could be multiple ones.");n=""+n,e=""+e;let t=We(this,n,e,"directed");if(!t)throw new $(`Graph.dropDirectedEdge: could not find a "${n}" -> "${e}" edge in the graph.`);return Ut(this,t),this}dropUndirectedEdge(n,e){if(arguments.length<2)throw new J("Graph.dropUndirectedEdge: it does not make sense to drop a directed edge by key. What if the edge with this key is undirected? Use #.dropEdge for this purpose instead.");if(this.multi)throw new J("Graph.dropUndirectedEdge: cannot use a {source,target} combo when dropping an edge in a MultiGraph since we cannot infer the one you want to delete as there could be multiple ones.");let t=We(this,n,e,"undirected");if(!t)throw new $(`Graph.dropUndirectedEdge: could not find a "${n}" -> "${e}" edge in the graph.`);return Ut(this,t),this}clear(){this._edges.clear(),this._nodes.clear(),this._resetInstanceCounters(),this.emit("cleared")}clearEdges(){let n=this._nodes.values(),e;for(;e=n.next(),e.done!==!0;)e.value.clear();this._edges.clear(),this._resetInstanceCounters(),this.emit("edgesCleared")}getAttribute(n){return this._attributes[n]}getAttributes(){return this._attributes}hasAttribute(n){return this._attributes.hasOwnProperty(n)}setAttribute(n,e){return this._attributes[n]=e,this.emit("attributesUpdated",{type:"set",attributes:this._attributes,name:n}),this}updateAttribute(n,e){if(typeof e!="function")throw new X("Graph.updateAttribute: updater should be a function.");let t=this._attributes[n];return this._attributes[n]=e(t),this.emit("attributesUpdated",{type:"set",attributes:this._attributes,name:n}),this}removeAttribute(n){return delete this._attributes[n],this.emit("attributesUpdated",{type:"remove",attributes:this._attributes,name:n}),this}replaceAttributes(n){if(!Ae(n))throw new X("Graph.replaceAttributes: provided attributes are not a plain object.");return this._attributes=n,this.emit("attributesUpdated",{type:"replace",attributes:this._attributes}),this}mergeAttributes(n){if(!Ae(n))throw new X("Graph.mergeAttributes: provided attributes are not a plain object.");return Te(this._attributes,n),this.emit("attributesUpdated",{type:"merge",attributes:this._attributes,data:n}),this}updateAttributes(n){if(typeof n!="function")throw new X("Graph.updateAttributes: provided updater is not a function.");return this._attributes=n(this._attributes),this.emit("attributesUpdated",{type:"update",attributes:this._attributes}),this}updateEachNodeAttributes(n,e){if(typeof n!="function")throw new X("Graph.updateEachNodeAttributes: expecting an updater function.");if(e&&!jr(e))throw new X("Graph.updateEachNodeAttributes: invalid hints. Expecting an object having the following shape: {attributes?: [string]}");let t=this._nodes.values(),r,i;for(;r=t.next(),r.done!==!0;)i=r.value,i.attributes=n(i.key,i.attributes);this.emit("eachNodeAttributesUpdated",{hints:e||null})}updateEachEdgeAttributes(n,e){if(typeof n!="function")throw new X("Graph.updateEachEdgeAttributes: expecting an updater function.");if(e&&!jr(e))throw new X("Graph.updateEachEdgeAttributes: invalid hints. Expecting an object having the following shape: {attributes?: [string]}");let t=this._edges.values(),r,i,o,s;for(;r=t.next(),r.done!==!0;)i=r.value,o=i.source,s=i.target,i.attributes=n(i.key,i.attributes,o.key,s.key,o.attributes,s.attributes,i.undirected);this.emit("eachEdgeAttributesUpdated",{hints:e||null})}forEachAdjacencyEntry(n){if(typeof n!="function")throw new X("Graph.forEachAdjacencyEntry: expecting a callback.");Vn(!1,!1,!1,this,n)}forEachAdjacencyEntryWithOrphans(n){if(typeof n!="function")throw new X("Graph.forEachAdjacencyEntryWithOrphans: expecting a callback.");Vn(!1,!1,!0,this,n)}forEachAssymetricAdjacencyEntry(n){if(typeof n!="function")throw new X("Graph.forEachAssymetricAdjacencyEntry: expecting a callback.");Vn(!1,!0,!1,this,n)}forEachAssymetricAdjacencyEntryWithOrphans(n){if(typeof n!="function")throw new X("Graph.forEachAssymetricAdjacencyEntryWithOrphans: expecting a callback.");Vn(!1,!0,!0,this,n)}nodes(){return Array.from(this._nodes.keys())}forEachNode(n){if(typeof n!="function")throw new X("Graph.forEachNode: expecting a callback.");let e=this._nodes.values(),t,r;for(;t=e.next(),t.done!==!0;)r=t.value,n(r.key,r.attributes)}findNode(n){if(typeof n!="function")throw new X("Graph.findNode: expecting a callback.");let e=this._nodes.values(),t,r;for(;t=e.next(),t.done!==!0;)if(r=t.value,n(r.key,r.attributes))return r.key}mapNodes(n){if(typeof n!="function")throw new X("Graph.mapNode: expecting a callback.");let e=this._nodes.values(),t,r,i=new Array(this.order),o=0;for(;t=e.next(),t.done!==!0;)r=t.value,i[o++]=n(r.key,r.attributes);return i}someNode(n){if(typeof n!="function")throw new X("Graph.someNode: expecting a callback.");let e=this._nodes.values(),t,r;for(;t=e.next(),t.done!==!0;)if(r=t.value,n(r.key,r.attributes))return!0;return!1}everyNode(n){if(typeof n!="function")throw new X("Graph.everyNode: expecting a callback.");let e=this._nodes.values(),t,r;for(;t=e.next(),t.done!==!0;)if(r=t.value,!n(r.key,r.attributes))return!1;return!0}filterNodes(n){if(typeof n!="function")throw new X("Graph.filterNodes: expecting a callback.");let e=this._nodes.values(),t,r,i=[];for(;t=e.next(),t.done!==!0;)r=t.value,n(r.key,r.attributes)&&i.push(r.key);return i}reduceNodes(n,e){if(typeof n!="function")throw new X("Graph.reduceNodes: expecting a callback.");if(arguments.length<2)throw new X("Graph.reduceNodes: missing initial value. You must provide it because the callback takes more than one argument and we cannot infer the initial value from the first iteration, as you could with a simple array.");let t=e,r=this._nodes.values(),i,o;for(;i=r.next(),i.done!==!0;)o=i.value,t=n(t,o.key,o.attributes);return t}nodeEntries(){let n=this._nodes.values();return{[Symbol.iterator](){return this},next(){let e=n.next();if(e.done)return e;let t=e.value;return{value:{node:t.key,attributes:t.attributes},done:!1}}}}export(){let n=new Array(this._nodes.size),e=0;this._nodes.forEach((r,i)=>{n[e++]=au(i,r)});let t=new Array(this._edges.size);return e=0,this._edges.forEach((r,i)=>{t[e++]=ru(this.type,i,r)}),{options:{type:this.type,multi:this.multi,allowSelfLoops:this.allowSelfLoops},attributes:this.getAttributes(),nodes:n,edges:t}}import(n,e=!1){if(n instanceof a)return n.forEachNode((l,u)=>{e?this.mergeNode(l,u):this.addNode(l,u)}),n.forEachEdge((l,u,d,h,c,f,g)=>{e?g?this.mergeUndirectedEdgeWithKey(l,d,h,u):this.mergeDirectedEdgeWithKey(l,d,h,u):g?this.addUndirectedEdgeWithKey(l,d,h,u):this.addDirectedEdgeWithKey(l,d,h,u)}),this;if(!Ae(n))throw new X("Graph.import: invalid argument. Expecting a serialized graph or, alternatively, a Graph instance.");if(n.attributes){if(!Ae(n.attributes))throw new X("Graph.import: invalid attributes. Expecting a plain object.");e?this.mergeAttributes(n.attributes):this.replaceAttributes(n.attributes)}let t,r,i,o,s;if(n.nodes){if(i=n.nodes,!Array.isArray(i))throw new X("Graph.import: invalid nodes. Expecting an array.");for(t=0,r=i.length;t<r;t++){o=i[t],iu(o);let{key:l,attributes:u}=o;e?this.mergeNode(l,u):this.addNode(l,u)}}if(n.edges){let l=!1;if(this.type==="undirected"&&(l=!0),i=n.edges,!Array.isArray(i))throw new X("Graph.import: invalid edges. Expecting an array.");for(t=0,r=i.length;t<r;t++){s=i[t],ou(s);let{source:u,target:d,attributes:h,undirected:c=l}=s,f;"key"in s?(f=e?c?this.mergeUndirectedEdgeWithKey:this.mergeDirectedEdgeWithKey:c?this.addUndirectedEdgeWithKey:this.addDirectedEdgeWithKey,f.call(this,s.key,u,d,h)):(f=e?c?this.mergeUndirectedEdge:this.mergeDirectedEdge:c?this.addUndirectedEdge:this.addDirectedEdge,f.call(this,u,d,h))}}return this}nullCopy(n){let e=new a(Te({},this._options,n));return e.replaceAttributes(Te({},this.getAttributes())),e}emptyCopy(n){let e=this.nullCopy(n);return this._nodes.forEach((t,r)=>{let i=Te({},t.attributes);t=new e.NodeDataClass(r,i),e._nodes.set(r,t)}),e}copy(n){if(n=n||{},typeof n.type=="string"&&n.type!==this.type&&n.type!=="mixed")throw new J(`Graph.copy: cannot create an incompatible copy from "${this.type}" type to "${n.type}" because this would mean losing information about the current graph.`);if(typeof n.multi=="boolean"&&n.multi!==this.multi&&n.multi!==!0)throw new J("Graph.copy: cannot create an incompatible copy by downgrading a multi graph to a simple one because this would mean losing information about the current graph.");if(typeof n.allowSelfLoops=="boolean"&&n.allowSelfLoops!==this.allowSelfLoops&&n.allowSelfLoops!==!0)throw new J("Graph.copy: cannot create an incompatible copy from a graph allowing self loops to one that does not because this would mean losing information about the current graph.");let e=this.emptyCopy(n),t=this._edges.values(),r,i;for(;r=t.next(),r.done!==!0;)i=r.value,ii(e,"copy",!1,i.undirected,i.key,i.source.key,i.target.key,Te({},i.attributes));return e}toJSON(){return this.export()}toString(){return"[object Graph]"}inspect(){let n={};this._nodes.forEach((i,o)=>{n[o]=i.attributes});let e={},t={};this._edges.forEach((i,o)=>{let s=i.undirected?"--":"->",l="",u=i.source.key,d=i.target.key,h;i.undirected&&u>d&&(h=u,u=d,d=h);let c=`(${u})${s}(${d})`;o.startsWith("geid_")?this.multi&&(typeof t[c]>"u"?t[c]=0:t[c]++,l+=`${t[c]}. `):l+=`[${o}]: `,l+=c,e[l]=i.attributes});let r={};for(let i in this)this.hasOwnProperty(i)&&!Xr.has(i)&&typeof this[i]!="function"&&typeof i!="symbol"&&(r[i]=this[i]);return r.attributes=this._attributes,r.nodes=n,r.edges=e,Me(r,"constructor",this.constructor),r}};typeof Symbol<"u"&&(fe.prototype[Symbol.for("nodejs.util.inspect.custom")]=fe.prototype.inspect);uu.forEach(a=>{["add","merge","update"].forEach(n=>{let e=a.name(n),t=n==="add"?ii:cu;a.generateKey?fe.prototype[e]=function(r,i,o){return t(this,e,!0,(a.type||this.type)==="undirected",null,r,i,o,n==="update")}:fe.prototype[e]=function(r,i,o,s){return t(this,e,!1,(a.type||this.type)==="undirected",r,i,o,s,n==="update")}})});xl(fe);Pl(fe);Xl(fe);nu(fe);var qn=class extends fe{constructor(n){let e=Te({type:"directed"},n);if("multi"in e&&e.multi!==!1)throw new X("DirectedGraph.from: inconsistent indication that the graph should be multi in given options!");if(e.type!=="directed")throw new X('DirectedGraph.from: inconsistent "'+e.type+'" type in given options!');super(e)}},Ot=class extends fe{constructor(n){let e=Te({type:"undirected"},n);if("multi"in e&&e.multi!==!1)throw new X("UndirectedGraph.from: inconsistent indication that the graph should be multi in given options!");if(e.type!=="undirected")throw new X('UndirectedGraph.from: inconsistent "'+e.type+'" type in given options!');super(e)}},jn=class extends fe{constructor(n){let e=Te({multi:!0},n);if("multi"in e&&e.multi!==!0)throw new X("MultiGraph.from: inconsistent indication that the graph should be simple in given options!");super(e)}},Bt=class extends fe{constructor(n){let e=Te({type:"directed",multi:!0},n);if("multi"in e&&e.multi!==!0)throw new X("MultiDirectedGraph.from: inconsistent indication that the graph should be simple in given options!");if(e.type!=="directed")throw new X('MultiDirectedGraph.from: inconsistent "'+e.type+'" type in given options!');super(e)}},Xn=class extends fe{constructor(n){let e=Te({type:"undirected",multi:!0},n);if("multi"in e&&e.multi!==!0)throw new X("MultiUndirectedGraph.from: inconsistent indication that the graph should be simple in given options!");if(e.type!=="undirected")throw new X('MultiUndirectedGraph.from: inconsistent "'+e.type+'" type in given options!');super(e)}};function Vt(a){a.from=function(n,e){let t=Te({},n.options,e),r=new a(t);return r.import(n),r}}Vt(fe);Vt(qn);Vt(Ot);Vt(jn);Vt(Bt);Vt(Xn);fe.Graph=fe;fe.DirectedGraph=qn;fe.UndirectedGraph=Ot;fe.MultiGraph=jn;fe.MultiDirectedGraph=Bt;fe.MultiUndirectedGraph=Xn;fe.InvalidArgumentsGraphError=X;fe.NotFoundGraphError=$;fe.UsageGraphError=J;var Os=tt(Ri(),1),Bs=tt(Wi(),1),Hs=tt(Hi(),1);function ta(a,n){(n==null||n>a.length)&&(n=a.length);for(var e=0,t=Array(n);e<n;e++)t[e]=a[e];return t}function na(a,n){if(a){if(typeof a=="string")return ta(a,n);var e={}.toString.call(a).slice(8,-1);return e==="Object"&&a.constructor&&(e=a.constructor.name),e==="Map"||e==="Set"?Array.from(a):e==="Arguments"||/^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(e)?ta(a,n):void 0}}function Uu(a){if(Array.isArray(a))return a}function Ou(a,n){var e=a==null?null:typeof Symbol<"u"&&a[Symbol.iterator]||a["@@iterator"];if(e!=null){var t,r,i,o,s=[],l=!0,u=!1;try{if(i=(e=e.call(a)).next,n===0){if(Object(e)!==e)return;l=!1}else for(;!(l=(t=i.call(e)).done)&&(s.push(t.value),s.length!==n);l=!0);}catch(d){u=!0,r=d}finally{try{if(!l&&e.return!=null&&(o=e.return(),Object(o)!==o))return}finally{if(u)throw r}}return s}}function Bu(){throw new TypeError(`Invalid attempt to destructure non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`)}function ie(a,n){return Uu(a)||Ou(a,n)||na(a,n)||Bu()}function O(a,n){var e=typeof Symbol<"u"&&a[Symbol.iterator]||a["@@iterator"];if(!e){if(Array.isArray(a)||(e=na(a))||n&&a&&typeof a.length=="number"){e&&(a=e);var t=0,r=function(){};return{s:r,n:function(){return t>=a.length?{done:!0}:{done:!1,value:a[t++]}},e:function(l){throw l},f:r}}throw new TypeError(`Invalid attempt to iterate non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`)}var i,o=!0,s=!1;return{s:function(){e=e.call(a)},n:function(){var l=e.next();return o=l.done,l},e:function(l){s=!0,i=l},f:function(){try{o||e.return==null||e.return()}finally{if(s)throw i}}}}function Oe(){return Float32Array.of(1,0,0,0,1,0,0,0,1)}function Jn(a,n,e){return a[0]=n,a[4]=typeof e=="number"?e:n,a}function $i(a,n){var e=Math.sin(n),t=Math.cos(n);return a[0]=t,a[1]=e,a[3]=-e,a[4]=t,a}function Vi(a,n,e){return a[6]=n,a[7]=e,a}function ct(a,n){var e=a[0],t=a[1],r=a[2],i=a[3],o=a[4],s=a[5],l=a[6],u=a[7],d=a[8],h=n[0],c=n[1],f=n[2],g=n[3],y=n[4],m=n[5],v=n[6],p=n[7],b=n[8];return a[0]=h*e+c*i+f*l,a[1]=h*t+c*o+f*u,a[2]=h*r+c*s+f*d,a[3]=g*e+y*i+m*l,a[4]=g*t+y*o+m*u,a[5]=g*r+y*s+m*d,a[6]=v*e+p*i+b*l,a[7]=v*t+p*o+b*u,a[8]=v*r+p*s+b*d,a}function ja(a,n){var e=Math.cos(n),t=Math.sin(n);return{x:e*a.x+t*a.y,y:-t*a.x+e*a.y}}function Yt(a,n){var e=arguments.length>2&&arguments[2]!==void 0?arguments[2]:1,t=a[0],r=a[1],i=a[3],o=a[4],s=a[6],l=a[7],u=n.x,d=n.y;return{x:u*t+d*i+s*e,y:u*r+d*o+l*e}}function Hu(a,n){var e=a.height/a.width,t=n.height/n.width;return e<1&&t>1||e>1&&t<1?1:Math.min(Math.max(t,1/t),Math.max(1/e,e))}function ft(a,n,e,t,r){var i=a.angle,o=a.ratio,s=a.x,l=a.y,u=n.width,d=n.height,h=Oe(),c=Math.min(u,d)-2*t,f=Hu(n,e);return r?(ct(h,Vi(Oe(),s,l)),ct(h,Jn(Oe(),o)),ct(h,$i(Oe(),i)),ct(h,Jn(Oe(),u/c/2/f,d/c/2/f))):(ct(h,Jn(Oe(),2*(c/u)*f,2*(c/d)*f)),ct(h,$i(Oe(),-i)),ct(h,Jn(Oe(),1/o)),ct(h,Vi(Oe(),-s,-l))),h}function qi(a,n,e){var t=Yt(a,{x:Math.cos(n.angle),y:Math.sin(n.angle)},0),r=t.x,i=t.y;return 1/Math.sqrt(Math.pow(r,2)+Math.pow(i,2))/e.width}function Xa(a,n,e,t,r){var i=Math.floor(n/r*t),o=Math.floor(a.drawingBufferHeight/r-e/r*t);return[i,o]}var _n={black:"#000000",silver:"#C0C0C0",gray:"#808080",grey:"#808080",white:"#FFFFFF",maroon:"#800000",red:"#FF0000",purple:"#800080",fuchsia:"#FF00FF",green:"#008000",lime:"#00FF00",olive:"#808000",yellow:"#FFFF00",navy:"#000080",blue:"#0000FF",teal:"#008080",aqua:"#00FFFF",darkblue:"#00008B",mediumblue:"#0000CD",darkgreen:"#006400",darkcyan:"#008B8B",deepskyblue:"#00BFFF",darkturquoise:"#00CED1",mediumspringgreen:"#00FA9A",springgreen:"#00FF7F",cyan:"#00FFFF",midnightblue:"#191970",dodgerblue:"#1E90FF",lightseagreen:"#20B2AA",forestgreen:"#228B22",seagreen:"#2E8B57",darkslategray:"#2F4F4F",darkslategrey:"#2F4F4F",limegreen:"#32CD32",mediumseagreen:"#3CB371",turquoise:"#40E0D0",royalblue:"#4169E1",steelblue:"#4682B4",darkslateblue:"#483D8B",mediumturquoise:"#48D1CC",indigo:"#4B0082",darkolivegreen:"#556B2F",cadetblue:"#5F9EA0",cornflowerblue:"#6495ED",rebeccapurple:"#663399",mediumaquamarine:"#66CDAA",dimgray:"#696969",dimgrey:"#696969",slateblue:"#6A5ACD",olivedrab:"#6B8E23",slategray:"#708090",slategrey:"#708090",lightslategray:"#778899",lightslategrey:"#778899",mediumslateblue:"#7B68EE",lawngreen:"#7CFC00",chartreuse:"#7FFF00",aquamarine:"#7FFFD4",skyblue:"#87CEEB",lightskyblue:"#87CEFA",blueviolet:"#8A2BE2",darkred:"#8B0000",darkmagenta:"#8B008B",saddlebrown:"#8B4513",darkseagreen:"#8FBC8F",lightgreen:"#90EE90",mediumpurple:"#9370DB",darkviolet:"#9400D3",palegreen:"#98FB98",darkorchid:"#9932CC",yellowgreen:"#9ACD32",sienna:"#A0522D",brown:"#A52A2A",darkgray:"#A9A9A9",darkgrey:"#A9A9A9",lightblue:"#ADD8E6",greenyellow:"#ADFF2F",paleturquoise:"#AFEEEE",lightsteelblue:"#B0C4DE",powderblue:"#B0E0E6",firebrick:"#B22222",darkgoldenrod:"#B8860B",mediumorchid:"#BA55D3",rosybrown:"#BC8F8F",darkkhaki:"#BDB76B",mediumvioletred:"#C71585",indianred:"#CD5C5C",peru:"#CD853F",chocolate:"#D2691E",tan:"#D2B48C",lightgray:"#D3D3D3",lightgrey:"#D3D3D3",thistle:"#D8BFD8",orchid:"#DA70D6",goldenrod:"#DAA520",palevioletred:"#DB7093",crimson:"#DC143C",gainsboro:"#DCDCDC",plum:"#DDA0DD",burlywood:"#DEB887",lightcyan:"#E0FFFF",lavender:"#E6E6FA",darksalmon:"#E9967A",violet:"#EE82EE",palegoldenrod:"#EEE8AA",lightcoral:"#F08080",khaki:"#F0E68C",aliceblue:"#F0F8FF",honeydew:"#F0FFF0",azure:"#F0FFFF",sandybrown:"#F4A460",wheat:"#F5DEB3",beige:"#F5F5DC",whitesmoke:"#F5F5F5",mintcream:"#F5FFFA",ghostwhite:"#F8F8FF",salmon:"#FA8072",antiquewhite:"#FAEBD7",linen:"#FAF0E6",lightgoldenrodyellow:"#FAFAD2",oldlace:"#FDF5E6",magenta:"#FF00FF",deeppink:"#FF1493",orangered:"#FF4500",tomato:"#FF6347",hotpink:"#FF69B4",coral:"#FF7F50",darkorange:"#FF8C00",lightsalmon:"#FFA07A",orange:"#FFA500",lightpink:"#FFB6C1",pink:"#FFC0CB",gold:"#FFD700",peachpuff:"#FFDAB9",navajowhite:"#FFDEAD",moccasin:"#FFE4B5",bisque:"#FFE4C4",mistyrose:"#FFE4E1",blanchedalmond:"#FFEBCD",papayawhip:"#FFEFD5",lavenderblush:"#FFF0F5",seashell:"#FFF5EE",cornsilk:"#FFF8DC",lemonchiffon:"#FFFACD",floralwhite:"#FFFAF0",snow:"#FFFAFA",lightyellow:"#FFFFE0",ivory:"#FFFFF0"},ji=new Int8Array(4),ea=new Int32Array(ji.buffer,0,1),Xi=new Float32Array(ji.buffer,0,1),$u=/^\s*rgba?\s*\(/,Vu=/^\s*rgba?\s*\(\s*([0-9]*)\s*,\s*([0-9]*)\s*,\s*([0-9]*)(?:\s*,\s*(.*)?)?\)\s*$/;function aa(a){var n=0,e=0,t=0,r=1,i=a.toLowerCase();if(i==="transparent")return{r:0,g:0,b:0,a:0};if(i in _n)return aa(_n[i]);if(a[0]==="#")a.length===4?(n=parseInt(a.charAt(1)+a.charAt(1),16),e=parseInt(a.charAt(2)+a.charAt(2),16),t=parseInt(a.charAt(3)+a.charAt(3),16)):(n=parseInt(a.charAt(1)+a.charAt(2),16),e=parseInt(a.charAt(3)+a.charAt(4),16),t=parseInt(a.charAt(5)+a.charAt(6),16)),a.length===9&&(r=parseInt(a.charAt(7)+a.charAt(8),16)/255);else if($u.test(a)){var o=a.match(Vu);o&&(n=+o[1],e=+o[2],t=+o[3],o[4]&&(r=+o[4]))}return{r:n,g:e,b:t,a:r}}function Yi(a){var n=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!1,e=aa(a),t=e.r,r=e.g,i=e.b,o=e.a;return n?[t/255*o,r/255*o,i/255*o,o]:[t/255,r/255,i/255,o]}var Xt={};for(bn in _n)Xt[bn]=Be(_n[bn]),Xt[_n[bn]]=Xt[bn];var bn;function qu(a,n,e,t,r){return ea[0]=t<<24|e<<16|n<<8|a,r&&(ea[0]=ea[0]&4278190079),Xi[0]}function Be(a){if(a=a.toLowerCase(),typeof Xt[a]<"u")return Xt[a];var n=aa(a),e=n.r,t=n.g,r=n.b,i=n.a;i=i*255|0;var o=qu(e,t,r,i,!0);return Xt[a]=o,o}function gt(a,n){Xi[0]=Be(a);var e=ea[0];n&&(e=e|16777216);var t=e&255,r=e>>8&255,i=e>>16&255,o=e>>24&255;return[t,r,i,o]}function Kt(a){var n=a>>>8&255,e=a>>>16&255,t=a>>>24&255,r=a&255;return(r<<24|t<<16|e<<8|n)>>>0}function Ya(a,n,e,t){return(e<<24|n<<16|a<<8|t)>>>0}function Ki(a,n,e,t,r,i){var o=Xa(a,e,t,r,i),s=ie(o,2),l=s[0],u=s[1],d=new Uint8Array(4);a.bindFramebuffer(a.FRAMEBUFFER,n),a.readPixels(l,u,1,1,a.RGBA,a.UNSIGNED_BYTE,d);var h=ie(d,4),c=h[0],f=h[1],g=h[2],y=h[3];return[c,f,g,y]}function Zi(a){var n=aa(a),e=n.r,t=n.g,r=n.b,i=n.a,o=(e/255).toFixed(6),s=(t/255).toFixed(6),l=(r/255).toFixed(6),u=i.toFixed(6);return"vec4(".concat(o,", ").concat(s,", ").concat(l,", ").concat(u,")")}function ju(a,n){if(typeof a!="object"||!a)return a;var e=a[Symbol.toPrimitive];if(e!==void 0){var t=e.call(a,n||"default");if(typeof t!="object")return t;throw new TypeError("@@toPrimitive must return a primitive value.")}return(n==="string"?String:Number)(a)}function eo(a){var n=ju(a,"string");return typeof n=="symbol"?n:n+""}function D(a,n,e){return(n=eo(n))in a?Object.defineProperty(a,n,{value:e,enumerable:!0,configurable:!0,writable:!0}):a[n]=e,a}function Qi(a,n){var e=Object.keys(a);if(Object.getOwnPropertySymbols){var t=Object.getOwnPropertySymbols(a);n&&(t=t.filter(function(r){return Object.getOwnPropertyDescriptor(a,r).enumerable})),e.push.apply(e,t)}return e}function H(a){for(var n=1;n<arguments.length;n++){var e=arguments[n]!=null?arguments[n]:{};n%2?Qi(Object(e),!0).forEach(function(t){D(a,t,e[t])}):Object.getOwnPropertyDescriptors?Object.defineProperties(a,Object.getOwnPropertyDescriptors(e)):Qi(Object(e)).forEach(function(t){Object.defineProperty(a,t,Object.getOwnPropertyDescriptor(e,t))})}return a}function te(a,n){if(!(a instanceof n))throw new TypeError("Cannot call a class as a function")}function Ji(a,n){for(var e=0;e<n.length;e++){var t=n[e];t.enumerable=t.enumerable||!1,t.configurable=!0,"value"in t&&(t.writable=!0),Object.defineProperty(a,eo(t.key),t)}}function ne(a,n,e){return n&&Ji(a.prototype,n),e&&Ji(a,e),Object.defineProperty(a,"prototype",{writable:!1}),a}function wt(a){return wt=Object.setPrototypeOf?Object.getPrototypeOf.bind():function(n){return n.__proto__||Object.getPrototypeOf(n)},wt(a)}function to(){try{var a=!Boolean.prototype.valueOf.call(Reflect.construct(Boolean,[],function(){}))}catch{}return(to=function(){return!!a})()}function Xu(a){if(a===void 0)throw new ReferenceError("this hasn't been initialised - super() hasn't been called");return a}function Yu(a,n){if(n&&(typeof n=="object"||typeof n=="function"))return n;if(n!==void 0)throw new TypeError("Derived constructors may only return object or undefined");return Xu(a)}function me(a,n,e){return n=wt(n),Yu(a,to()?Reflect.construct(n,e||[],wt(a).constructor):n.apply(a,e))}function Ka(a,n){return Ka=Object.setPrototypeOf?Object.setPrototypeOf.bind():function(e,t){return e.__proto__=t,e},Ka(a,n)}function ye(a,n){if(typeof n!="function"&&n!==null)throw new TypeError("Super expression must either be null or a function");a.prototype=Object.create(n&&n.prototype,{constructor:{value:a,writable:!0,configurable:!0}}),Object.defineProperty(a,"prototype",{writable:!1}),n&&Ka(a,n)}function Ku(a){if(Array.isArray(a))return ta(a)}function Zu(a){if(typeof Symbol<"u"&&a[Symbol.iterator]!=null||a["@@iterator"]!=null)return Array.from(a)}function Qu(){throw new TypeError(`Invalid attempt to spread non-iterable instance.
In order to be iterable, non-array objects must have a [Symbol.iterator]() method.`)}function Q(a){return Ku(a)||Zu(a)||na(a)||Qu()}function re(a){"@babel/helpers - typeof";return re=typeof Symbol=="function"&&typeof Symbol.iterator=="symbol"?function(n){return typeof n}:function(n){return n&&typeof Symbol=="function"&&n.constructor===Symbol&&n!==Symbol.prototype?"symbol":typeof n},re(a)}function ot(a){return re(a)==="object"&&a!==null&&"attribute"in a}function no(){var a=`
float sdf_circle(vec2 uv, float size) {
  return length(uv) - size;
}
`;return{name:"circle",glsl:a,uniforms:[]}}function ao(a){var n,e=WebGL2RenderingContext,t=e.UNSIGNED_BYTE,r=(n=a?.color)!==null&&n!==void 0?n:{attribute:"color"};if(!ot(r)){var i=r,o=`
vec4 layer_fill() {
  return `.concat(Zi(i),`;
}
`);return{name:"fill",uniforms:[],attributes:[],glsl:o}}var s=r.attribute,l=`
vec4 layer_fill(vec4 v_fillColor) {
  return v_fillColor;
}
`;return{name:"fill",uniforms:[],attributes:[{name:"fillColor",size:4,type:t,normalized:!0,source:s}],glsl:l}}function Ju(a,n){if(typeof a=="string"){var e=Yi(a).map(function(u){return u.toFixed(6)}),t=ie(e,4),r=t[0],i=t[1],o=t[2],s=t[3];return{glsl:"vec4(".concat(r,", ").concat(i,", ").concat(o,", ").concat(s,")"),attributes:[],needsNodeColors:!1}}if("node"in a&&a.node)return{glsl:a.node==="source"?"v_sourceColor":"v_targetColor",attributes:[],needsNodeColors:!0};var l=a;return{glsl:"v_".concat(n),attributes:[{name:"a_".concat(n),size:4,type:WebGL2RenderingContext.UNSIGNED_BYTE,normalized:!0,source:l.attribute,defaultValue:l.default}],needsNodeColors:!1}}function At(a){var n=a?.color;if(n===void 0){var e=`
// Plain solid color layer
vec4 layer_plain(EdgeContext ctx) {
  return v_color;
}
`;return{name:"plain",glsl:e,uniforms:[],attributes:[]}}var t=Ju(n,"plainColor"),r=`
// Plain solid color layer
vec4 layer_plain(EdgeContext ctx) {
  return `.concat(t.glsl,`;
}
`);return{name:"plain",glsl:r,uniforms:[],attributes:t.attributes,needsNodeColors:t.needsNodeColors}}function ro(){var a=`
// Position at parameter t \u2208 [0, 1]
vec2 path_straight_position(float t, vec2 source, vec2 target) {
  return mix(source, target, t);
}

// Total length of the path (analytical - more efficient than sampling)
float path_straight_length(vec2 source, vec2 target) {
  return length(target - source);
}
`;return{name:"straight",segments:1,minBodyLengthRatio:0,linearParameterization:!0,glsl:a,uniforms:[],attributes:[]}}function io(a){var n=a??{},e=n.segments,t=e===void 0?32:e,r=`
const float LOOP_PI = 3.141592653589793;

float loopWorldRadius() {
  float nodeWorldRadius = v_sourceNodeSize * u_correctionRatio / u_sizeRatio;
  return max(v_loopRadius * nodeWorldRadius, 0.001);
}

// Cubic B\xE9zier with P0 = P3 = source.
// Control points extend outward orthogonal to the node surface at exit/entry angles.
vec2 path_loop_position(float t, vec2 source, vec2 target) {
  float R = loopWorldRadius();
  float angle = v_loopAngle + (v_loopFixedOrientation > 0.5 ? u_cameraAngle : 0.0);
  float halfSpread = v_loopSpread * 0.5;

  float exitAngle = angle - halfSpread;
  float entryAngle = angle + halfSpread;

  // Control point distance: at t=0.5 the B\xE9zier reaches 0.75 * cpDist * cos(halfSpread)
  // from source. Solve for cpDist so the loop tip reaches exactly R.
  float cpDist = R / (0.75 * cos(halfSpread));

  vec2 cp1 = source + cpDist * vec2(cos(exitAngle), sin(exitAngle));
  vec2 cp2 = source + cpDist * vec2(cos(entryAngle), sin(entryAngle));

  float u = 1.0 - t;
  vec2 d1 = cp1 - source;
  vec2 d2 = cp2 - source;
  return source + 3.0 * t * u * (u * d1 + t * d2);
}

// Approximate arc length via chord sampling
float path_loop_length(vec2 source, vec2 target) {
  float len = 0.0;
  vec2 prev = path_loop_position(0.0, source, target);
  const int STEPS = 16;
  for (int i = 1; i <= STEPS; i++) {
    float t = float(i) / float(STEPS);
    vec2 cur = path_loop_position(t, source, target);
    len += length(cur - prev);
    prev = cur;
  }
  return len;
}
`;return{name:"loop",segments:t,glsl:r,needsNodeSize:!0,uniforms:[],attributes:[{name:"loopRadius",size:1,type:WebGL2RenderingContext.FLOAT},{name:"loopAngle",size:1,type:WebGL2RenderingContext.FLOAT},{name:"loopSpread",size:1,type:WebGL2RenderingContext.FLOAT},{name:"loopFixedOrientation",size:1,type:WebGL2RenderingContext.FLOAT}],variables:{loopRadius:{type:"number",default:4},loopAngle:{type:"number",default:Math.PI/4},loopSpread:{type:"number",default:80*Math.PI/180},loopFixedOrientation:{type:"number",default:0}},spread:{variable:"loopRadius",compute:function(o){return o+4}}}}var co=tt(cn());function oo(a){return re(a)==="object"&&"glsl"in a&&!("attributes"in a)}function so(a){return re(a)==="object"&&"glsl"in a&&!("attributes"in a)}var xn={shapes:[no()],variables:{},layers:[ao()],label:{},backdrop:{},labelAttachments:{}},Zt={paths:[ro(),io()],extremities:[],variables:{},layers:[At()],defaultHead:"none",defaultTail:"none",label:{}},ra=["nodes","topNodes"],ia=["edges","topEdges"],oa=[].concat(ia,ra),lo={nodes:xn,edges:Zt,depthLayers:Q(oa)};var ed=function(n){return n},td=function(n){return n*n},nd=function(n){return n*(2-n)},ad=function(n){return(n*=2)<1?.5*n*n:-.5*(--n*(n-2)-1)},rd=function(n){return n*n*n},id=function(n){return--n*n*n+1},od=function(n){return(n*=2)<1?.5*n*n*n:.5*((n-=2)*n*n+2)},sd=function(n){return n===0?0:Math.pow(2,10*(n-1))},ld=function(n){return n===1?1:1-Math.pow(2,-10*n)},ud=function(n){return n===0?0:n===1?1:n<.5?Math.pow(2,10*(2*n-1))/2:(2-Math.pow(2,-10*(2*n-1)))/2},Za={linear:ed,quadraticIn:td,quadraticOut:nd,quadraticInOut:ad,cubicIn:rd,cubicOut:id,cubicInOut:od,exponentialIn:sd,exponentialOut:ld,exponentialInOut:ud};function sa(a){return a?typeof a=="function"?a:Za[a]:Za.linear}function Ja(a){return re(a)==="object"&&a!==null&&"attribute"in a}function fo(a){return typeof a=="function"}function go(a){return re(a)==="object"&&a!==null&&"when"in a&&typeof a.when=="function"&&"then"in a}function vo(a){return re(a)==="object"&&a!==null&&"whenState"in a&&"then"in a}function po(a){return re(a)==="object"&&a!==null&&"whenData"in a&&"then"in a}var dd={isHovered:!1,isLabelHovered:!1,isHidden:!1,isHighlighted:!1,isDragged:!1},hd={isHovered:!1,isLabelHovered:!1,isHidden:!1,isHighlighted:!1,parallelIndex:0,parallelCount:1},cd={isIdle:!0,isPanning:!1,isZooming:!1,isDragging:!1,hasHovered:!1,hasHighlighted:!1};function mo(a){return H(H({},dd),a)}function yo(a){return H(H({},hd),a)}function er(a){return H(H({},cd),a)}var fd={x:{attribute:"x"},y:{attribute:"y"},size:{whenState:"isHovered",then:{attribute:"size",defaultValue:12},else:{attribute:"size",defaultValue:10}},color:{attribute:"color",defaultValue:"#666"},label:{attribute:"label"},visibility:{whenState:"isHidden",then:"hidden",else:"visible"},labelVisibility:{whenState:"isHovered",then:"visible",else:"auto"},backdropVisibility:{whenState:"isHovered",then:"visible",else:"hidden"},backdropColor:"#ffffff",backdropShadowColor:"rgba(0, 0, 0, 0.5)",backdropShadowBlur:12,backdropPadding:6},gd={size:{attribute:"size",defaultValue:1},color:{attribute:"color",defaultValue:"#ccc"},label:{attribute:"label"},visibility:{whenState:"isHidden",then:"hidden",else:"visible"}};var ua={nodes:H(H({},fd),{},{depth:{whenState:"isHovered",then:"topNodes",else:"nodes"}}),edges:H(H({},gd),{},{depth:{whenState:["isHighlighted","isHovered"],then:"topEdges",else:"edges"}})};function vd(a){return"min"in a||"max"in a||"minValue"in a||"maxValue"in a||"easing"in a}function pd(a){return"dict"in a}function da(a,n){return typeof a=="string"?n[a]===!0:Array.isArray(a)?a.every(function(e){return n[e]===!0}):re(a)==="object"&&a!==null?Object.entries(a).every(function(e){var t=ie(e,2),r=t[0],i=t[1];return n[r]===i}):!1}function md(a,n){var e=n[a.attribute];return e===void 0?a.defaultValue:e}function yd(a,n,e){var t,r,i,o,s=n[a.attribute];if(s===void 0)return a.defaultValue;var l=Number(s);if(isNaN(l))return a.defaultValue;if(a.min===void 0&&a.max===void 0)return l;var u=(t=a.minValue)!==null&&t!==void 0?t:l,d=(r=a.maxValue)!==null&&r!==void 0?r:l;if(d===u){var h;return(h=a.min)!==null&&h!==void 0?h:l}var c=(l-u)/(d-u);c=Math.max(0,Math.min(1,c));var f=sa(a.easing);c=f(c);var g=(i=a.min)!==null&&i!==void 0?i:0,y=(o=a.max)!==null&&o!==void 0?o:1;return g+c*(y-g)}function bd(a,n){var e=n[a.attribute];if(e===void 0)return a.defaultValue;var t=String(e);return t in a.dict?a.dict[t]:a.defaultValue}function _d(a,n,e){return pd(a)?bd(a,n):vd(a)?yd(a,n):md(a,n)}function bo(a,n){return typeof a=="string"?!!n[a]:Array.isArray(a)?a.every(function(e){return!!n[e]}):re(a)==="object"&&a!==null?Object.entries(a).every(function(e){var t=ie(e,2),r=t[0],i=t[1];return n[r]===i}):!1}function la(a,n,e,t,r,i){if(a==null)return i;if(re(a)!=="object"&&typeof a!="function")return a;if(go(a)){var o=a.when(n,e,t,r)?a.then:a.else;return o===void 0?i:la(o,n,e,t,r,i)}if(vo(a)){var s=da(a.whenState,e)?a.then:a.else;return s===void 0?i:la(s,n,e,t,r,i)}if(po(a)){var l=bo(a.whenData,n)?a.then:a.else;return l===void 0?i:la(l,n,e,t,r,i)}if(fo(a)){var u=a(n,e,t,r);return u??i}if(Ja(a)){var d=_d(a,n);return d??i}return a}function Ye(a){if(a==null)return"static";if(go(a))return"graph-state";if(vo(a)){var n=Ye(a.then),e=a.else!==void 0?Ye(a.else):"static";return He("item-state",He(n,e))}if(po(a)){var t=Ye(a.then),r=a.else!==void 0?Ye(a.else):"static";return He(t,r)}return fo(a)?"graph-state":(Ja(a),"static")}function He(a,n){return a==="graph-state"||n==="graph-state"?"graph-state":a==="item-state"||n==="item-state"?"item-state":"static"}function tr(a){if(!a)return{dependency:"static",xAttribute:null,yAttribute:null};var n=Array.isArray(a)?a:[a],e="static",t=null,r=null,i=O(n),o;try{for(i.s();!(o=i.n()).done;){var s=o.value;if("matchData"in s&&"cases"in s)for(var l=s.cases,u=0,d=Object.values(l);u<d.length;u++)for(var h=d[u],c=0,f=Object.values(h);c<f.length;c++){var g=f[c];e=He(e,Ye(g))}else if("matchState"in s&&"cases"in s){e=He(e,"item-state");for(var y=s.cases,m=0,v=Object.values(y);m<v.length;m++)for(var p=v[m],b=0,T=Object.values(p);b<T.length;b++){var _=T[b];e=He(e,Ye(_))}}else if("when"in s&&"then"in s)e="graph-state";else if("whenState"in s){e=He(e,"item-state");var E=s.then;if(E&&re(E)==="object")for(var A=0,w=Object.values(E);A<w.length;A++){var S=w[A];e=He(e,Ye(S))}var C=s.else;if(C&&re(C)==="object")for(var G=0,L=Object.values(C);G<L.length;G++){var N=L[G];e=He(e,Ye(N))}}else if("whenData"in s){var k=s.then;if(k&&re(k)==="object")for(var I=0,W=Object.values(k);I<W.length;I++){var F=W[I];e=He(e,Ye(F))}var x=s.else;if(x&&re(x)==="object")for(var P=0,U=Object.values(x);P<U.length;P++){var z=U[P];e=He(e,Ye(z))}}else for(var R=0,j=Object.entries(s);R<j.length;R++){var q=ie(j[R],2),Z=q[0],Se=q[1];if(!ar.has(Z)&&(e=He(e,Ye(Se)),(Z==="x"||Z==="y")&&Ja(Se))){var de=Se.attribute;Z==="x"&&!t&&(t=de),Z==="y"&&!r&&(r=de)}}}}catch(K){i.e(K)}finally{i.f()}return{dependency:e,xAttribute:t,yAttribute:r}}var st={size:10,color:"#666",opacity:1,shape:"circle",rotationAlignment:"viewport",labelRotationAlignment:"viewport",visibility:"visible",depth:"nodes",zIndex:0,label:"",labelColor:"#000",labelSize:12,labelFont:"sans-serif",labelVisibility:"auto",labelPosition:"right",labelAngle:0,labelDepth:"nodes",backdropVisibility:"hidden",backdropColor:"transparent",backdropShadowColor:"transparent",backdropShadowBlur:0,backdropPadding:0,backdropBorderColor:"transparent",backdropBorderWidth:0,backdropCornerRadius:0,backdropLabelPadding:-1,backdropArea:"both",labelAttachment:null,labelAttachmentPlacement:"below"},nr={size:1,color:"#ccc",opacity:1,path:"straight",selfLoopPath:"loop",parallelSpread:.25,tail:"none",head:"none",visibility:"visible",depth:"edges",zIndex:0,label:"",labelColor:"#666",labelVisibility:"auto",labelDepth:"edges"},ar=new Set(["when","whenState","whenData","then","else"]),uo=Object.keys(st),xd=Object.values(st),ho=Object.keys(nr),Td=Object.values(nr);function Qt(a,n,e,t,r,i,o){for(var s in n){var l;if(!ar.has(s)){var u=(l=a[s])!==null&&l!==void 0?l:o[s];a[s]=la(n[s],e,t,r,i,u)}}"depth"in n&&!("labelDepth"in n)&&(a.labelDepth=a.depth)}function _o(a,n,e,t,r,i,o){var s=O(n),l;try{for(s.s();!(l=s.n()).done;){var u=l.value;if("matchData"in u&&"cases"in u){var d,h=String((d=e[u.matchData])!==null&&d!==void 0?d:""),c=u.cases;h in c&&Qt(a,c[h],e,t,r,i,o)}else if("matchState"in u&&"cases"in u){var f,g=String((f=t[u.matchState])!==null&&f!==void 0?f:""),y=u.cases;g in y&&Qt(a,y[g],e,t,r,i,o)}else if("when"in u&&"then"in u){var m=u.when;if(!m(e,t,r,i))continue;Qt(a,u.then,e,t,r,i,o)}else if("whenState"in u&&"then"in u){if(!da(u.whenState,t))continue;Qt(a,u.then,e,t,r,i,o)}else if("whenData"in u&&"then"in u){if(!bo(u.whenData,e))continue;Qt(a,u.then,e,t,r,i,o)}else Qt(a,u,e,t,r,i,o)}}catch(v){s.e(v)}finally{s.f()}}function rr(a,n,e,t,r,i){for(var o=i||{},s=o,l=0,u=uo.length;l<u;l++)s[uo[l]]=xd[l];if(s.x=void 0,s.y=void 0,s.labelBackgroundColor=void 0,s.labelBackgroundPadding=void 0,s.labelCursor=void 0,!a){var d,h,c,f,g;return s.x=(d=n.x)!==null&&d!==void 0?d:0,s.y=(h=n.y)!==null&&h!==void 0?h:0,o.size=(c=n.size)!==null&&c!==void 0?c:10,o.color=(f=n.color)!==null&&f!==void 0?f:"#666",o.label=(g=n.label)!==null&&g!==void 0?g:"",o}var y=Array.isArray(a)?a:[a];return _o(s,y,n,e,t,r,st),o}function ir(a,n,e,t,r,i){for(var o=i||{},s=o,l=0,u=ho.length;l<u;l++)s[ho[l]]=Td[l];if(!a){var d,h,c;return o.size=(d=n.size)!==null&&d!==void 0?d:1,o.color=(h=n.color)!==null&&h!==void 0?h:"#ccc",o.label=(c=n.label)!==null&&c!==void 0?c:"",o}var f=Array.isArray(a)?a:[a];return _o(s,f,n,e,t,r,nr),typeof s.labelPosition=="number"&&(s.labelPosition=void 0),o}function Ed(a,n,e){var t,r;if(a==null)return e;if(typeof a=="function")return(t=a(n))!==null&&t!==void 0?t:e;if(re(a)==="object"&&"when"in a){var i,o=a,s=o.when(n),l=s?o.then:o.else;return l===void 0?e:typeof l=="function"?(i=l(n))!==null&&i!==void 0?i:e:l??e}if(re(a)==="object"&&"whenState"in a){var u,d=a,h=da(d.whenState,n),c=h?d.then:d.else;return c===void 0?e:typeof c=="function"?(u=c(n))!==null&&u!==void 0?u:e:c??e}return(r=a)!==null&&r!==void 0?r:e}function or(a,n){var e={};if(!a)return e;var t=Array.isArray(a)?a:[a],r=O(t),i;try{for(r.s();!(i=r.n()).done;){var o=i.value;if("when"in o&&"then"in o){var s=o.when(n),l=s?o.then:o.else;l&&re(l)==="object"&&Qa(e,l,n)}else if("whenState"in o&&"then"in o){var u=da(o.whenState,n),d=u?o.then:o.else;d&&re(d)==="object"&&Qa(e,d,n)}else Qa(e,o,n)}}catch(h){r.e(h)}finally{r.f()}return e}function Qa(a,n,e){for(var t=0,r=Object.entries(n);t<r.length;t++){var i=ie(r[t],2),o=i[0],s=i[1];ar.has(o)||(a[o]=Ed(s,e))}}var ha=(function(a){function n(){var e;return te(this,n),e=me(this,n),e.rawEmitter=e,e}return ye(n,a),ne(n)})(co.EventEmitter);var xo=lo;function sr(a,n){var e=n.size;if(e!==0){var t=a.length;a.length+=e;var r=0;n.forEach(function(i){a[t+r]=i,r++})}}function To(a){a=a||{};for(var n=0,e=arguments.length<=1?0:arguments.length-1;n<e;n++){var t=n+1<1||arguments.length<=n+1?void 0:arguments[n+1];t&&Object.assign(a,t)}return a}function Jt(a,n){for(var e in n)if(Object.prototype.hasOwnProperty.call(n,e)&&n[e]!==a[e])return!0;return!1}function Eo(a,n){var e=a,t=n;for(var r in e)if(Object.prototype.hasOwnProperty.call(e,r)&&e[r]!==t[r])return!1;for(var i in t)if(Object.prototype.hasOwnProperty.call(t,i)&&t[i]!==e[i])return!1;return!0}function Dt(a,n,e){e?a.add(n):a.delete(n)}var So=tt(qt());var wo={easing:"quadraticInOut",duration:150};function vt(a){return a.labelVisibility==="visible"&&a.visibility!=="hidden"}function lr(a){return a.backdropVisibility==="visible"&&a.visibility!=="hidden"}function ca(a){return[a.rotationAlignment==="graph"?1:0,a.labelRotationAlignment==="graph"?1:0]}function ur(a,n,e){var t=a[n];if(t)for(var r=0;r<t.length;r++){var i=t[r];if(!(e<i.offset||e>=i.offset+i.count)){if(i.count===1)t.splice(r,1);else if(e===i.offset)i.offset++,i.count--;else if(e===i.offset+i.count-1)i.count--;else{var o=e+1,s=i.offset+i.count-o;i.count=e-i.offset,t.splice(r+1,0,{offset:o,count:s})}return}}}function dr(a,n,e){if(!a[n]){a[n]=[{offset:e,count:1}];return}for(var t=a[n],r=t.length,i=0;i<t.length;i++)if(e<t[i].offset){r=i;break}var o=r>0?t[r-1]:null,s=r<t.length?t[r]:null,l=o&&o.offset+o.count===e,u=s&&e+1===s.offset;l&&u?(o.count+=1+s.count,t.splice(r,1)):l?o.count++:u?(s.offset--,s.count++):t.splice(r,0,{offset:e,count:1})}function Ao(a){if(!(0,So.default)(a))throw new Error("Sigma: invalid graph instance.")}function fa(a){var n=ie(a.x,2),e=n[0],t=n[1],r=ie(a.y,2),i=r[0],o=r[1],s=Math.max(t-e,o-i),l=(t+e)/2,u=(o+i)/2;(s===0||Math.abs(s)===1/0||isNaN(s))&&(s=1),isNaN(l)&&(l=0),isNaN(u)&&(u=0);var d=function(c){return{x:.5+(c.x-l)/s,y:.5+(c.y-u)/s}};return d.applyTo=function(h){h.x=.5+(h.x-l)/s,h.y=.5+(h.y-u)/s},d.inverse=function(h){return{x:l+s*(h.x-.5),y:u+s*(h.y-.5)}},d.ratio=s,d}var ga={hideEdgesOnMove:!1,hideLabelsOnMove:!1,renderLabels:!0,renderEdgeLabels:!1,edgeLabelAnchors:"nodeLabels",enableEdgeEvents:!1,nodeLabelEvents:!1,edgeLabelEvents:!1,pickingDownSizingRatio:2,nodePickingPadding:0,edgePickingPadding:4,labelPickingPadding:10,stagePadding:30,minEdgeThickness:1.7,antiAliasingFeather:1,antialiasEdges:!0,antialiasNodes:!0,dragTimeout:100,draggedEventsTolerance:3,inertiaDuration:200,inertiaRatio:3,zoomDuration:250,zoomingRatio:1.7,doubleClickTimeout:300,doubleClickZoomingRatio:2.2,doubleClickZoomingDuration:200,tapMoveTolerance:10,zoomToSizeRatioFunction:Math.sqrt,itemSizesReference:"positions",autoRescale:!0,autoRescaleContent:"positions",enableNodeDrag:!1,getDraggedNodes:function(n){return[n]},dragPositionToAttributes:null,labelDensity:1,labelGridCellSize:100,labelRenderedSizeThreshold:6,labelPixelSnapping:!0,minCameraRatio:null,maxCameraRatio:null,enableCameraZooming:!0,enableCameraPanning:!0,enableCameraRotation:!0,enableCameraMouseRotation:!0,cameraPanBoundaries:null,gestureTarget:"graph",sharedGestureWheelMessage:"Use Ctrl + scroll to zoom the graph",sharedGestureAppleWheelMessage:"Use \u2318 + scroll to zoom the graph",sharedGestureTouchMessage:"Use two fingers to move the graph",allowInvalidContainer:!1,DEBUG_displayPickingLayer:!1,DEBUG_logShaders:!1,DEBUG_logRenderStats:!1,DEBUG_gpuTimerQueries:!1};function va(a){if(typeof a.labelDensity!="number"||a.labelDensity<0)throw new Error("Settings: invalid `labelDensity`. Expecting a positive number.");var n=a.minCameraRatio,e=a.maxCameraRatio;if(typeof n=="number"&&typeof e=="number"&&e<n)throw new Error("Settings: invalid camera ratio boundaries. Expecting `maxCameraRatio` to be greater than `minCameraRatio`.")}function Do(a){return To({},ga,a)}var Sd=new Set(["italic","oblique"]),wd=new Set(["bold","bolder","lighter"]);function pa(a){for(var n="normal",e="normal",t=a.trim(),r=t.split(/\s+/),i=0,o=0;o<r.length;o++){var s=r[o].toLowerCase();if(Sd.has(s))e=s,i=o+1;else if(wd.has(s)||/^\d{3}$/.test(s))n=s,i=o+1;else if(s==="normal")i=o+1;else break}var l=r.slice(i).join(" ");return{family:l||t,weight:n,style:e}}function en(a,n,e){var t=document.createElement(a);if(n)for(var r in n)t.style[r]=n[r];if(e)for(var i in e)t.setAttribute(i,e[i]);return t}function Tn(){return typeof window.devicePixelRatio<"u"?window.devicePixelRatio:1}var No=tt(cn());function Ad(a){var n=a.type===WebGL2RenderingContext.FLOAT&&!a.normalized,e=a.type===WebGL2RenderingContext.UNSIGNED_BYTE&&a.size===4&&a.normalized;if(!n&&!e)throw new Error('Attribute "'.concat(a.name,'" is invalid: only non-normalized FLOAT and normalized UNSIGNED_BYTE with size 4 are supported.'));return a.normalized?1:a.size}function hr(a){var n=0;return a.forEach(function(e){return n+=Ad(e)}),n}function Mo(a,n,e){var t=a==="VERTEX"?n.VERTEX_SHADER:n.FRAGMENT_SHADER,r=n.createShader(t);if(r===null)throw new Error("loadShader: error while creating the shader");n.shaderSource(r,e),n.compileShader(r);var i=n.getShaderParameter(r,n.COMPILE_STATUS);if(!i){var o=n.getShaderInfoLog(r);throw n.deleteShader(r),new Error(`loadShader: error while compiling the shader:
`.concat(o,`
`).concat(e))}return r}function fr(a,n){return Mo("VERTEX",a,n)}function gr(a,n){return Mo("FRAGMENT",a,n)}function vr(a,n){var e=a.createProgram();if(e===null)throw new Error("loadProgram: error while creating the program.");var t,r;for(t=0,r=n.length;t<r;t++)a.attachShader(e,n[t]);a.linkProgram(e);var i=a.getProgramParameter(e,a.LINK_STATUS);if(!i){var o=a.getProgramInfoLog(e);throw a.deleteProgram(e),new Error("loadProgram: error while linking the program: ".concat(o))}return e}function Ro(a){var n=a.gl,e=a.buffer,t=a.program,r=a.vertexShader,i=a.fragmentShader;n.deleteShader(r),n.deleteShader(i),n.deleteProgram(t),n.deleteBuffer(e)}function xe(a){return a%1===0?a.toFixed(1):a.toString()}var Ta=new Map,Wo=new Map,Dd=0;function Uo(a,n){var e,t=(e=a.variables)===null||e===void 0||(e=e[n.source||n.name.replace(/^a_/,"")])===null||e===void 0?void 0:e.default,r=typeof t=="number"?t:typeof n.defaultValue=="number"?n.defaultValue:0;return xe(r)}function Ea(a,n,e){var t,r=arguments.length>3&&arguments[3]!==void 0?arguments[3]:function(o){return"v_".concat(o.name.replace(/^a_/,""))},i=[n,e].concat(Q(a.uniforms.filter(function(o){return o.type==="float"}).map(function(o){var s;return xe((s=o.value)!==null&&s!==void 0?s:0)})),Q(((t=a.attributes)!==null&&t!==void 0?t:[]).map(r)));return"sdf_".concat(a.name,"(").concat(i.join(", "),")")}function Rd(a){var n,e=a.name,t=a.uniforms.filter(function(o){return o.type==="float"&&o.value!==void 0&&o.value!==0}).map(function(o){return"".concat(o.name.replace("u_",""),"=").concat(o.value)}).sort(),r=((n=a.attributes)!==null&&n!==void 0?n:[]).map(function(o){var s;return"".concat(o.name,"@").concat((s=o.source)!==null&&s!==void 0?s:"","=").concat(Uo(a,o))}),i=[].concat(Q(t),Q(r));return i.length>0&&(e+="#"+i.join("#")),e}function Cd(a){var n=Rd(a);if(!Ta.has(n)){var e={},t=O(a.uniforms),r;try{for(t.s();!(r=t.n()).done;){var i=r.value;i.type==="float"&&i.value!==void 0&&(e[i.name]=i.value)}}catch(o){t.e(o)}finally{t.f()}Ta.set(n,{shape:a,uniformValues:e,slug:n}),Wo.set(n,Dd++)}return n}function Dn(a){var n;return(n=Wo.get(a))!==null&&n!==void 0?n:-1}function Oo(a){var n=[],e=new Set,t=new Set,r=/mat2 rotate2D\(float angle\)\s*\{[^}]+\}/,i=O(a),o;try{for(i.s();!(o=i.n()).done;){var s=o.value;if(!t.has(s.name)){t.add(s.name);var l=s.glsl;r.test(l)&&(e.has("rotate2D")?l=l.replace(r,""):e.add("rotate2D")),n.push(l)}}}catch(u){i.e(u)}finally{i.f()}return n.join(`
`)}function Ld(){return Oo(Array.from(Ta.values()).map(function(a){return a.shape}))}function kd(a){var n=Array.from(Ta.entries());if(n.length===0)return`
float querySDF(int shapeId, vec2 uv, float size) {
  return length(uv) - size;
}
`;var e=n.map(function(t,r){var i=ie(t,2),o=i[0],s=i[1].shape,l=Ea(s,"uv","size",function(u){var d=u.name.replace(/^a_/,"");return a!=null&&a.has(d)?"g_".concat(d):Uo(s,u)});return"    case ".concat(r,": return ").concat(l,"; // ").concat(o)}).join(`
`);return`
float querySDF(int shapeId, vec2 uv, float size) {
  switch (shapeId) {
`.concat(e,`
    default: return length(uv) - size;
  }
}
`)}function pr(a){return Oo(a)}function Rn(a){return Q(new Map(a.flatMap(function(n){return n.uniforms}).map(function(n){return[n.name,n]})).values())}function Pd(a,n){if(a.length===0)return`
void queryNodeSDF(int shapeId, vec2 uv, float size) {
  context.sdf = length(uv) - size;
  context.inradiusFactor = 1.0;
}
`;var e=function(h){return Ea(h,"uv","size")},t=function(h){var c,f;return(c=h.inradiusFactorGLSL)!==null&&c!==void 0?c:xe((f=h.inradiusFactor)!==null&&f!==void 0?f:1)};if(a.length===1){var r=a[0];return`
void queryNodeSDF(int shapeId, vec2 uv, float size) {
  context.sdf = `.concat(e(r),`;
  context.inradiusFactor = `).concat(t(r),`;
}
`)}var i=a.map(function(d,h){return"    case ".concat(h,": // ").concat(d.name,`
      context.sdf = `).concat(e(d),`;
      context.inradiusFactor = `).concat(t(d),`;
      break;`)}).join(`
`),o=a[0],s="",l="shapeId";if(n&&n.length>1){var u=n.map(function(d,h){return"    case ".concat(d,": return ").concat(h,"; // ").concat(a[h].name)}).join(`
`);s=`
int globalToLocalShapeId(int globalId) {
  switch (globalId) {
`.concat(u,`
    default: return 0;
  }
}
`),l="globalToLocalShapeId(shapeId)"}return"".concat(s,`
void queryNodeSDF(int shapeId, vec2 uv, float size) {
  switch (`).concat(l,`) {
`).concat(i,`
    default:
      context.sdf = `).concat(e(o),`;
      context.inradiusFactor = `).concat(t(o),`;
  }
}
`)}var nn={right:0,left:1,above:2,below:3,over:4},an=5,mr=3,Bo=`
float matrixScaleX = length(vec2(u_matrix[0][0], u_matrix[1][0]));
float nodeRadiusGraphSpace = nodeSize * u_correctionRatio / u_sizeRatio * 2.0;
float nodeRadiusNDC = nodeRadiusGraphSpace * matrixScaleX;
float nodeRadiusPixels = nodeRadiusNDC * u_resolution.x / 2.0;
`,Fd=`
mat2 rotate2D(float angle) {
  float c = cos(angle);
  float s = sin(angle);
  return mat2(c, -s, s, c);
}
`,Ho=`
vec2 getLabelDirection(float positionMode) {
  if (positionMode < 0.5) return vec2(1.0, 0.0);   // Right
  if (positionMode < 1.5) return vec2(-1.0, 0.0);  // Left
  if (positionMode < 2.5) return vec2(0.0, -1.0);  // Above
  if (positionMode < 3.5) return vec2(0.0, 1.0);   // Below
  return vec2(0.0);                                 // Over (centered)
}
`,Id=`
float sdfBox(vec2 p, vec2 halfSize) {
  vec2 d = abs(p) - halfSize;
  return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
}
`,Gd=`
float sdfRotatedBox(vec2 p, vec2 halfSize, float angle) {
  float c = cos(-angle);
  float s = sin(-angle);
  vec2 rotatedP = mat2(c, -s, s, c) * p;
  return sdfBox(rotatedP, halfSize);
}
`,zd=`
float sdfRoundedBox(vec2 p, vec2 halfSize, float radius) {
  vec2 d = abs(p) - halfSize + radius;
  return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0) - radius;
}
`,Nd=`
float sdfRoundedRotatedBox(vec2 p, vec2 halfSize, float angle, float radius) {
  float c = cos(-angle);
  float s = sin(-angle);
  vec2 rotatedP = mat2(c, -s, s, c) * p;
  return sdfRoundedBox(rotatedP, halfSize, radius);
}
`,$o=`
vec2 labelBoxCenter(float positionMode, float labelStart, vec2 halfSize, float textHalfY) {
  if (positionMode < 0.5) return vec2(labelStart + halfSize.x, 0.0);    // right
  if (positionMode < 1.5) return vec2(-(labelStart + halfSize.x), 0.0); // left
  if (positionMode < 2.5) return vec2(0.0, -(labelStart + textHalfY));  // above
  if (positionMode < 3.5) return vec2(0.0, labelStart + textHalfY);     // below
  return vec2(0.0);                                                     // over
}
`,yr=2,lt=`
vec4 readNodeData(sampler2D nodeDataTexture, int nodeDataTextureWidth, int nodeIndex) {
  int t = nodeIndex * `.concat(yr,`;
  ivec2 coord = ivec2(t % nodeDataTextureWidth, t / nodeDataTextureWidth);
  return texelFetch(nodeDataTexture, coord, 0);
}
`),Ct=`
vec4 readNodeFlags(sampler2D nodeDataTexture, int nodeDataTextureWidth, int nodeIndex) {
  int t = nodeIndex * `.concat(yr,` + 1;
  ivec2 coord = ivec2(t % nodeDataTextureWidth, t / nodeDataTextureWidth);
  return texelFetch(nodeDataTexture, coord, 0);
}
`),Md=`
vec4 readNodeColor(sampler2D nodeDataTexture, int nodeDataTextureWidth, int nodeIndex) {
  int t = nodeIndex * `.concat(yr,` + 1;
  ivec2 coord = ivec2(t % nodeDataTextureWidth, t / nodeDataTextureWidth);
  vec4 texel = texelFetch(nodeDataTexture, coord, 0);
  float r = floor(texel.b / 65536.0);
  float g = floor(mod(texel.b, 65536.0) / 256.0);
  float b = mod(texel.b, 256.0);
  return vec4(r / 255.0, g / 255.0, b / 255.0, texel.a);
}
`),rn=`
vec4 readFrameTexel(sampler2D frameTexture, int frameTextureWidth, int index) {
  ivec2 coord = ivec2(index % frameTextureWidth, index / frameTextureWidth);
  return texelFetch(frameTexture, coord, 0);
}
`;function Wd(a,n){var e=function(o){return Ea(o,"uv","size")};if(a.length===1)return{code:Co(e(a[0])),multiShape:!1};var t=a.map(function(i,o){return"    case ".concat(n?n[o]:o,": return ").concat(e(i),";")}).join(`
`),r=`
float queryShapeSDF(int shapeId, vec2 uv, float size) {
  switch (shapeId) {
`.concat(t,`
    default: return `).concat(e(a[0]),`;
  }
}
int g_shapeId;
`).concat(Co("queryShapeSDF(g_shapeId, uv, size)"),`
`);return{code:r,multiShape:!0}}function Co(a){return`
float findEdgeDistance(vec2 direction, float size) {
  float lo = 0.0, hi = 2.0;
  for (int i = 0; i < 8; i++) {
    float mid = (lo + hi) * 0.5;
    vec2 uv = direction * mid;
    if (`.concat(a,` < 0.0) lo = mid; else hi = mid;
  }
  return (lo + hi) * 0.5;
}
`)}function Ud(a,n){for(;!{}.hasOwnProperty.call(a,n)&&(a=wt(a))!==null;);return a}function cr(){return cr=typeof Reflect<"u"&&Reflect.get?Reflect.get.bind():function(a,n,e){var t=Ud(a,n);if(t){var r=Object.getOwnPropertyDescriptor(t,n);return r.get?r.get.call(arguments.length<3?a:e):r.value}},cr.apply(null,arguments)}function Ee(a,n,e,t){var r=cr(wt(1&t?a.prototype:a),n,e);return 2&t&&typeof r=="function"?function(i){return r.apply(e,i)}:r}var Od=1024,Bd=1.5,Hd=4096,Vo=-1,Sa=(function(){function a(n,e){var t=arguments.length>2&&arguments[2]!==void 0?arguments[2]:Od;te(this,a),D(this,"texture",null),D(this,"dirty",!1),D(this,"dirtyRangeStart",1/0),D(this,"dirtyRangeEnd",-1),D(this,"indexMap",new Map),D(this,"freeIndices",[]),D(this,"nextIndex",0),this.gl=n,this.TEXELS_PER_ITEM=e,this.capacity=this.roundUpToPowerOfTwo(t);var r=this.computeTextureDimensions(this.capacity);this.textureWidth=r.width,this.textureHeight=r.height,this.data=new Float32Array(this.textureWidth*this.textureHeight*4),this.createTexture()}return ne(a,[{key:"computeTextureDimensions",value:function(e){var t=e*this.TEXELS_PER_ITEM,r=Math.min(t,Hd),i=Math.ceil(t/r);return{width:r,height:i}}},{key:"roundUpToPowerOfTwo",value:function(e){return Math.pow(2,Math.ceil(Math.log2(Math.max(1,e))))}},{key:"createTexture",value:function(){var e=this.gl;this.texture=e.createTexture(),e.activeTexture(e.TEXTURE0),e.bindTexture(e.TEXTURE_2D,this.texture),e.texImage2D(e.TEXTURE_2D,0,e.RGBA32F,this.textureWidth,this.textureHeight,0,e.RGBA,e.FLOAT,this.data),e.texParameteri(e.TEXTURE_2D,e.TEXTURE_MIN_FILTER,e.NEAREST),e.texParameteri(e.TEXTURE_2D,e.TEXTURE_MAG_FILTER,e.NEAREST),e.texParameteri(e.TEXTURE_2D,e.TEXTURE_WRAP_S,e.CLAMP_TO_EDGE),e.texParameteri(e.TEXTURE_2D,e.TEXTURE_WRAP_T,e.CLAMP_TO_EDGE),e.bindTexture(e.TEXTURE_2D,null)}},{key:"resize",value:function(e){if(!(e<=this.capacity)){var t=this.roundUpToPowerOfTwo(Math.ceil(e*Bd)),r=this.gl,i=this.computeTextureDimensions(t),o=new Float32Array(i.width*i.height*4);o.set(this.data),this.texture&&r.deleteTexture(this.texture),this.data=o,this.capacity=t,this.textureWidth=i.width,this.textureHeight=i.height,this.createTexture(),this.dirty=!0,this.dirtyRangeStart=0,this.dirtyRangeEnd=this.nextIndex}}},{key:"allocate",value:function(e){var t=this.indexMap.get(e);if(t!==void 0)return t;var r;return this.freeIndices.length>0?r=this.freeIndices.pop():(r=this.nextIndex++,r>=this.capacity&&this.resize(r+1)),this.indexMap.set(e,r),r}},{key:"free",value:function(e){var t=this.indexMap.get(e);if(t!==void 0){this.indexMap.delete(e),this.freeIndices.push(t);for(var r=t*this.TEXELS_PER_ITEM*4,i=0;i<this.TEXELS_PER_ITEM*4;i++)this.data[r+i]=0;this.markDirty(t)}}},{key:"getIndex",value:function(e){var t;return(t=this.indexMap.get(e))!==null&&t!==void 0?t:-1}},{key:"has",value:function(e){return this.indexMap.has(e)}},{key:"markDirty",value:function(e){this.dirty=!0,this.dirtyRangeStart=Math.min(this.dirtyRangeStart,e),this.dirtyRangeEnd=Math.max(this.dirtyRangeEnd,e+1)}},{key:"upload",value:function(){if(!(!this.dirty||!this.texture)){var e=this.gl,t=this.textureWidth;e.activeTexture(e.TEXTURE0),e.bindTexture(e.TEXTURE_2D,this.texture);var r=this.dirtyRangeStart*this.TEXELS_PER_ITEM,i=Math.min(this.dirtyRangeEnd*this.TEXELS_PER_ITEM,this.capacity*this.TEXELS_PER_ITEM);if(r<i)for(var o=Math.floor(r/t),s=Math.floor((i-1)/t),l=o;l<=s;l++){var u=l*t,d=Math.min(u+t,this.capacity*this.TEXELS_PER_ITEM),h=Math.max(r,u),c=Math.min(i,d);if(h<c){var f=h-u,g=c-h,y=this.data.subarray(h*4,c*4);e.texSubImage2D(e.TEXTURE_2D,0,f,l,g,1,e.RGBA,e.FLOAT,y)}}e.bindTexture(e.TEXTURE_2D,null),this.dirty=!1,this.dirtyRangeStart=1/0,this.dirtyRangeEnd=-1}}},{key:"bind",value:function(e){var t=this.gl;t.activeTexture(t.TEXTURE0+e),t.bindTexture(t.TEXTURE_2D,this.texture)}},{key:"getTexture",value:function(){return this.texture}},{key:"getCapacity",value:function(){return this.capacity}},{key:"getTextureWidth",value:function(){return this.textureWidth}},{key:"getTextureHeight",value:function(){return this.textureHeight}},{key:"getTexelsPerItem",value:function(){return this.TEXELS_PER_ITEM}},{key:"getCount",value:function(){return this.indexMap.size}},{key:"getHighWaterMark",value:function(){return this.nextIndex}},{key:"isDirty",value:function(){return this.dirty}},{key:"clear",value:function(){this.indexMap.clear(),this.freeIndices=[],this.nextIndex=0,this.data.fill(0),this.dirty=!0,this.dirtyRangeStart=0,this.dirtyRangeEnd=this.capacity}},{key:"restore",value:function(){this.createTexture(),this.dirty=!1,this.dirtyRangeStart=1/0,this.dirtyRangeEnd=-1}},{key:"kill",value:function(){this.texture&&(this.gl.deleteTexture(this.texture),this.texture=null),this.indexMap.clear(),this.freeIndices=[]}}])})();function $e(a){var n={},e={},t=0,r=O(a),i;try{for(r.s();!(i=r.n()).done;){var o=i.value,s=O(o.attributes),l;try{for(s.s();!(l=s.n()).done;){var u=l.value,d=u.name.replace(/^a_/,"");d in n||(n[d]=t,e[d]=u,t+=u.size)}}catch(h){s.e(h)}finally{s.f()}}}catch(h){r.e(h)}finally{r.f()}return{floatsPerItem:t,texelsPerItem:Math.max(1,Math.ceil(t/4)),offsets:n,specs:e}}var wa=(function(a){function n(e,t,r){var i;return te(this,n),i=me(this,n,[e,t.texelsPerItem,r]),i.floatsPerItem=t.floatsPerItem,i}return ye(n,a),ne(n,[{key:"updateAllAttributes",value:function(t,r){var i=this.indexMap.get(t);i===void 0&&(i=this.allocate(t));for(var o=i*this.TEXELS_PER_ITEM*4,s=Math.min(r.length,this.floatsPerItem),l=0;l<s;l++)this.data[o+l]=r[l];this.markDirty(i)}},{key:"updateAllAttributesAtRow",value:function(t,r){t>=this.capacity&&this.resize(t+1);for(var i=t*this.TEXELS_PER_ITEM*4,o=Math.min(r.length,this.floatsPerItem),s=0;s<o;s++)this.data[i+s]=r[s];this.markDirty(t)}}])})(Sa);function Aa(a,n,e){for(var t=[],r=new Set,i=0;i<a.length;i++){var o=a[i],s=O(o.attributes),l;try{for(s.s();!(l=s.n()).done;){var u=l.value,d=u.name.replace(/^a_/,"");if(!r.has(d)){r.add(d);var h=n.offsets[d];if(h!==void 0){var c=e?.get(i);t.push({sourceKey:u.source||d,packedOffset:h,size:u.size,isColor:u.size===4&&!!u.normalized,defaultNum:typeof u.defaultValue=="number"?u.defaultValue:u.defaultValue===!0?1:0,defaultColor:typeof u.defaultValue=="string"?u.defaultValue:"",sourceIndex:i,hasLifecycleHook:!!(c!=null&&c.getAttributeData)})}}}}catch(f){s.e(f)}finally{s.f()}}return t}function Da(a,n,e,t,r,i){e.fill(0);for(var o=0,s=a.length;o<s;o++){var l=a[o],u=l.packedOffset,d=void 0;if(l.hasLifecycleHook){var h=r.get(l.sourceIndex-i);d=h.getAttributeData(n,l.sourceKey),d===null&&(d=n[l.sourceKey])}else d=n[l.sourceKey];if(l.isColor){var c=typeof d=="string"?d:l.defaultColor||t,f=gt(c),g=ie(f,4),y=g[0],m=g[1],v=g[2],p=g[3];e[u]=y/255,e[u+1]=m/255,e[u+2]=v/255,e[u+3]=p/255}else if(l.size===1)e[u]=typeof d=="number"?d:typeof d=="boolean"?d?1:0:l.defaultNum;else{var b=Array.isArray(d)?d:null;if(b)for(var T=0;T<l.size;T++){var _;e[u+T]=(_=b[T])!==null&&_!==void 0?_:0}}}}var ma=["r","g","b","a"];function tn(a,n){var e=a.offsets,t=a.specs,r=a.texelsPerItem,i=a.floatsPerItem,o=Object.keys(e);if(o.length===0||i===0)return{fetchCode:"",varyingAssignments:""};var s=n.varPrefix,l=n.baseTexelExpr,u=n.textureWidthUniform,d=n.textureSamplerUniform,h=n.outputPrefix,c=h===void 0?"v_":h,f=[];f.push("  int ".concat(s,"BaseTexel = ").concat(l,";")),f.push("");for(var g=0;g<r;g++)f.push("  ivec2 ".concat(s,"Coord").concat(g," = ivec2((").concat(s,"BaseTexel + ").concat(g,") % ").concat(u,", (").concat(s,"BaseTexel + ").concat(g,") / ").concat(u,");")),f.push("  vec4 ".concat(s,"Texel").concat(g," = texelFetch(").concat(d,", ").concat(s,"Coord").concat(g,", 0);"));f.push("");for(var y=[],m=function(){var T=p[v],_=t[T],E=e[T],A=Math.floor(E/4),w=E%4,S="".concat(s,"Texel").concat(A),C="".concat(s,"Texel").concat(A+1),G="".concat(s,"Fetched_").concat(T);if(_.size===1)f.push("  float ".concat(G," = ").concat(S,".").concat(ma[w],";"));else if(_.size===4&&w===0)f.push("  vec4 ".concat(G," = ").concat(S,";"));else{var L=w+_.size;if(L<=4){var N="vec".concat(_.size),k=ma.slice(w,L).join("");f.push("  ".concat(N," ").concat(G," = ").concat(S,".").concat(k,";"))}else{var I=_.size===4?"vec4":"vec".concat(_.size),W=ma.slice(w).map(function(P){return"".concat(S,".").concat(P)}),F=ma.slice(0,L-4).map(function(P){return"".concat(C,".").concat(P)}),x=[].concat(Q(W),Q(F)).join(", ");f.push("  ".concat(I," ").concat(G," = ").concat(I,"(").concat(x,");"))}}y.push("  ".concat(c).concat(T," = ").concat(G,";"))},v=0,p=o;v<p.length;v++)m();return{fetchCode:f.join(`
`),varyingAssignments:y.join(`
`)}}function br(a,n,e){if(!(!n||e.type==="sampler2D"))switch(e.type){case"float":a.uniform1f(n,e.value);break;case"int":case"bool":a.uniform1i(n,e.value);break;case"vec2":a.uniform2fv(n,e.value);break;case"vec3":a.uniform3fv(n,e.value);break;case"vec4":a.uniform4fv(n,e.value);break;case"mat3":a.uniformMatrix3fv(n,!1,e.value);break;case"mat4":a.uniformMatrix4fv(n,!1,e.value);break}}var $d=D(D(D(D(D(D(D(D({},WebGL2RenderingContext.BOOL,1),WebGL2RenderingContext.BYTE,1),WebGL2RenderingContext.UNSIGNED_BYTE,1),WebGL2RenderingContext.SHORT,2),WebGL2RenderingContext.UNSIGNED_SHORT,2),WebGL2RenderingContext.INT,4),WebGL2RenderingContext.UNSIGNED_INT,4),WebGL2RenderingContext.FLOAT,4);function ya(a){var n=a.match(/^(#version[^\n]*\n)/);return n?n[1]+`#define PICKING_MODE
`+a.slice(n[1].length):`#define PICKING_MODE
`+a}var Lt=(function(){function a(n,e,t){te(this,a),D(this,"floats",new Float32Array),D(this,"ints",new Uint32Array),D(this,"constantArray",new Float32Array),D(this,"capacity",0),D(this,"verticesCount",0),D(this,"bufferGeneration",0),D(this,"uploadedGeneration",new Map),D(this,"constantBufferGeneration",0),D(this,"uploadedConstantGeneration",new Map),D(this,"renderOffset",0),D(this,"renderCount",-1),D(this,"debugStats",{drawCalls:0,verticesDrawn:0,bufferUploadBytes:0}),D(this,"shadersLogged",!1),D(this,"pickProgram",null);var r=this.getDefinition();if(this.VERTICES=r.VERTICES,this.VERTEX_SHADER_SOURCE=r.VERTEX_SHADER_SOURCE,this.FRAGMENT_SHADER_SOURCE=r.FRAGMENT_SHADER_SOURCE,this.UNIFORMS=r.UNIFORMS,this.ATTRIBUTES=r.ATTRIBUTES,this.METHOD=r.METHOD,this.CONSTANT_ATTRIBUTES="CONSTANT_ATTRIBUTES"in r?r.CONSTANT_ATTRIBUTES:[],this.CONSTANT_DATA="CONSTANT_DATA"in r?r.CONSTANT_DATA:[],this.isInstanced="CONSTANT_ATTRIBUTES"in r,this.ATTRIBUTES_ITEMS_COUNT=hr(this.ATTRIBUTES),this.STRIDE=this.VERTICES*this.ATTRIBUTES_ITEMS_COUNT,this.renderer=t,this.normalProgram=this.getProgramInfo("normal",n,r.VERTEX_SHADER_SOURCE,r.FRAGMENT_SHADER_SOURCE,null),this.pickProgram=this.getProgramInfo("pick",n,ya(r.VERTEX_SHADER_SOURCE),ya(r.FRAGMENT_SHADER_SOURCE),null),this.isInstanced){var i=hr(this.CONSTANT_ATTRIBUTES);if(this.CONSTANT_DATA.length!==this.VERTICES)throw new Error("Program: error while getting constant data (expected ".concat(this.VERTICES," items, received ").concat(this.CONSTANT_DATA.length," instead)"));this.constantArray=new Float32Array(this.CONSTANT_DATA.length*i);for(var o=0;o<this.CONSTANT_DATA.length;o++){var s=this.CONSTANT_DATA[o];if(s.length!==i)throw new Error("Program: error while getting constant data (one vector has ".concat(s.length," items instead of ").concat(i,")"));for(var l=0;l<s.length;l++)this.constantArray[o*i+l]=s[l]}this.STRIDE=this.ATTRIBUTES_ITEMS_COUNT}}return ne(a,[{key:"kill",value:function(){Ro(this.normalProgram),this.pickProgram&&Ro(this.pickProgram)}},{key:"resetDebugStats",value:function(){this.debugStats.drawCalls=0,this.debugStats.verticesDrawn=0,this.debugStats.bufferUploadBytes=0}},{key:"getProgramInfo",value:function(e,t,r,i,o){var s=t.createBuffer();if(s===null)throw new Error("Program: error while creating the WebGL buffer.");var l=fr(t,r),u=gr(t,i),d=vr(t,[l,u]),h={};this.UNIFORMS.forEach(function(g){var y=t.getUniformLocation(d,g);y&&(h[g]=y)});var c={};this.ATTRIBUTES.forEach(function(g){c[g.name]=t.getAttribLocation(d,g.name)});var f;if(this.isInstanced&&(this.CONSTANT_ATTRIBUTES.forEach(function(g){c[g.name]=t.getAttribLocation(d,g.name)}),f=t.createBuffer(),f===null))throw new Error("Program: error while creating the WebGL constant buffer.");return{name:e,program:d,gl:t,frameBuffer:o,buffer:s,constantBuffer:f||{},uniformLocations:h,attributeLocations:c,isPicking:e==="pick",vertexShader:l,fragmentShader:u}}},{key:"bindProgram",value:function(e){var t=this,r=0,i=e.gl,o=e.buffer;if(this.isInstanced){if(i.bindBuffer(i.ARRAY_BUFFER,e.constantBuffer),r=0,this.CONSTANT_ATTRIBUTES.forEach(function(d){return r+=t.bindAttribute(d,e,r,!1)}),this.uploadedConstantGeneration.get(e.constantBuffer)!==this.constantBufferGeneration){var l;i.bufferData(i.ARRAY_BUFFER,this.constantArray,i.STATIC_DRAW),this.uploadedConstantGeneration.set(e.constantBuffer,this.constantBufferGeneration),(l=this.renderer)!==null&&l!==void 0&&l.getSetting("DEBUG_logRenderStats")&&(this.debugStats.bufferUploadBytes+=this.constantArray.byteLength)}if(i.bindBuffer(i.ARRAY_BUFFER,e.buffer),r=this.renderOffset*this.ATTRIBUTES_ITEMS_COUNT*Float32Array.BYTES_PER_ELEMENT,this.ATTRIBUTES.forEach(function(d){return r+=t.bindAttribute(d,e,r,!0)}),this.uploadedGeneration.get(o)!==this.bufferGeneration){var u;i.bufferData(i.ARRAY_BUFFER,this.floats,i.DYNAMIC_DRAW),this.uploadedGeneration.set(o,this.bufferGeneration),(u=this.renderer)!==null&&u!==void 0&&u.getSetting("DEBUG_logRenderStats")&&(this.debugStats.bufferUploadBytes+=this.floats.byteLength)}}else if(i.bindBuffer(i.ARRAY_BUFFER,o),r=0,this.ATTRIBUTES.forEach(function(d){return r+=t.bindAttribute(d,e,r)}),this.uploadedGeneration.get(o)!==this.bufferGeneration){var s;i.bufferData(i.ARRAY_BUFFER,this.floats,i.DYNAMIC_DRAW),this.uploadedGeneration.set(o,this.bufferGeneration),(s=this.renderer)!==null&&s!==void 0&&s.getSetting("DEBUG_logRenderStats")&&(this.debugStats.bufferUploadBytes+=this.floats.byteLength)}i.bindBuffer(i.ARRAY_BUFFER,null)}},{key:"unbindProgram",value:function(e){var t=this;this.isInstanced?(this.CONSTANT_ATTRIBUTES.forEach(function(r){return t.unbindAttribute(r,e,!1)}),this.ATTRIBUTES.forEach(function(r){return t.unbindAttribute(r,e,!0)})):this.ATTRIBUTES.forEach(function(r){return t.unbindAttribute(r,e)})}},{key:"bindAttribute",value:function(e,t,r,i){var o=$d[e.type];if(typeof o!="number")throw new Error('Program.bind: yet unsupported attribute type "'.concat(e.type,'"'));var s=t.attributeLocations[e.name],l=t.gl;if(s!==-1){l.enableVertexAttribArray(s);var u=this.isInstanced?(i?this.ATTRIBUTES_ITEMS_COUNT:hr(this.CONSTANT_ATTRIBUTES))*Float32Array.BYTES_PER_ELEMENT:this.ATTRIBUTES_ITEMS_COUNT*Float32Array.BYTES_PER_ELEMENT;l.vertexAttribPointer(s,e.size,e.type,e.normalized||!1,u,r),this.isInstanced&&i&&l.vertexAttribDivisor(s,1)}return e.size*o}},{key:"unbindAttribute",value:function(e,t,r){var i=t.attributeLocations[e.name],o=t.gl;i!==-1&&(o.disableVertexAttribArray(i),this.isInstanced&&r&&o.vertexAttribDivisor(i,0))}},{key:"reallocate",value:function(e){e!==this.capacity&&(this.capacity=e,this.verticesCount=this.VERTICES*e,this.floats=new Float32Array(this.isInstanced?this.capacity*this.ATTRIBUTES_ITEMS_COUNT:this.verticesCount*this.ATTRIBUTES_ITEMS_COUNT),this.ints=new Uint32Array(this.floats.buffer),this.invalidateBuffers())}},{key:"invalidateBuffers",value:function(){this.bufferGeneration++,this.constantBufferGeneration++}},{key:"hasNothingToRender",value:function(){return this.verticesCount===0}},{key:"setTypedUniform",value:function(e,t){var r;br(t.gl,(r=t.uniformLocations[e.name])!==null&&r!==void 0?r:null,e)}},{key:"renderProgram",value:function(e,t){var r=t.gl,i=t.program,o=t.isPicking;o?r.disable(r.BLEND):r.enable(r.BLEND),r.useProgram(i),this.setUniforms(e,t),this.drawWebGL(this.METHOD,t)}},{key:"render",value:function(e,t,r){var i;if(!this.shadersLogged&&(i=this.renderer)!==null&&i!==void 0&&i.getSetting("DEBUG_logShaders")&&(this.shadersLogged=!0,console.log("[sigma] DEBUG_logShaders: ".concat(this.constructor.name),{normal:{vertexShaderSource:this.VERTEX_SHADER_SOURCE,fragmentShaderSource:this.FRAGMENT_SHADER_SOURCE},pick:{vertexShaderSource:ya(this.VERTEX_SHADER_SOURCE),fragmentShaderSource:ya(this.FRAGMENT_SHADER_SOURCE)}})),!this.hasNothingToRender()){this.renderOffset=t??0,this.renderCount=r??-1;var o=this.normalProgram.gl;if(o.bindFramebuffer(o.FRAMEBUFFER,null),o.viewport(0,0,e.width*e.pixelRatio,e.height*e.pixelRatio),this.bindProgram(this.normalProgram),this.renderProgram(e,this.normalProgram),this.unbindProgram(this.normalProgram),this.pickProgram&&e.pickingFrameBuffer){var s=Math.ceil(e.width*e.pixelRatio/e.downSizingRatio),l=Math.ceil(e.height*e.pixelRatio/e.downSizingRatio);o.bindFramebuffer(o.FRAMEBUFFER,e.pickingFrameBuffer),o.viewport(0,0,s,l),this.bindProgram(this.pickProgram),this.renderProgram(e,this.pickProgram),this.unbindProgram(this.pickProgram),o.bindFramebuffer(o.FRAMEBUFFER,null),o.viewport(0,0,e.width*e.pixelRatio,e.height*e.pixelRatio)}}}},{key:"drawWebGL",value:function(e,t){var r,i=t.gl,o=this.renderCount>=0?this.renderCount:this.capacity;(r=this.renderer)!==null&&r!==void 0&&r.getSetting("DEBUG_logRenderStats")&&(this.debugStats.drawCalls++,this.debugStats.verticesDrawn+=o*this.VERTICES),this.isInstanced?i.drawArraysInstanced(e,0,this.VERTICES,o):i.drawArrays(e,this.renderOffset*this.VERTICES,o*this.VERTICES)}}])})(),yt=2,Cn=7,qo={below:0,above:1,left:2,right:3};function Vd(){var a=`#version 300 es
precision highp float;

uniform mat3 u_matrix;
uniform vec2 u_resolution;
uniform float u_labelPixelSnapping;
uniform float u_sizeRatio;
uniform float u_correctionRatio;
uniform float u_cameraAngle;
uniform float u_pixelRatio;
uniform float u_labelMargin;
uniform float u_zoomLabelSizeRatio;

uniform sampler2D u_nodeDataTexture;
uniform int u_nodeDataTextureWidth;
uniform sampler2D u_nodeFrameTexture;
uniform int u_nodeFrameTextureWidth;

// Atlas size is fixed at 2048\xD72048 \u2014 matches AttachmentManager.ATLAS_SIZE.
uniform sampler2D u_atlasTexture;
const vec2 u_atlasSize = vec2(2048.0);

// Per-instance
in float a_nodeIndex;           // node-data texture index
in vec4 a_atlasRect;            // x, y, width, height in atlas pixels
in vec2 a_attachmentSize;       // attachment dimensions (CSS px)
in float a_positionMode;        // label position: 0=right 1=left 2=above 3=below 4=over
in float a_attachmentPlacement; // 0=below 1=above 2=left 3=right (relative to label)
in float a_labelWidth;          // label width (CSS px)
in float a_labelHeight;         // label height: font line box (CSS px)
in float a_textHeight;          // actual glyph height (CSS px)
in float a_labelAngle;          // label rotation angle (radians)

// Per-vertex (constant)
in vec2 a_quadCorner;           // [-1,-1], [1,-1], [-1,1], [1,1]

out vec2 v_texCoord;

`.concat(lt,`
`).concat(Ct,`
`).concat(rn,`
`).concat($o,`
`).concat(Fd,`

void main() {
  int nodeIdx = int(a_nodeIndex);

  // Node data: (x, y, size, shapeId).
  vec4 nodeData = readNodeData(u_nodeDataTexture, u_nodeDataTextureWidth, nodeIdx);
  vec2 nodePos = nodeData.xy;
  float nodeSize = nodeData.z;

  // Normalized edge distance from the shared frame texture (the frame-pass ran
  // the SDF search once; we just read the result).
  float edgeDist = readFrameTexel(u_nodeFrameTexture, u_nodeFrameTextureWidth, nodeIdx).r;

  // Per-node label rotation alignment: 0 = viewport, 1 = label turns with camera.
  float labelRotation = readNodeFlags(u_nodeDataTexture, u_nodeDataTextureWidth, nodeIdx).g;

  vec3 nodeClip = u_matrix * vec3(nodePos, 1.0);

  // Node radius in physical pixels (matches label/background).
  float matrixScaleX = length(vec2(u_matrix[0][0], u_matrix[1][0]));
  float nodeRadiusGraphSpace = nodeSize * u_correctionRatio / u_sizeRatio * 2.0;
  float nodeRadiusPixels = nodeRadiusGraphSpace * matrixScaleX * u_resolution.x / 2.0;

  // CSS-px inputs -> physical px, scaled by the zoom-dependent label ratio, so
  // the attachment stays glued to the label box exactly as the label scales.
  float zoomScale = u_zoomLabelSizeRatio;
  vec2 labelHalf = vec2(a_labelWidth, a_labelHeight) * 0.5 * zoomScale * u_pixelRatio;
  vec2 attachHalf = a_attachmentSize * 0.5 * zoomScale * u_pixelRatio;
  float gap = `).concat(yt.toFixed(1),` * zoomScale * u_pixelRatio;
  float labelMargin = u_labelMargin * zoomScale * u_pixelRatio;

  // Graph-aligned labels add the camera angle so the attachment orbits with the box.
  mat2 labelRotMat = rotate2D(a_labelAngle - labelRotation * u_cameraAngle);

  // Label box center relative to the node center (pre-rotation). The shape-aware
  // edge distance comes from the frame texture, so placement matches the label.
  vec2 boxCenter = vec2(0.0);
  if (a_positionMode < 4.0) {
    float labelStart = nodeRadiusPixels * edgeDist + labelMargin;
    float textHalf = a_textHeight * 0.5 * zoomScale * u_pixelRatio;
    boxCenter = labelBoxCenter(a_positionMode, labelStart, labelHalf, textHalf);
  }

  // Horizontal anchor of below/above attachments tracks the label position, so
  // the attachment hangs from the label edge nearest the node (or is centered
  // when the label itself is node-centered): right->left, left->right, else center.
  float anchorX = 0.0;
  if (a_positionMode < 0.5) anchorX = -labelHalf.x + attachHalf.x;       // right label
  else if (a_positionMode < 1.5) anchorX = labelHalf.x - attachHalf.x;   // left label

  // Attachment center relative to the box (pre-rotation, Y-down). This offset
  // depends only on the box, the gap and the attachment size \u2014 never the shape.
  vec2 attachCenter;
  if (a_attachmentPlacement < 0.5) {
    // below
    attachCenter = boxCenter + vec2(anchorX, labelHalf.y + gap + attachHalf.y);
  } else if (a_attachmentPlacement < 1.5) {
    // above
    attachCenter = boxCenter + vec2(anchorX, -(labelHalf.y + gap + attachHalf.y));
  } else if (a_attachmentPlacement < 2.5) {
    // left, top-aligned
    attachCenter = boxCenter + vec2(-(labelHalf.x + gap + attachHalf.x), -labelHalf.y + attachHalf.y);
  } else {
    // right, top-aligned
    attachCenter = boxCenter + vec2(labelHalf.x + gap + attachHalf.x, -labelHalf.y + attachHalf.y);
  }

  // Rotate the whole assembly by the label angle, around the node center.
  vec2 rotatedCenter = labelRotMat * attachCenter;
  vec2 cornerOffset = labelRotMat * (a_quadCorner * attachHalf);

  // Node center in screen px (Y-down).
  vec2 nodeScreen = vec2(
    (nodeClip.x + 1.0) * u_resolution.x,
    (1.0 - nodeClip.y) * u_resolution.y
  ) * 0.5;

  // Snap node center to the pixel grid so label/backdrop/attachment move as one.
  vec2 snapDelta = (round(nodeScreen) - nodeScreen) * u_labelPixelSnapping;

  // Snap the quad's top-left to integer pixels so atlas texels map 1:1.
  vec2 centerScreen = nodeScreen + rotatedCenter + snapDelta;
  vec2 topLeft = centerScreen - attachHalf;
  topLeft = mix(topLeft, round(topLeft), u_labelPixelSnapping);
  centerScreen = topLeft + attachHalf;

  vec2 vertexScreen = centerScreen + cornerOffset;
  gl_Position = vec4(
    vertexScreen.x * 2.0 / u_resolution.x - 1.0,
    1.0 - vertexScreen.y * 2.0 / u_resolution.y,
    0.0, 1.0
  );

  vec2 texOrigin = a_atlasRect.xy / u_atlasSize;
  vec2 texSize = a_atlasRect.zw / u_atlasSize;
  vec2 uv = (a_quadCorner + 1.0) / 2.0;
  v_texCoord = texOrigin + uv * texSize;
}
`);return a}var qd=`#version 300 es
precision highp float;

uniform sampler2D u_atlasTexture;

in vec2 v_texCoord;

layout(location = 0) out vec4 fragColor;
#ifdef PICKING_MODE
layout(location = 1) out vec4 pickColor;
#endif

void main() {
  // Canvas textures are premultiplied; output directly for (ONE, 1-SRC_ALPHA) blending
  vec4 color = texture(u_atlasTexture, v_texCoord);
  if (color.a < 0.01) discard;
  fragColor = color;
#ifdef PICKING_MODE
  pickColor = vec4(0.0); // Attachments are not pickable
#endif
}
`;function jd(a,n,e,t){var r,i,o=t.label,s=o===void 0?{}:o,l=(r=s.margin)!==null&&r!==void 0?r:an,u=(i=s.zoomToLabelSizeRatioFunction)!==null&&i!==void 0?i:function(){return 1},d=Vd(),h=qd,c=(function(f){function g(){var y;te(this,g);for(var m=arguments.length,v=new Array(m),p=0;p<m;p++)v[p]=arguments[p];return y=me(this,g,[].concat(v)),D(y,"totalCount",0),D(y,"bufferCapacity",0),y}return ye(g,f),ne(g,[{key:"getDefinition",value:function(){var m=WebGL2RenderingContext,v=m.FLOAT,p=m.TRIANGLE_STRIP;return{VERTICES:4,VERTEX_SHADER_SOURCE:d,FRAGMENT_SHADER_SOURCE:h,METHOD:p,UNIFORMS:["u_matrix","u_resolution","u_labelPixelSnapping","u_sizeRatio","u_correctionRatio","u_cameraAngle","u_pixelRatio","u_labelMargin","u_zoomLabelSizeRatio","u_nodeDataTexture","u_nodeDataTextureWidth","u_nodeFrameTexture","u_nodeFrameTextureWidth","u_atlasTexture"],ATTRIBUTES:[{name:"a_nodeIndex",size:1,type:v},{name:"a_atlasRect",size:4,type:v},{name:"a_attachmentSize",size:2,type:v},{name:"a_positionMode",size:1,type:v},{name:"a_attachmentPlacement",size:1,type:v},{name:"a_labelWidth",size:1,type:v},{name:"a_labelHeight",size:1,type:v},{name:"a_textHeight",size:1,type:v},{name:"a_labelAngle",size:1,type:v}],CONSTANT_ATTRIBUTES:[{name:"a_quadCorner",size:2,type:v}],CONSTANT_DATA:[[-1,-1],[1,-1],[-1,1],[1,1]]}}},{key:"processAttachment",value:function(m,v){var p=this.floats,b=m*this.STRIDE;p[b++]=v.nodeIndex,p[b++]=v.atlasX,p[b++]=v.atlasY,p[b++]=v.atlasW,p[b++]=v.atlasH,p[b++]=v.attachWidth,p[b++]=v.attachHeight,p[b++]=v.positionMode,p[b++]=v.attachmentPlacement,p[b++]=v.labelWidth,p[b++]=v.labelHeight,p[b++]=v.textHeight,p[b++]=v.labelAngle}},{key:"setUniforms",value:function(m,v){var p=v.gl,b=v.uniformLocations;p.uniformMatrix3fv(b.u_matrix,!1,m.matrix),p.uniform2f(b.u_resolution,m.width*m.pixelRatio,m.height*m.pixelRatio),p.uniform1f(b.u_labelPixelSnapping,m.labelPixelSnapping),p.uniform1f(b.u_sizeRatio,m.sizeRatio),p.uniform1f(b.u_correctionRatio,m.correctionRatio),p.uniform1f(b.u_cameraAngle,m.cameraAngle),p.uniform1f(b.u_pixelRatio,m.pixelRatio),p.uniform1f(b.u_labelMargin,g.labelMargin),p.uniform1f(b.u_zoomLabelSizeRatio,1/u(m.zoomRatio)),p.uniform1i(b.u_nodeDataTexture,m.nodeDataTextureUnit),p.uniform1i(b.u_nodeDataTextureWidth,m.nodeDataTextureWidth),p.uniform1i(b.u_nodeFrameTexture,m.nodeFrameTextureUnit),p.uniform1i(b.u_nodeFrameTextureWidth,m.nodeFrameTextureWidth),p.uniform1i(b.u_atlasTexture,Cn)}},{key:"reallocateAttachments",value:function(m){this.totalCount=m,m>this.bufferCapacity&&(this.bufferCapacity=Math.max(m,Math.ceil(this.bufferCapacity*1.5)||10),Ee(g,"reallocate",this,3)([this.bufferCapacity]))}},{key:"hasNothingToRender",value:function(){return this.totalCount===0}},{key:"drawWebGL",value:function(m,v){var p=v.gl;this.totalCount!==0&&p.drawArraysInstanced(m,0,this.VERTICES,this.totalCount)}}])})(Lt);return D(c,"labelMargin",l),new c(a,n,e)}var pt=5;function Ra(a,n){return[].concat(Q(n),Q(a.map(function(e){var t;return{attributes:(t=e.attributes)!==null&&t!==void 0?t:[]}})))}function on(a,n){var e=$e(Ra(a,n)),t=new Set(a.flatMap(function(u){var d;return(d=u.attributes)!==null&&d!==void 0?d:[]}).map(function(u){return u.name.replace(/^a_/,"")})),r={},i={},o=O(t),s;try{for(o.s();!(s=o.n()).done;){var l=s.value;r[l]=e.offsets[l],i[l]=e.specs[l]}}catch(u){o.e(u)}finally{o.f()}return H(H({},e),{},{offsets:r,specs:i})}function Xd(a,n){var e=new Set(["u_matrix","u_sizeRatio","u_correctionRatio","u_cameraAngle","u_pickingPadding","u_nodeDataTexture","u_layerAttributeTexture"]),t=new Set,r=a.flatMap(function(f){return f.uniforms}).filter(function(f){return e.has(f.name)||t.has(f.name)?!1:(t.add(f.name),!0)}).map(function(f){return"uniform ".concat(f.type," ").concat(f.name,";")}).join(`
`),i=n.flatMap(function(f){return f.uniforms}).filter(function(f){return e.has(f.name)||t.has(f.name)?!1:(t.add(f.name),!0)}).map(function(f){return"uniform ".concat(f.type," ").concat(f.name,";")}).join(`
`),o=Ra(a,n),s=new Set,l=o.flatMap(function(f){return f.attributes}).filter(function(f){var g=f.name.replace(/^a_/,"");return s.has(g)?!1:(s.add(g),!0)}).map(function(f){var g=f.name.replace(/^a_/,""),y=f.size===1?"float":"vec".concat(f.size);return"out ".concat(y," v_").concat(g,";")}).join(`
`),u=tn($e(o),{varPrefix:"layer",baseTexelExpr:"nodeIdx * u_layerAttributeTexelsPerNode",textureWidthUniform:"u_layerAttributeTextureWidth",textureSamplerUniform:"u_layerAttributeTexture"}),d=u.fetchCode,h=u.varyingAssignments,c=`#version 300 es

// Standard node attributes (per instance) - minimal buffer usage
in float a_nodeIndex;  // Index into node data texture AND layer attribute texture
in vec4 a_id;          // Node ID for picking
in float a_opacity;    // Node opacity, applied once to the final fragment

// Constant attributes (per vertex, same for all instances)
in vec2 a_quadCorner;  // (-1,-1), (1,-1), (1,1), (-1,1) for quad corners

// Standard uniforms
uniform mat3 u_matrix;
uniform float u_sizeRatio;
uniform float u_correctionRatio;
uniform float u_cameraAngle;
#ifdef PICKING_MODE
uniform float u_pickingPadding;
#endif
uniform sampler2D u_nodeDataTexture;
uniform int u_nodeDataTextureWidth;

// Layer attribute texture uniforms
uniform sampler2D u_layerAttributeTexture;
uniform int u_layerAttributeTextureWidth;
uniform int u_layerAttributeTexelsPerNode;

`.concat(r,`
`).concat(i,`

// Standard varyings
out vec2 v_uv;                    // Normalized coordinates [-1, 1]
out vec4 v_id;
out float v_opacity;
out float v_antialiasingWidth;    // Width for antialiasing in UV space
out float v_pixelSize;            // Node size in pixels (for pixel-mode borders)
out float v_pixelToUV;            // Conversion factor: multiply by this to convert screen pixels to UV units
out float v_shapeId;              // Shape ID for multi-shape programs

// Layer varyings
`).concat(l,`

// Node-data fetch helpers (geometry texel + rotation-flags texel)
`).concat(lt,`
`).concat(Ct,`

void main() {
  // Fetch node geometry: vec4(x, y, size, shapeId).
  int nodeIdx = int(a_nodeIndex);

  // Hidden nodes are flagged with a negative row by NodeProgram.process(). Push
  // the whole quad outside the clip volume: every vertex lands at the same
  // out-of-range position, so the primitive is fully clipped and rasterizes
  // nothing \u2014 neither to the frame buffer nor to the picking buffer.
  if (nodeIdx < 0) {
    gl_Position = vec4(2.0, 0.0, 0.0, 1.0);
    v_id = vec4(0.0);
    return;
  }

  vec4 nodeData = readNodeData(u_nodeDataTexture, u_nodeDataTextureWidth, nodeIdx);
  vec2 a_position = nodeData.xy;
  float a_size = nodeData.z;
  v_shapeId = nodeData.w;  // Pass shape ID to fragment shader

  // Per-node rotation alignment: 0 = viewport (screen-upright), 1 = graph.
  float nodeRotation = readNodeFlags(u_nodeDataTexture, u_nodeDataTextureWidth, nodeIdx).r;

`).concat(d,`

  // Calculate the actual size in pixels
  float size = a_size * u_correctionRatio / u_sizeRatio * 2.0;

  // In PICKING_MODE, inflate the quad by nodePickingPadding pixels on each side
  #ifdef PICKING_MODE
    float paddedSize = size + u_pickingPadding * u_correctionRatio;
    vec2 offset = a_quadCorner * paddedSize;
  #else
    vec2 offset = a_quadCorner * size;
  #endif
  // Counter-rotate the quad offset so viewport-aligned nodes stay upright as the
  // camera turns. Graph-aligned nodes (nodeRotation=1) skip it and turn with the
  // camera. The angle scales by (1 - nodeRotation) so both fall out of one path.
  {
    float ca = u_cameraAngle * (1.0 - nodeRotation);
    float c = cos(ca);
    float s = sin(ca);
    offset = mat2(c, s, -s, c) * offset;
  }
  vec2 position = a_position + offset;

  gl_Position = vec4(
    (u_matrix * vec3(position, 1)).xy,
    0,
    1
  );

  // In PICKING_MODE, UV is scaled beyond [-1, 1] to match the inflated quad
  #ifdef PICKING_MODE
    v_uv = a_quadCorner * (paddedSize / size);
  #else
    v_uv = a_quadCorner;
  #endif

  // Pass ID to fragment shader
  v_id = a_id;
  v_opacity = a_opacity;

  // Pass pixel size for layers that need pixel-mode calculations
  // Multiply by 2 because 'size' is half-width (offset from center), not full diameter
  v_pixelSize = size * 2.0;

  // Conversion factor from screen pixels to UV units
  // Same derivation as v_antialiasingWidth which represents ~1 pixel in UV space
  // P pixels in UV space = P * u_correctionRatio / size
  v_pixelToUV = u_correctionRatio / size;

  // We use an antialiasing width of 1px (so v_pixelToUV)
  v_antialiasingWidth = v_pixelToUV;

  // Pass layer attributes to fragment shader (fetched from texture)
`).concat(h,`
}
`);return c}function Yd(a,n,e){var t=arguments.length>3&&arguments[3]!==void 0?arguments[3]:!0,r=n.map(function(g,y){var m="layer_".concat(g.name),v=[].concat(Q(g.attributes.map(function(p){return"v_".concat(p.name.replace(/^a_/,""))})),Q(g.uniforms.map(function(p){return p.name}))).join(", ");return"  // Layer ".concat(y+1,": ").concat(g.name,`
  color = blendOver(color, `).concat(m,"(").concat(v,"));")}).join(`

`),i=new Set(["u_correctionRatio"]),o=new Set,s=a.flatMap(function(g){return g.uniforms}).filter(function(g){return i.has(g.name)||o.has(g.name)?!1:(o.add(g.name),!0)}).map(function(g){return"uniform ".concat(g.type," ").concat(g.name,";")}).join(`
`),l=n.flatMap(function(g){return g.uniforms}).filter(function(g){return i.has(g.name)||o.has(g.name)?!1:(o.add(g.name),!0)}).map(function(g){return"uniform ".concat(g.type," ").concat(g.name,";")}).join(`
`),u=new Set,d=Ra(a,n).flatMap(function(g){return g.attributes}).filter(function(g){var y=g.name.replace(/^a_/,"");return u.has(y)?!1:(u.add(y),!0)}).map(function(g){var y=g.name.replace(/^a_/,""),m=g.size===1?"float":"vec".concat(g.size);return"in ".concat(m," v_").concat(y,";")}).join(`
`),h=pr(a),c=Pd(a,e),f=`#version 300 es
precision highp float;

// Standard varyings
in vec2 v_uv;
in vec4 v_id;
in float v_opacity;
in float v_antialiasingWidth;
in float v_pixelSize;
in float v_pixelToUV;
in float v_shapeId;  // Shape ID for multi-shape programs

// Standard uniforms (needed for some layer calculations like pixel-mode borders)
uniform float u_correctionRatio;
#ifdef PICKING_MODE
uniform float u_pickingPadding;
#endif

// Shape uniforms
`.concat(s,`

// Layer uniforms
`).concat(l,`

// Layer varyings
`).concat(d,`

// Fragment output (single target - picking handled via separate pass)
out vec4 fragColor;

// LayerContext struct - provides rendering context to all layers
struct LayerContext {
  float sdf;             // Signed distance from shape boundary (negative inside)
  vec2 uv;               // UV coordinates [-1, 1], center at (0,0)
  float shapeSize;       // Effective shape size (~diameter) in UV space (1.0 - aaWidth)
  float shapeHalfSize;   // Effective shape half size (~radius) in UV space
  float pixelSize;       // Node full size (~diameter) in screen pixels
  float aaWidth;         // Anti-aliasing width for smooth transitions
  float correctionRatio; // Scaling factor for consistent rendering across zoom levels
  float pixelToUV;       // Conversion factor: multiply screen pixels by this to get UV units
  float inradiusFactor;  // Ratio of inradius to circumradius (shape depth factor)
};

LayerContext context;  // Global instance, populated before layer calls

// Alpha "over" compositing for layer blending
vec4 blendOver(vec4 bg, vec4 fg) {
  float a = fg.a;
  return vec4(mix(bg.rgb, fg.rgb, a), bg.a + a * (1.0 - bg.a));
}

// SDF shape functions
`).concat(h,`

// Shape selector function (sets context.sdf and context.inradiusFactor)
`).concat(c,`

// Layer functions
`).concat(n.map(function(g){return g.glsl}).join(`

`),`

void main() {
  // 1. Setup LayerContext (available to all layer functions)
  context.shapeSize = 1.0 - v_antialiasingWidth;
  context.shapeHalfSize = context.shapeSize * 0.5;
  context.pixelSize = v_pixelSize;
  context.uv = v_uv;
  context.aaWidth = v_antialiasingWidth;
  context.correctionRatio = u_correctionRatio;
  context.pixelToUV = v_pixelToUV;

  // Query shape SDF based on shapeId (sets context.sdf and context.inradiusFactor)
  queryNodeSDF(int(v_shapeId), v_uv, context.shapeSize);

  // 2. Early discard for pixels fully outside the shape (with AA margin)
  // In PICKING_MODE, allow extra fragments up to the picking padding distance
  #ifdef PICKING_MODE
    if (context.sdf > u_pickingPadding * v_pixelToUV + context.aaWidth) discard;
  #else
    if (context.sdf > context.aaWidth) discard;
  #endif

  // 3. Apply layers sequentially with "over" compositing
  vec4 color = vec4(0.0);

`).concat(r,`

  #ifdef PICKING_MODE
    // Picking pass: output node ID for pixels within the picking area.
    if (context.sdf > u_pickingPadding * v_pixelToUV) discard;
    fragColor = v_id;
  #else
`).concat(t?`    // Visual pass: apply antialiasing at shape boundary, node opacity once
    // smoothstep provides smooth transition from opaque to transparent
    float alpha = smoothstep(context.aaWidth, -context.aaWidth, context.sdf) * v_opacity;`:`    // Visual pass: hard-edged (no anti-aliasing gradient) shape boundary, node opacity applied once
    float alpha = (context.sdf < 0.0 ? 1.0 : 0.0) * v_opacity;`,`
    // Mix with transparent to fade both color AND alpha together (avoids bright halo)
    fragColor = mix(vec4(0.0), color, alpha);
  #endif
}
`);return f}function Kd(a,n){var e=new Set;return e.add("u_matrix"),e.add("u_sizeRatio"),e.add("u_correctionRatio"),e.add("u_cameraAngle"),e.add("u_pickingPadding"),e.add("u_nodeDataTexture"),e.add("u_nodeDataTextureWidth"),e.add("u_layerAttributeTexture"),e.add("u_layerAttributeTextureWidth"),e.add("u_layerAttributeTexelsPerNode"),a.forEach(function(t){t.uniforms.forEach(function(r){return e.add(r.name)})}),n.forEach(function(t){t.uniforms.forEach(function(r){return e.add(r.name)})}),Array.from(e)}function Zd(a){var n=WebGL2RenderingContext,e=n.UNSIGNED_BYTE,t=n.FLOAT;return[{name:"a_nodeIndex",size:1,type:t},{name:"a_id",size:4,type:e,normalized:!0},{name:"a_opacity",size:1,type:t}]}function Lo(a){var n=a.shapes,e=a.layers,t=a.shapeGlobalIds,r=a.antialias,i=r===void 0?!0:r;return{vertexShader:Xd(n,e),fragmentShader:Yd(n,e,t,i),uniforms:Kd(n,e),attributes:Zd()}}function jo(a,n,e){var t=on(a,n),r=t.specs;return Object.keys(r).map(function(i){return"flat ".concat(e," ").concat(r[i].size===1?"float":"vec".concat(r[i].size)," v_").concat(i,";")}).join(`
`)}function Qd(a){var n,e,t=a.shapes,r=a.layers,i=a.shapeGlobalIds,o=tn(on(t,r),{varPrefix:"nodeAttr",baseTexelExpr:"nodeIdx * u_layerAttributeTexelsPerNode",textureWidthUniform:"u_layerAttributeTextureWidth",textureSamplerUniform:"u_layerAttributeTexture"}),s=t.length===1?"float inradiusFactor = ".concat(xe((n=t[0].inradiusFactor)!==null&&n!==void 0?n:1),";"):"float inradiusFactor = ".concat(xe((e=t[0].inradiusFactor)!==null&&e!==void 0?e:1),`;
  switch (int(shapeId)) {
`).concat(t.map(function(u,d){var h,c=i?i[d]:d;return"    case ".concat(c,": inradiusFactor = ").concat(xe((h=u.inradiusFactor)!==null&&h!==void 0?h:1),"; break;")}).join(`
`),`
    default: break;
  }`),l=`#version 300 es

in float a_nodeIndex;
in float a_labelWidth;
in float a_labelHeight;
in float a_textHeight;
in float a_positionMode;
in float a_labelAngle;
in vec4 a_backdropColor;
in vec4 a_backdropShadowColor;
in float a_backdropShadowBlur;
in float a_backdropPadding;
in vec4 a_backdropBorderColor;
in vec4 a_backdropExtra; // [borderWidth, cornerRadius, labelPadding, area]
in vec2 a_labelBoxOffset;
in vec2 a_quadCorner;

uniform mat3 u_matrix;
uniform float u_sizeRatio;
uniform float u_correctionRatio;
uniform float u_cameraAngle;
uniform vec2 u_resolution;
uniform float u_pixelRatio;
uniform float u_labelMargin;
uniform float u_zoomLabelSizeRatio;
uniform float u_labelPixelSnapping;
uniform sampler2D u_nodeDataTexture;
uniform int u_nodeDataTextureWidth;
uniform sampler2D u_nodeFrameTexture;
uniform int u_nodeFrameTextureWidth;
uniform sampler2D u_layerAttributeTexture;
uniform int u_layerAttributeTextureWidth;
uniform int u_layerAttributeTexelsPerNode;

out vec2 v_uv;
out vec2 v_nodeCenter;
out float v_nodeRadius;
out vec2 v_labelCenter;
out vec2 v_labelHalfSize;
out float v_aaWidth;
out float v_shapeId;
out float v_nodeRotation;
out float v_labelAngle;
out vec4 v_backdropColor;
out vec4 v_backdropShadowColor;
out float v_backdropShadowBlur;
out float v_backdropPadding;
out vec4 v_backdropBorderColor;
out float v_backdropBorderWidth;
out float v_backdropCornerRadius;
out float v_backdropArea;
`.concat(jo(t,r,"out"),`

`).concat(lt,`
`).concat(Ct,`
`).concat(rn,`

void main() {
  int nodeIdx = int(a_nodeIndex);
`).concat(o.fetchCode,`
`).concat(o.varyingAssignments,`

  // Node data: (x, y, size, shapeId). shapeId (global) is forwarded to the
  // fragment shader, which keeps the shape SDF for the outline.
  vec4 nodeData = readNodeData(u_nodeDataTexture, u_nodeDataTextureWidth, nodeIdx);
  vec2 nodePosition = nodeData.xy;
  float nodeSize = nodeData.z;
  float shapeId = nodeData.w;

  // Per-node rotation alignment (0 = viewport, 1 = graph). nodeRotation drives
  // the fragment's shape outline; labelRotation turns the label box with camera.
  vec4 nodeFlags = readNodeFlags(u_nodeDataTexture, u_nodeDataTextureWidth, nodeIdx);
  float nodeRotation = nodeFlags.r;
  float labelRotation = nodeFlags.g;
  v_nodeRotation = nodeRotation;

  `).concat(Bo,`
  // CSS pixel attributes are multiplied by u_pixelRatio to match nodeRadiusPixels,
  // which is already in physical pixels (nodeRadiusNDC * u_resolution.x / 2.0).
  float padding = a_backdropPadding * u_pixelRatio;
  float shadowBlur = a_backdropShadowBlur * u_pixelRatio;
  // Unpack a_backdropExtra: [borderWidth, cornerRadius, labelPadding, area]
  float borderWidth = a_backdropExtra.x * u_pixelRatio;
  float cornerRadius = a_backdropExtra.y * u_pixelRatio;
  float labelPad = a_backdropExtra.z * u_pixelRatio;
  float backdropArea = a_backdropExtra.w;
  // Use 2x shadowBlur so the Gaussian fully decays before the quad edge
  float totalExpansion = shadowBlur * 2.0 + borderWidth;
  float enlargedRadius = nodeRadiusPixels + padding;

  // Circumscribed radius for the quad bounds. Non-circular shapes reach past
  // their inradius out to their circumradius (= enlargedRadius / inradiusFactor),
  // in any direction once rotated. The axis-aligned quad must contain that, or
  // the fill/shadow gets clipped (square corners, triangle tip, etc.).
  `).concat(s,`
  float boundRadius = enlargedRadius / inradiusFactor;

  // Apply zoom-dependent label size scaling
  float zoomScale = u_zoomLabelSizeRatio;
  float labelW = a_labelWidth * zoomScale * u_pixelRatio;
  float labelH = a_labelHeight * zoomScale * u_pixelRatio;
  float labelMargin = u_labelMargin * zoomScale * u_pixelRatio;

  // Only apply labelPad when a label is actually present
  float effectiveLabelPad = labelW > 0.0 ? labelPad : 0.0;
  vec2 labelHalfSize = vec2(labelW * 0.5 + effectiveLabelPad, labelH * 0.5 + effectiveLabelPad);
  vec2 labelOffset = vec2(0.0);

  // Effective label angle: intrinsic angle plus the camera angle when the label
  // is graph-aligned, so the box orbits the node in lockstep with the frame-pass.
  float labelAngle = a_labelAngle - labelRotation * u_cameraAngle;
  float la_c = cos(labelAngle);
  float la_s = sin(labelAngle);
  mat2 labelRotMat = mat2(la_c, -la_s, la_s, la_c);

  vec3 nodeClip = u_matrix * vec3(nodePosition, 1.0);
  vec2 snapDelta = vec2(0.0);

  if (labelW > 0.0) {
    // labelW > 0.0 means this node's label is displayed, so the frame-pass wrote
    // its edge distance this frame.
    float edgeDistPixels = nodeRadiusPixels * readFrameTexel(u_nodeFrameTexture, u_nodeFrameTextureWidth, nodeIdx).r;
    // labelMargin matches the label shader's margin (gap from node edge to text)
    float labelStart = edgeDistPixels + labelMargin;
    // Above/below center on the actual glyph height, not the font line box, so
    // the box stays aligned with the rendered text (matches labelBoxCenter()).
    float textHalf = a_textHeight * zoomScale * u_pixelRatio * 0.5;

    // Snap node center to pixel grid so label/backdrop/attachment move as a unit
    vec2 nodeScreen = vec2(
      (nodeClip.x + 1.0) * u_resolution.x,
      (1.0 - nodeClip.y) * u_resolution.y
    ) * 0.5;
    snapDelta = (round(nodeScreen) - nodeScreen) * u_labelPixelSnapping;

    if (a_positionMode < 0.5) {
      // Right: box spans from node center to text end + padding
      float boxRightEdge = labelStart + labelW + labelPad;
      labelOffset = vec2(boxRightEdge * 0.5, 0.0);
      labelHalfSize.x = boxRightEdge * 0.5;
    } else if (a_positionMode < 1.5) {
      // Left: mirror of right
      float boxLeftEdge = labelStart + labelW + labelPad;
      labelOffset = vec2(-boxLeftEdge * 0.5, 0.0);
      labelHalfSize.x = boxLeftEdge * 0.5;
    } else if (a_positionMode < 2.5) {
      // Above: text bottom at labelStart, centered horizontally
      labelOffset = vec2(0.0, -(labelStart + textHalf));
    } else if (a_positionMode < 3.5) {
      // Below: text top at labelStart, centered horizontally
      labelOffset = vec2(0.0, labelStart + textHalf);
    }
    // over (>=4): labelOffset stays (0,0) \u2014 text centered on the node.

    // The attachment-cover shift is in label space (like the attachment itself),
    // so rotate it together with the position offset \u2014 otherwise the box drifts
    // off the attachment as the label angle grows.
    labelOffset = labelRotMat * (labelOffset + a_labelBoxOffset * zoomScale * u_pixelRatio);
  }

  // For node-only mode, zero out label dimensions
  if (backdropArea > 0.5 && backdropArea < 1.5) {
    labelHalfSize = vec2(0.0);
    labelOffset = vec2(0.0);
  }

  vec2 minBound, maxBound;

  bool hasLabelBounds = labelW > 0.0 && (backdropArea > 1.5 || backdropArea < 0.5);

  if (hasLabelBounds) {
    // Union with label bounds (area=both) or label-only bounds (area=label)
    vec2 labelMin, labelMax;

    if (a_labelAngle != 0.0) {
      vec2 corner1 = labelOffset + labelRotMat * vec2(-labelHalfSize.x, -labelHalfSize.y);
      vec2 corner2 = labelOffset + labelRotMat * vec2(labelHalfSize.x, -labelHalfSize.y);
      vec2 corner3 = labelOffset + labelRotMat * vec2(labelHalfSize.x, labelHalfSize.y);
      vec2 corner4 = labelOffset + labelRotMat * vec2(-labelHalfSize.x, labelHalfSize.y);
      labelMin = min(min(corner1, corner2), min(corner3, corner4));
      labelMax = max(max(corner1, corner2), max(corner3, corner4));
    } else {
      labelMin = labelOffset - labelHalfSize;
      labelMax = labelOffset + labelHalfSize;
    }

    if (backdropArea > 1.5) {
      // Label-only: bounds from label rect only
      minBound = labelMin - totalExpansion;
      maxBound = labelMax + totalExpansion;
    } else {
      // Both: union of node + label
      minBound = min(-vec2(boundRadius), labelMin) - totalExpansion;
      maxBound = max(vec2(boundRadius), labelMax) + totalExpansion;
    }
  } else {
    // Node-only or no visible label
    float totalRadius = boundRadius + totalExpansion;
    minBound = -vec2(totalRadius);
    maxBound = vec2(totalRadius);
  }

  vec2 quadSize = maxBound - minBound;
  vec2 quadCenter = (minBound + maxBound) * 0.5;

  vec2 localPos = quadCenter + a_quadCorner * quadSize * 0.5 + snapDelta;
  vec2 ndcOffset = localPos * 2.0 / u_resolution;
  ndcOffset.y = -ndcOffset.y;

  gl_Position = vec4(nodeClip.xy + ndcOffset, 0.0, 1.0);

  v_uv = localPos;
  v_nodeCenter = vec2(0.0);
  v_nodeRadius = nodeRadiusPixels;
  v_labelCenter = labelOffset;
  v_labelHalfSize = labelHalfSize;
  v_aaWidth = 1.0;
  v_shapeId = shapeId;
  v_labelAngle = labelAngle;
  v_backdropColor = a_backdropColor;
  v_backdropShadowColor = a_backdropShadowColor;
  v_backdropShadowBlur = a_backdropShadowBlur;
  v_backdropPadding = a_backdropPadding;
  v_backdropBorderColor = a_backdropBorderColor;
  v_backdropBorderWidth = borderWidth;
  v_backdropCornerRadius = cornerRadius;
  v_backdropArea = backdropArea;
}
`);return l}function Jd(a){var n=a.shapes,e=a.layers,t=a.shapeGlobalIds,r=pr(n),i=Rn(n).map(function(c){return"uniform ".concat(c.type," ").concat(c.name,";")}).join(`
`),o=function(f){return Ea(f,"nodeUV","1.0")},s;if(n.length===1)s="float nodeSdfNormalized = ".concat(o(n[0]),";");else{var l=n.map(function(c,f){var g=t?t[f]:f;return"    case ".concat(g,": nodeSdfNormalized = ").concat(o(c),"; break;")}).join(`
`),u=o(n[0]);s=`float nodeSdfNormalized;
  int shapeId = int(v_shapeId);
  switch (shapeId) {
`.concat(l,`
    default: nodeSdfNormalized = `).concat(u,`;
  }`)}var d=`float effectiveRadius = max(enlargedRadius - cornerRadius, 0.01);
  float ca = u_cameraAngle * v_nodeRotation;
  float ca_c = cos(ca);
  float ca_s = sin(ca);
  vec2 rotatedScreenUV = mat2(ca_c, -ca_s, ca_s, ca_c) * screenUV;
  vec2 nodeUV = vec2(rotatedScreenUV.x, -rotatedScreenUV.y) / effectiveRadius;`,h=`#version 300 es
precision highp float;

in vec2 v_uv;
in vec2 v_nodeCenter;
in float v_nodeRadius;
in vec2 v_labelCenter;
in vec2 v_labelHalfSize;
in float v_aaWidth;
in float v_shapeId;
in float v_nodeRotation;
in float v_labelAngle;
in vec4 v_backdropColor;
in vec4 v_backdropShadowColor;
in float v_backdropShadowBlur;
in float v_backdropPadding;
in vec4 v_backdropBorderColor;
in float v_backdropBorderWidth;
in float v_backdropCornerRadius;
in float v_backdropArea;
`.concat(jo(n,e,"in"),`

uniform float u_cameraAngle;
`).concat(i,`

layout(location = 0) out vec4 fragColor;
layout(location = 1) out vec4 fragPicking;

`).concat(r,`
`).concat(Id,`
`).concat(Gd,`
`).concat(zd,`
`).concat(Nd,`

void main() {
  vec4 backdropColor = v_backdropColor;
  vec4 shadowColor = v_backdropShadowColor;
  float shadowBlur = v_backdropShadowBlur;
  float padding = v_backdropPadding;
  vec4 borderColor = v_backdropBorderColor;
  float borderWidth = v_backdropBorderWidth;
  float cornerRadius = v_backdropCornerRadius;

  float enlargedRadius = v_nodeRadius + padding;
  vec2 screenUV = v_uv - v_nodeCenter;
  `).concat(d,`

  // Query the correct shape SDF based on shapeId
  `).concat(s,`
  float nodeSdfPixels = nodeSdfNormalized * effectiveRadius - cornerRadius;

  // Label SDF with optional corner radius and rotation
  float labelSdfPixels;
  if (v_labelHalfSize.x > 0.0) {
    vec2 labelP = v_uv - v_labelCenter;
    labelSdfPixels = sdfRoundedRotatedBox(labelP, v_labelHalfSize, v_labelAngle, cornerRadius);
  } else {
    labelSdfPixels = 10000.0;
  }

  // Select area: 0=both, 1=node, 2=label
  float combinedSdf;
  if (v_backdropArea > 1.5) {
    combinedSdf = labelSdfPixels;
  } else if (v_backdropArea > 0.5) {
    combinedSdf = nodeSdfPixels;
  } else {
    combinedSdf = min(nodeSdfPixels, labelSdfPixels);
  }

  // Fill + border composite
  float outerEdge = smoothstep(v_aaWidth, -v_aaWidth, combinedSdf);
  vec4 background;
  if (borderWidth > 0.5) {
    float innerEdge = smoothstep(v_aaWidth, -v_aaWidth, combinedSdf + borderWidth);
    float fillAlpha = innerEdge * backdropColor.a;
    vec4 fill = vec4(backdropColor.rgb * fillAlpha, fillAlpha);
    float borderAlpha = (outerEdge - innerEdge) * borderColor.a;
    vec4 border = vec4(borderColor.rgb * borderAlpha, borderAlpha);
    background = fill + border * (1.0 - fill.a);
  } else {
    float fillAlpha = outerEdge * backdropColor.a;
    background = vec4(backdropColor.rgb * fillAlpha, fillAlpha);
  }

  // Gaussian-like shadow falloff (mimics canvas shadowBlur)
  vec4 shadow = vec4(0.0);
  float sigma = shadowBlur / 2.5;
  if (sigma > 0.001) {
    float shadowDist = max(0.0, combinedSdf);
    float shadowAlpha = exp(-(shadowDist * shadowDist) / (2.0 * sigma * sigma)) * shadowColor.a;
    shadow = vec4(shadowColor.rgb * shadowAlpha, shadowAlpha);
  }

  fragColor = background + shadow * (1.0 - background.a);
  fragPicking = vec4(0.0);
}
`);return h}function eh(a){var n=["u_matrix","u_sizeRatio","u_correctionRatio","u_cameraAngle","u_resolution","u_pixelRatio","u_labelMargin","u_zoomLabelSizeRatio","u_labelPixelSnapping","u_nodeDataTexture","u_nodeDataTextureWidth","u_nodeFrameTexture","u_nodeFrameTextureWidth","u_layerAttributeTexture","u_layerAttributeTextureWidth","u_layerAttributeTexelsPerNode"],e=O(Rn(a)),t;try{for(e.s();!(t=e.n()).done;){var r=t.value;n.includes(r.name)||n.push(r.name)}}catch(i){e.e(i)}finally{e.f()}return n}function th(a){return{vertexShader:Qd(a),fragmentShader:Jd(a),uniforms:eh(a.shapes)}}function nh(a,n,e,t){var r,i,o=t.label,s=o===void 0?{}:o,l=t.shapes,u=t.layers,d=t.getAttributeTexture,h=t.shapeGlobalIds;if(l.length===0)throw new Error("createBackdropProgram: at least one shape must be provided in 'shapes'");var c=(r=s.margin)!==null&&r!==void 0?r:5,f=(i=s.zoomToLabelSizeRatioFunction)!==null&&i!==void 0?i:function(){return 1},g={shapes:l,layers:u,shapeGlobalIds:h},y=th(g),m=(function(v){function p(){var b;te(this,p);for(var T=arguments.length,_=new Array(T),E=0;E<T;E++)_[E]=arguments[E];return b=me(this,p,[].concat(_)),D(b,"totalBackdropCount",0),D(b,"bufferCapacity",0),b}return ye(p,v),ne(p,[{key:"getDefinition",value:function(){var T=WebGL2RenderingContext,_=T.FLOAT,E=T.TRIANGLE_STRIP;return{VERTICES:4,VERTEX_SHADER_SOURCE:y.vertexShader,FRAGMENT_SHADER_SOURCE:y.fragmentShader,METHOD:E,UNIFORMS:y.uniforms,ATTRIBUTES:[{name:"a_nodeIndex",size:1,type:_},{name:"a_labelWidth",size:1,type:_},{name:"a_labelHeight",size:1,type:_},{name:"a_textHeight",size:1,type:_},{name:"a_positionMode",size:1,type:_},{name:"a_labelAngle",size:1,type:_},{name:"a_backdropColor",size:4,type:_},{name:"a_backdropShadowColor",size:4,type:_},{name:"a_backdropShadowBlur",size:1,type:_},{name:"a_backdropPadding",size:1,type:_},{name:"a_backdropBorderColor",size:4,type:_},{name:"a_backdropExtra",size:4,type:_},{name:"a_labelBoxOffset",size:2,type:_}],CONSTANT_ATTRIBUTES:[{name:"a_quadCorner",size:2,type:_}],CONSTANT_DATA:[[-1,-1],[1,-1],[-1,1],[1,1]]}}},{key:"processBackdrop",value:function(T,_){var E=this.floats,A=this.STRIDE,w=T*A;E[w++]=_.nodeIndex,E[w++]=_.labelWidth,E[w++]=_.labelHeight,E[w++]=_.textHeight,E[w++]=nn[_.position],E[w++]=_.labelAngle,E[w++]=_.backdropColor[0],E[w++]=_.backdropColor[1],E[w++]=_.backdropColor[2],E[w++]=_.backdropColor[3],E[w++]=_.backdropShadowColor[0],E[w++]=_.backdropShadowColor[1],E[w++]=_.backdropShadowColor[2],E[w++]=_.backdropShadowColor[3],E[w++]=_.backdropShadowBlur,E[w++]=_.backdropPadding,E[w++]=_.backdropBorderColor[0],E[w++]=_.backdropBorderColor[1],E[w++]=_.backdropBorderColor[2],E[w++]=_.backdropBorderColor[3],E[w++]=_.backdropBorderWidth,E[w++]=_.backdropCornerRadius,E[w++]=_.backdropLabelPadding,E[w++]=_.backdropArea,E[w++]=_.labelBoxOffset[0],E[w++]=_.labelBoxOffset[1]}},{key:"setUniforms",value:function(T,_){var E=_.gl,A=_.uniformLocations;E.uniformMatrix3fv(A.u_matrix,!1,T.matrix),E.uniform1f(A.u_sizeRatio,T.sizeRatio),E.uniform1f(A.u_correctionRatio,T.correctionRatio),E.uniform1f(A.u_cameraAngle,T.cameraAngle),E.uniform2f(A.u_resolution,T.width*T.pixelRatio,T.height*T.pixelRatio),E.uniform1f(A.u_pixelRatio,T.pixelRatio),E.uniform1f(A.u_labelMargin,p.labelMargin),E.uniform1f(A.u_zoomLabelSizeRatio,1/f(T.zoomRatio)),E.uniform1f(A.u_labelPixelSnapping,T.labelPixelSnapping),E.uniform1i(A.u_nodeDataTexture,T.nodeDataTextureUnit),E.uniform1i(A.u_nodeDataTextureWidth,T.nodeDataTextureWidth),E.uniform1i(A.u_nodeFrameTexture,T.nodeFrameTextureUnit),E.uniform1i(A.u_nodeFrameTextureWidth,T.nodeFrameTextureWidth);var w=d();A.u_layerAttributeTexture&&w&&(w.bind(pt),E.uniform1i(A.u_layerAttributeTexture,pt),E.uniform1i(A.u_layerAttributeTextureWidth,w.getTextureWidth()),E.uniform1i(A.u_layerAttributeTexelsPerNode,w.getTexelsPerItem()));var S=O(Rn(l)),C;try{for(S.s();!(C=S.n()).done;){var G=C.value;this.setTypedUniform(G,_)}}catch(L){S.e(L)}finally{S.f()}}},{key:"hasNothingToRender",value:function(){return this.totalBackdropCount===0}},{key:"drawWebGL",value:function(T,_){var E=_.gl;this.totalBackdropCount!==0&&(this.isInstanced?E.drawArraysInstanced(T,0,this.VERTICES,this.totalBackdropCount):E.drawArrays(T,0,this.totalBackdropCount*this.VERTICES))}},{key:"reallocate",value:function(T){this.totalBackdropCount=T,T>this.bufferCapacity&&(this.bufferCapacity=Math.max(T,Math.ceil(this.bufferCapacity*1.5)||10),Ee(p,"reallocate",this,3)([this.bufferCapacity]))}}])})(Lt);return D(m,"labelMargin",c),new m(a,n,e)}var Xo=(function(a){function n(){var e;te(this,n);for(var t=arguments.length,r=new Array(t),i=0;i<t;i++)r[i]=arguments[i];return e=me(this,n,[].concat(r)),D(e,"totalCharacterCount",0),D(e,"bufferCapacity",0),e}return ye(n,a),ne(n,[{key:"processLabel",value:function(t,r,i){if(i.hidden||!i.text)return 0;for(var o=i.text,s=o.length,l=0;l<s;l++){var u=o[l];this.processCharacter(r+l,i,u,l)}return s}},{key:"hasNothingToRender",value:function(){return this.totalCharacterCount===0}},{key:"drawWebGL",value:function(t,r){var i=r.gl;this.totalCharacterCount!==0&&(this.isInstanced?i.drawArraysInstanced(t,0,this.VERTICES,this.totalCharacterCount):i.drawArrays(t,0,this.totalCharacterCount*this.VERTICES))}},{key:"reallocate",value:function(t){this.totalCharacterCount=t,t>this.bufferCapacity&&(this.bufferCapacity=Math.max(t,Math.ceil(this.bufferCapacity*1.5)||1e3),Ee(n,"reallocate",this,3)([this.bufferCapacity]))}}])})(Lt);function ah(){var a=`#version 300 es

in float a_nodeIndex;
in vec4 a_id;
in vec4 a_color;
in float a_labelWidth;
in float a_labelHeight;
in float a_textHeight;
in float a_positionMode;
in float a_labelAngle;
in float a_padding;
in vec2 a_quadCorner;

uniform mat3 u_matrix;
uniform float u_sizeRatio;
uniform float u_correctionRatio;
uniform float u_cameraAngle;
uniform vec2 u_resolution;
uniform float u_pixelRatio;
uniform float u_labelMargin;
uniform float u_zoomLabelSizeRatio;
uniform float u_labelPixelSnapping;
uniform float u_pickingPadding;
uniform sampler2D u_nodeDataTexture;
uniform int u_nodeDataTextureWidth;
uniform sampler2D u_nodeFrameTexture;
uniform int u_nodeFrameTextureWidth;

out vec4 v_id;
out vec4 v_color;

`.concat(lt,`
`).concat(Ct,`
`).concat(rn,`
`).concat($o,`

void main() {
  int nodeIdx = int(a_nodeIndex);

  // Node data: (x, y, size, shapeId).
  vec4 nodeData = readNodeData(u_nodeDataTexture, u_nodeDataTextureWidth, nodeIdx);
  vec2 nodePosition = nodeData.xy;
  float nodeSize = nodeData.z;

  // Shape-aware edge distance, read once from the shared frame texture.
  float edgeDist = readFrameTexel(u_nodeFrameTexture, u_nodeFrameTextureWidth, nodeIdx).r;

  // Per-node label rotation alignment: 0 = viewport, 1 = label turns with camera.
  float labelRotation = readNodeFlags(u_nodeDataTexture, u_nodeDataTextureWidth, nodeIdx).g;

  `).concat(Bo,`

  float zoomScale = u_zoomLabelSizeRatio;
  float labelW = a_labelWidth * zoomScale * u_pixelRatio;
  float labelH = a_labelHeight * zoomScale * u_pixelRatio;
  float labelMargin = u_labelMargin * zoomScale * u_pixelRatio;
#ifdef PICKING_MODE
  float padding = u_pickingPadding * u_pixelRatio;
#else
  float padding = a_padding * u_pixelRatio;
#endif

  if (labelW <= 0.0) {
    gl_Position = vec4(2.0, 0.0, 0.0, 1.0);
    v_id = vec4(0.0);
    v_color = vec4(0.0);
    return;
  }

  vec2 labelHalfSize = vec2(labelW * 0.5 + padding, labelH * 0.5 + padding);
  vec2 labelOffset = vec2(0.0);

  // Graph-aligned labels add the camera angle so the rect orbits with the text.
  float labelAngle = a_labelAngle - labelRotation * u_cameraAngle;
  float la_c = cos(labelAngle);
  float la_s = sin(labelAngle);
  mat2 labelRotMat = mat2(la_c, -la_s, la_s, la_c);

  vec3 nodeClip = u_matrix * vec3(nodePosition, 1.0);
  vec2 nodeScreen = vec2(
    (nodeClip.x + 1.0) * u_resolution.x,
    (1.0 - nodeClip.y) * u_resolution.y
  ) * 0.5;
  vec2 snapDelta = (round(nodeScreen) - nodeScreen) * u_labelPixelSnapping;

  if (a_positionMode < 4.0) {
    float labelStart = nodeRadiusPixels * edgeDist + labelMargin;
    float textHalf = a_textHeight * zoomScale * u_pixelRatio * 0.5;
    // Box center uses the text half-size; the padding expands the quad below.
    labelOffset = labelRotMat * labelBoxCenter(a_positionMode, labelStart, vec2(labelW * 0.5, labelH * 0.5), textHalf);
  }

  // Rotate the rect with the label so it stays aligned with the (rotated) text.
  vec2 localPos = labelOffset + labelRotMat * (a_quadCorner * labelHalfSize);
  vec2 ndcOffset = (localPos + snapDelta) * 2.0 / u_resolution;
  ndcOffset.y = -ndcOffset.y;

  gl_Position = vec4(nodeClip.xy + ndcOffset, 0.0, 1.0);
  v_id = a_id;
  v_color = a_color;
}
`);return a}var rh=`#version 300 es
precision highp float;

in vec4 v_id;
in vec4 v_color;

out vec4 fragColor;

void main() {
  #ifdef PICKING_MODE
    fragColor = v_id;
  #else
    if (v_color.a <= 0.0) discard;
    // v_color is non-premultiplied RGBA (0-1); convert to premultiplied for blending
    fragColor = vec4(v_color.rgb * v_color.a, v_color.a);
  #endif
}
`;function ih(a,n,e,t){var r,i,o=t.label,s=o===void 0?{}:o,l=(r=s.margin)!==null&&r!==void 0?r:an,u=(i=s.zoomToLabelSizeRatioFunction)!==null&&i!==void 0?i:function(){return 1},d=ah(),h=(function(c){function f(){var g;te(this,f);for(var y=arguments.length,m=new Array(y),v=0;v<y;v++)m[v]=arguments[v];return g=me(this,f,[].concat(m)),D(g,"totalCount",0),D(g,"bufferCapacity",0),g}return ye(f,c),ne(f,[{key:"getDefinition",value:function(){var y=WebGL2RenderingContext,m=y.FLOAT,v=y.UNSIGNED_BYTE,p=y.TRIANGLE_STRIP;return{VERTICES:4,VERTEX_SHADER_SOURCE:d,FRAGMENT_SHADER_SOURCE:rh,METHOD:p,UNIFORMS:["u_matrix","u_sizeRatio","u_correctionRatio","u_cameraAngle","u_resolution","u_pixelRatio","u_labelMargin","u_zoomLabelSizeRatio","u_labelPixelSnapping","u_pickingPadding","u_nodeDataTexture","u_nodeDataTextureWidth","u_nodeFrameTexture","u_nodeFrameTextureWidth"],ATTRIBUTES:[{name:"a_nodeIndex",size:1,type:m},{name:"a_id",size:4,type:v,normalized:!0},{name:"a_color",size:4,type:v,normalized:!0},{name:"a_labelWidth",size:1,type:m},{name:"a_labelHeight",size:1,type:m},{name:"a_textHeight",size:1,type:m},{name:"a_positionMode",size:1,type:m},{name:"a_labelAngle",size:1,type:m},{name:"a_padding",size:1,type:m}],CONSTANT_ATTRIBUTES:[{name:"a_quadCorner",size:2,type:m}],CONSTANT_DATA:[[-1,-1],[1,-1],[-1,1],[1,1]]}}},{key:"processLabelBackground",value:function(y,m){var v=this.floats,p=this.ints,b=y*this.STRIDE;v[b++]=m.nodeIndex,p[b++]=m.id,v[b++]=m.color,v[b++]=m.labelWidth,v[b++]=m.labelHeight,v[b++]=m.textHeight,v[b++]=m.positionMode,v[b++]=m.labelAngle,v[b++]=m.padding}},{key:"setUniforms",value:function(y,m){var v=m.gl,p=m.uniformLocations;v.uniformMatrix3fv(p.u_matrix,!1,y.matrix),v.uniform1f(p.u_sizeRatio,y.sizeRatio),v.uniform1f(p.u_correctionRatio,y.correctionRatio),v.uniform1f(p.u_cameraAngle,y.cameraAngle),v.uniform2f(p.u_resolution,y.width*y.pixelRatio,y.height*y.pixelRatio),v.uniform1f(p.u_pixelRatio,y.pixelRatio),v.uniform1f(p.u_labelMargin,f.labelMargin),v.uniform1f(p.u_zoomLabelSizeRatio,1/u(y.zoomRatio)),v.uniform1f(p.u_labelPixelSnapping,y.labelPixelSnapping),v.uniform1f(p.u_pickingPadding,y.labelPickingPadding),v.uniform1i(p.u_nodeDataTexture,y.nodeDataTextureUnit),v.uniform1i(p.u_nodeDataTextureWidth,y.nodeDataTextureWidth),v.uniform1i(p.u_nodeFrameTexture,y.nodeFrameTextureUnit),v.uniform1i(p.u_nodeFrameTextureWidth,y.nodeFrameTextureWidth)}},{key:"hasNothingToRender",value:function(){return this.totalCount===0}},{key:"drawWebGL",value:function(y,m){var v=m.gl;this.totalCount!==0&&v.drawArraysInstanced(v.TRIANGLE_STRIP,0,this.VERTICES,this.totalCount)}},{key:"reallocate",value:function(y){this.totalCount=y,y>this.bufferCapacity&&(this.bufferCapacity=Math.max(y,Math.ceil(this.bufferCapacity*1.5)||10),Ee(f,"reallocate",this,3)([this.bufferCapacity]))}}])})(Lt);return D(h,"labelMargin",l),new h(a,n,e)}var Je={fontSize:64,buffer:8,radius:24,cutoff:.25,maxTextureSize:2048,debounceTimeout:100},En=2,wn=1e20;function oh(a,n,e,t,r){var i=a+r*4,o=document.createElement("canvas");o.width=i,o.height=i;var s=o.getContext("2d",{willReadFrequently:!0});return s.font="".concat(t," ").concat(e," ").concat(a,"px ").concat(n),s.textBaseline="alphabetic",s.textAlign="left",s.fillStyle="black",{ctx:s,canvasSize:i,gridOuter:new Float64Array(i*i),gridInner:new Float64Array(i*i),f:new Float64Array(i),z:new Float64Array(i+1),v:new Uint16Array(i)}}function sh(a,n,e,t,r){var i=a.ctx,o=a.canvasSize,s=i.measureText(n),l=s.width,u=s.actualBoundingBoxAscent,d=s.actualBoundingBoxDescent,h=s.actualBoundingBoxLeft,c=s.actualBoundingBoxRight,f=Math.ceil(u),g=Math.ceil(h),y=Math.max(0,Math.min(o-e,Math.ceil(h)+Math.ceil(c))),m=Math.min(o-e,f+Math.ceil(d)),v=y+2*e,p=m+2*e,b=Math.max(v*p,0),T=new Uint8ClampedArray(b),_={data:T,width:v,height:p,glyphWidth:y,glyphHeight:m,glyphTop:f,glyphLeft:g,glyphAdvance:l};if(y===0||m===0)return _;var E=a.gridInner,A=a.gridOuter;i.clearRect(e,e,y,m),i.fillText(n,e+g,e+f);var w=i.getImageData(e,e,y,m);A.fill(wn,0,b),E.fill(0,0,b);for(var S=0;S<m;S++)for(var C=0;C<y;C++){var G=w.data[4*(S*y+C)+3]/255;if(G!==0){var L=(S+e)*v+C+e;if(G===1)A[L]=0,E[L]=wn;else{var N=.5-G;A[L]=N>0?N*N:0,E[L]=N<0?N*N:0}}}ko(A,0,0,v,p,v,a.f,a.v,a.z),ko(E,e,e,y,m,v,a.f,a.v,a.z);for(var k=0;k<b;k++){var I=Math.sqrt(A[k])-Math.sqrt(E[k]);T[k]=Math.round(255-255*(I/t+r))}return _}function ko(a,n,e,t,r,i,o,s,l){for(var u=n;u<n+t;u++)Po(a,e*i+u,i,r,o,s,l);for(var d=e;d<e+r;d++)Po(a,d*i+n,1,t,o,s,l)}function Po(a,n,e,t,r,i,o){i[0]=0,o[0]=-wn,o[1]=wn,r[0]=a[n];for(var s=1,l=0,u=0;s<t;s++){r[s]=a[n+s*e];var d=s*s;do{var h=i[l];u=(r[s]-r[h]+d-h*h)/(s-h)/2}while(u<=o[l]&&--l>-1);l++,i[l]=s,o[l]=u,o[l+1]=wn}for(var c=0,f=0;c<t;c++){for(;o[f+1]<c;)f++;var g=i[f],y=c-g;a[n+c*e]=r[g]+y*y}}var Rt=(function(a){function n(){var e,t=arguments.length>0&&arguments[0]!==void 0?arguments[0]:{};return te(this,n),e=me(this,n),D(e,"fonts",new Map),D(e,"textures",[]),D(e,"cursor",{x:0,y:0,rowHeight:0,atlasIndex:0}),D(e,"pendingGlyphs",[]),D(e,"debounceTimer",null),e.options=H(H({},Je),t),e.canvas=document.createElement("canvas"),e.canvas.width=e.options.maxTextureSize,e.canvas.height=e.options.maxTextureSize,e.ctx=e.canvas.getContext("2d",{willReadFrequently:!0}),e.measureCanvas=document.createElement("canvas"),e.measureCtx=e.measureCanvas.getContext("2d"),e.textures.push(e.ctx.getImageData(0,0,1,1)),e}return ye(n,a),ne(n,[{key:"getFontKey",value:function(t){return"".concat(t.family,"-").concat(t.weight,"-").concat(t.style)}},{key:"registerFont",value:function(t){var r=this.getFontKey(t);if(this.fonts.has(r))return r;var i=oh(this.options.fontSize,t.family,t.weight,t.style,this.options.buffer);return this.fonts.set(r,{descriptor:t,generator:i,glyphs:new Map}),r}},{key:"ensureGlyphs",value:function(t,r){var i=this.fonts.get(r);if(!i)throw new Error('Font "'.concat(r,'" is not registered. Call registerFont() first.'));var o=!1,s=O(t),l;try{for(s.s();!(l=s.n()).done;){var u=l.value,d=u.codePointAt(0);d!==void 0&&(i.glyphs.has(d)||(this.pendingGlyphs.push({fontKey:r,charCode:d}),o=!0))}}catch(h){s.e(h)}finally{s.f()}o&&this.scheduleTextureGeneration()}},{key:"measureText",value:function(t,r){var i=this.fonts.get(r);if(!i)throw new Error('Font "'.concat(r,'" is not registered.'));var o=i.descriptor,s=o.family,l=o.weight,u=o.style;return this.measureCtx.font="".concat(u," ").concat(l," ").concat(this.options.fontSize,"px ").concat(s),this.measureCtx.measureText(t).width}},{key:"getGlyph",value:function(t,r){var i=this.fonts.get(r);if(i)return i.glyphs.get(t)}},{key:"getTextures",value:function(){return this.textures}},{key:"getFontCount",value:function(){return this.fonts.size}},{key:"getGlyphCount",value:function(){var t=0,r=O(this.fonts.values()),i;try{for(r.s();!(i=r.n()).done;){var o=i.value;t+=o.glyphs.size}}catch(s){r.e(s)}finally{r.f()}return t}},{key:"hasPendingGlyphs",value:function(){return this.pendingGlyphs.length>0}},{key:"flush",value:function(){this.debounceTimer&&(clearTimeout(this.debounceTimer),this.debounceTimer=null),this.generateTextures()}},{key:"destroy",value:function(){this.debounceTimer&&clearTimeout(this.debounceTimer),this.fonts.clear(),this.textures=[],this.pendingGlyphs=[],this.removeAllListeners()}},{key:"scheduleTextureGeneration",value:function(){var t=this;this.debounceTimer===null&&(this.options.debounceTimeout===null?this.generateTextures():this.debounceTimer=setTimeout(function(){t.debounceTimer=null,t.generateTextures()},this.options.debounceTimeout))}},{key:"generateTextures",value:function(){if(this.pendingGlyphs.length!==0){var t=this.options,r=t.maxTextureSize,i=t.buffer,o=t.radius,s=t.cutoff,l=O(this.pendingGlyphs),u;try{for(l.s();!(u=l.n()).done;){var d=u.value,h=d.fontKey,c=d.charCode,f=this.fonts.get(h);if(!(!f||f.glyphs.has(c))){var g=String.fromCodePoint(c),y=sh(f.generator,g,i,o,s),m=y.width,v=y.height;this.cursor.x+m+En>r&&(this.cursor.x=0,this.cursor.y+=this.cursor.rowHeight+En,this.cursor.rowHeight=0),this.cursor.y+v+En>r&&(this.finalizeCurrentTexture(),this.cursor={x:0,y:0,rowHeight:0,atlasIndex:this.cursor.atlasIndex+1},this.ctx.clearRect(0,0,r,r));for(var p=y.data,b=new Uint8ClampedArray(m*v*4),T=0;T<p.length;T++){var _=T*4;b[_]=255,b[_+1]=255,b[_+2]=255,b[_+3]=p[T]}var E=new ImageData(b,m,v);this.ctx.putImageData(E,this.cursor.x,this.cursor.y);var A={charCode:c,width:y.glyphWidth,height:y.glyphHeight,bearingX:-y.glyphLeft-i,bearingY:y.glyphTop+i,advance:y.glyphAdvance,atlasX:this.cursor.x,atlasY:this.cursor.y,atlasWidth:m,atlasHeight:v,atlasIndex:this.cursor.atlasIndex};f.glyphs.set(c,A),this.cursor.x+=m+En,this.cursor.rowHeight=Math.max(this.cursor.rowHeight,v)}}}catch(w){l.e(w)}finally{l.f()}this.finalizeCurrentTexture(),this.pendingGlyphs=[],this.emit(n.ATLAS_UPDATED_EVENT,{textures:this.textures,glyphCount:this.getGlyphCount()})}}},{key:"finalizeCurrentTexture",value:function(){var t=this.options.maxTextureSize,r=this.cursor.y>0||this.cursor.rowHeight>0,i=Math.min(t,Math.max(this.cursor.x,r?t:1)),o=Math.min(t,this.cursor.y+this.cursor.rowHeight+En),s=this.ctx.getImageData(0,0,i,o);this.cursor.atlasIndex>=this.textures.length?this.textures.push(s):this.textures[this.cursor.atlasIndex]=s}}])})(No.EventEmitter);D(Rt,"ATLAS_UPDATED_EVENT","atlasUpdated");var lh=Je.fontSize;function uh(){var a=`  // -------------------------------------------------------------------------
  // Step 3: Calculate position offset from the shared edge distance
  // -------------------------------------------------------------------------
  vec2 positionOffset = vec2(0.0);

  if (a_positionMode < 4.0) {
    vec2 screenDir = getLabelDirection(a_positionMode);
    float boundaryDistPixels = nodeRadiusPixels * edgeDist;
    positionOffset = screenDir * (boundaryDistPixels + margin);
  }`,n=`#version 300 es

// ============================================================================
// Attributes
// ============================================================================

// Per-character (instanced)
in float a_nodeIndex;        // Index into node data texture
in vec2 a_charOffset;        // Character offset from label origin (pixels)
in vec2 a_charSize;          // Character dimensions (pixels)
in vec4 a_texCoords;         // Atlas coords: (x, y, width, height) in pixels
in vec4 a_color;             // Text color (RGBA)
in float a_margin;           // Gap between node edge and label (pixels)
in float a_positionMode;     // Position: 0=right, 1=left, 2=above, 3=below, 4=over
in float a_labelWidth;       // Total label width (pixels)
in float a_labelHeight;      // Label height (pixels)
in float a_verticalCenter;   // Vertical center offset from baseline (pixels)
in float a_textHeight;       // Actual text height: maxAscent + maxDescent (pixels)
in float a_labelAngle;       // Label rotation angle (radians)

// Per-vertex (constant quad corners)
in vec2 a_quadCorner;        // Quad corner: [-1,-1], [1,-1], [-1,1], [1,1]

// ============================================================================
// Uniforms
// ============================================================================

uniform mat3 u_matrix;
uniform float u_sizeRatio;
uniform float u_correctionRatio;
uniform float u_cameraAngle;
uniform vec2 u_resolution;
uniform vec2 u_atlasSize;
uniform sampler2D u_nodeDataTexture;
uniform int u_nodeDataTextureWidth;
uniform sampler2D u_nodeFrameTexture;
uniform int u_nodeFrameTextureWidth;
uniform float u_zoomLabelSizeRatio;
uniform float u_labelPixelSnapping;
uniform float u_pixelRatio;

// ============================================================================
// Varyings
// ============================================================================

out vec2 v_texCoord;
out vec4 v_color;
out float v_fontScale;

// ============================================================================
// Constants
// ============================================================================

const float bias = 255.0 / 254.0;
const float ATLAS_FONT_SIZE = `.concat(xe(lh),`;

// ============================================================================
// Helper Functions
// ============================================================================

`).concat(lt,`
`).concat(Ct,`
`).concat(rn,`
`).concat(Ho,`

// ============================================================================
// Main
// ============================================================================

void main() {
  // -------------------------------------------------------------------------
  // Step 0: Fetch node data + shared edge distance from textures
  // -------------------------------------------------------------------------
  // Node-data texture format: vec4(x, y, size, shapeId)
  // 2D texture layout: texCoord = (index % width, index / width)
  int nodeIdx = int(a_nodeIndex);
  vec4 nodeData = readNodeData(u_nodeDataTexture, u_nodeDataTextureWidth, nodeIdx);
  vec2 a_anchorPosition = nodeData.xy;
  float a_nodeSize = nodeData.z;

  // Normalized edge distance from the shared frame texture (the frame-pass ran
  // the SDF search once; the label just reads the result).
  float edgeDist = readFrameTexel(u_nodeFrameTexture, u_nodeFrameTextureWidth, nodeIdx).r;

  // Per-node label rotation alignment: 0 = viewport, 1 = label turns with camera.
  float labelRotation = readNodeFlags(u_nodeDataTexture, u_nodeDataTextureWidth, nodeIdx).g;

  // Apply zoom-dependent label size scaling
  // Positional values are in CSS pixels; multiply by u_pixelRatio to convert to
  // physical pixels, which is what the NDC conversion (/ u_resolution) expects.
  float zoomScale = u_zoomLabelSizeRatio;
  float margin = a_margin * zoomScale * u_pixelRatio;
  vec2 charOffset = a_charOffset * zoomScale * u_pixelRatio;
  vec2 charSize = a_charSize * zoomScale * u_pixelRatio;
  float labelWidth = a_labelWidth * zoomScale * u_pixelRatio;
  float labelHeight = a_labelHeight * zoomScale;

  // Font scale: ratio of CSS label size to the base atlas font size.
  // Divided by u_pixelRatio because the atlas is generated at ATLAS_FONT_SIZE * pixelRatio,
  // which cancels out the u_pixelRatio in the fragment shader's gamma formula and keeps
  // the anti-aliasing band width consistent across pixel densities.
  v_fontScale = a_labelHeight * zoomScale / (ATLAS_FONT_SIZE * u_pixelRatio);

  // -------------------------------------------------------------------------
  // Step 1: Transform node position to clip space
  // -------------------------------------------------------------------------
  vec3 anchorClip = u_matrix * vec3(a_anchorPosition, 1.0);

  // -------------------------------------------------------------------------
  // Step 2: Convert node size to screen pixels
  // -------------------------------------------------------------------------
  float matrixScaleX = length(vec2(u_matrix[0][0], u_matrix[1][0]));
  float nodeRadiusGraphSpace = a_nodeSize * u_correctionRatio / u_sizeRatio * 2.0;
  float nodeRadiusNDC = nodeRadiusGraphSpace * matrixScaleX;
  float nodeRadiusPixels = nodeRadiusNDC * u_resolution.x / 2.0;

`).concat(a,`

  // -------------------------------------------------------------------------
  // Step 4: Calculate final vertex position
  // -------------------------------------------------------------------------
  vec2 cornerOffset = (a_quadCorner + 1.0) * 0.5;
  vec2 charPixelPos = positionOffset + charOffset + cornerOffset * charSize;

  // Apply text alignment based on position mode
  float verticalCenter = a_verticalCenter * zoomScale * u_pixelRatio;
  float textHeight = a_textHeight * zoomScale * u_pixelRatio;
  float baselineToDescent = textHeight / 2.0 - verticalCenter;
  float baselineToAscent = textHeight / 2.0 + verticalCenter;

  if (a_positionMode < 0.5) {
    // Right: vertically center
    charPixelPos.y += verticalCenter;
  } else if (a_positionMode < 1.5) {
    // Left: right-align and vertically center
    charPixelPos.x -= labelWidth;
    charPixelPos.y += verticalCenter;
  } else if (a_positionMode < 2.5) {
    // Above: center horizontally, bottom of text at anchor
    charPixelPos.x -= labelWidth * 0.5;
    charPixelPos.y -= baselineToDescent;
  } else if (a_positionMode < 3.5) {
    // Below: center horizontally, top of text at anchor
    charPixelPos.x -= labelWidth * 0.5;
    charPixelPos.y += baselineToAscent;
  } else {
    // Over: center both
    charPixelPos.x -= labelWidth * 0.5;
    charPixelPos.y += verticalCenter;
  }

  // Apply label angle rotation. Graph-aligned labels add the camera angle so the
  // whole label orbits the node in lockstep with the frame-pass edge distance.
  float labelAngle = a_labelAngle - labelRotation * u_cameraAngle;
  float la_c = cos(labelAngle);
  float la_s = sin(labelAngle);
  mat2 labelRotMat = mat2(la_c, -la_s, la_s, la_c);
  charPixelPos = labelRotMat * charPixelPos;

  // Snap node center to pixel grid so label/backdrop/attachment move as a unit
  vec2 nodeScreen = vec2(
    (anchorClip.x + 1.0) * u_resolution.x,
    (1.0 - anchorClip.y) * u_resolution.y
  ) * 0.5;
  charPixelPos += (round(nodeScreen) - nodeScreen) * u_labelPixelSnapping;

  // Convert to NDC (flip Y: screen Y-down -> clip Y-up)
  vec2 ndcOffset = vec2(charPixelPos.x, -charPixelPos.y) * 2.0 / u_resolution;
  gl_Position = vec4(anchorClip.xy + ndcOffset, 0.0, 1.0);

  // -------------------------------------------------------------------------
  // Step 5: Texture coordinates
  // -------------------------------------------------------------------------
  v_texCoord = (a_texCoords.xy + cornerOffset * a_texCoords.zw) / u_atlasSize;

  // -------------------------------------------------------------------------
  // Step 6: Pass color
  // -------------------------------------------------------------------------
  v_color = a_color;
  v_color.a *= bias;
}
`);return n}function dh(){var a=`#version 300 es
precision highp float;

in vec2 v_texCoord;
in vec4 v_color;
in float v_fontScale;

uniform sampler2D u_atlas;
uniform float u_gamma;
uniform float u_sdfBuffer;
uniform float u_pixelRatio;

// Fragment output (single target - picking handled via separate pass)
out vec4 fragColor;

void main() {
  #ifdef PICKING_MODE
    // Labels are not pickable - discard all fragments in picking mode
    fragColor = vec4(0.0);
    discard;
  #else
    // Sample SDF value from atlas (high = inside glyph, low = outside)
    float sdfValue = texture(u_atlas, v_texCoord).a;

    // Edge threshold: 1.0 - cutoff = 0.75 for default cutoff=0.25
    // This is where the glyph edge is located in the SDF
    float edgeThreshold = 1.0 - u_sdfBuffer;

    // Gamma controls the anti-aliasing band width.
    // Scale inversely with font scale so small labels get a wider AA band
    // (smoother) and large labels get a tighter band (sharper).
    float gamma = u_gamma / (u_pixelRatio * v_fontScale);

    // Pure gamma-based anti-aliasing using smoothstep
    // The AA band extends from (threshold - gamma) to (threshold + gamma)
    float alpha = smoothstep(edgeThreshold - gamma, edgeThreshold + gamma, sdfValue);

    // Premultiplied alpha output for correct blending
    float finalAlpha = v_color.a * alpha;
    fragColor = vec4(v_color.rgb * finalAlpha, finalAlpha);
  #endif
}
`;return a}function hh(){return["u_matrix","u_sizeRatio","u_correctionRatio","u_cameraAngle","u_resolution","u_atlasSize","u_atlas","u_gamma","u_sdfBuffer","u_pixelRatio","u_nodeDataTexture","u_nodeDataTextureWidth","u_nodeFrameTexture","u_nodeFrameTextureWidth","u_zoomLabelSizeRatio","u_labelPixelSnapping"]}function ch(){return{vertexShader:uh(),fragmentShader:dh(),uniforms:hh()}}function fh(a,n,e,t){var r,i,o=t.label,s=o===void 0?{}:o,l=(r=s.margin)!==null&&r!==void 0?r:an,u=(i=s.zoomToLabelSizeRatioFunction)!==null&&i!==void 0?i:function(){return 1},d=ch(),h=(function(c){function f(g,y,m){var v,p,b,T;if(te(this,f),T=me(this,f,[g,y,m]),D(T,"atlasTexture",null),D(T,"atlasNeedsUpdate",!1),D(T,"labelGlyphCache",new Map),T.atlasFontSize=Je.fontSize*Tn(),T.atlasManager=new Rt({fontSize:T.atlasFontSize}),T.gamma=.025,T.sdfBuffer=Je.cutoff,T.atlasTexture=g.createTexture(),!T.atlasTexture)throw new Error("NodeLabelProgram: failed to create atlas texture");g.bindTexture(g.TEXTURE_2D,T.atlasTexture),g.texParameteri(g.TEXTURE_2D,g.TEXTURE_WRAP_S,g.CLAMP_TO_EDGE),g.texParameteri(g.TEXTURE_2D,g.TEXTURE_WRAP_T,g.CLAMP_TO_EDGE),g.texParameteri(g.TEXTURE_2D,g.TEXTURE_MIN_FILTER,g.LINEAR),g.texParameteri(g.TEXTURE_2D,g.TEXTURE_MAG_FILTER,g.LINEAR),g.bindTexture(g.TEXTURE_2D,null),T.atlasManager.on(Rt.ATLAS_UPDATED_EVENT,function(){T.atlasNeedsUpdate=!0});var _={family:((v=s.font)===null||v===void 0?void 0:v.family)||"sans-serif",weight:((p=s.font)===null||p===void 0?void 0:p.weight)||"normal",style:((b=s.font)===null||b===void 0?void 0:b.style)||"normal"};return T.defaultFontKey=T.atlasManager.registerFont(_),T}return ye(f,c),ne(f,[{key:"getDefinition",value:function(){var y=WebGL2RenderingContext,m=y.FLOAT,v=y.UNSIGNED_BYTE,p=y.TRIANGLE_STRIP;return{VERTICES:4,VERTEX_SHADER_SOURCE:d.vertexShader,FRAGMENT_SHADER_SOURCE:d.fragmentShader,METHOD:p,UNIFORMS:d.uniforms,ATTRIBUTES:[{name:"a_nodeIndex",size:1,type:m},{name:"a_charOffset",size:2,type:m},{name:"a_charSize",size:2,type:m},{name:"a_texCoords",size:4,type:m},{name:"a_color",size:4,type:v,normalized:!0},{name:"a_margin",size:1,type:m},{name:"a_positionMode",size:1,type:m},{name:"a_labelWidth",size:1,type:m},{name:"a_labelHeight",size:1,type:m},{name:"a_verticalCenter",size:1,type:m},{name:"a_textHeight",size:1,type:m},{name:"a_labelAngle",size:1,type:m}],CONSTANT_ATTRIBUTES:[{name:"a_quadCorner",size:2,type:m}],CONSTANT_DATA:[[-1,-1],[1,-1],[-1,1],[1,1]]}}},{key:"prepareLabelGlyphs",value:function(y,m){if(m.hidden||!m.text){this.labelGlyphCache.delete(y);return}var v=m.text,p=m.fontKey||this.defaultFontKey;this.atlasManager.ensureGlyphs(v,p);var b=[],T=[],_=0,E=0,A=0,w=O(v),S;try{for(w.s();!(S=w.n()).done;){var C=S.value,G=C.codePointAt(0);if(G===void 0){b.push(void 0),T.push(_);continue}var L=this.atlasManager.getGlyph(G,p);b.push(L),T.push(_),L&&(_+=L.advance,E=Math.max(E,L.bearingY),A=Math.max(A,L.atlasHeight-L.bearingY))}}catch(N){w.e(N)}finally{w.f()}this.labelGlyphCache.set(y,{glyphs:b,xOffsets:T,totalWidth:_,totalHeight:E+A,verticalCenterOffset:(E-A)/2})}},{key:"processCharacter",value:function(y,m,v,p){var b=this.floats,T=this.STRIDE,_=y*T,E=this.labelGlyphCache.get(m.parentKey);if(!E||!E.glyphs[p]){for(var A=0;A<T;A++)b[_+A]=0;return}var w=E.glyphs[p],S=E.xOffsets[p],C=m.size/this.atlasFontSize,G=Be(m.color),L=_;b[L++]=m.nodeIndex,b[L++]=(S+w.bearingX)*C,b[L++]=-w.bearingY*C,b[L++]=w.atlasWidth*C,b[L++]=w.atlasHeight*C,b[L++]=w.atlasX,b[L++]=w.atlasY,b[L++]=w.atlasWidth,b[L++]=w.atlasHeight,b[L++]=G,b[L++]=m.margin,b[L++]=nn[m.position],b[L++]=E.totalWidth*C,b[L++]=m.size,b[L++]=E.verticalCenterOffset*C,b[L++]=E.totalHeight*C,b[L++]=m.labelAngle}},{key:"processLabel",value:function(y,m,v){return this.prepareLabelGlyphs(y,v),Ee(f,"processLabel",this,3)([y,m,v])}},{key:"updateAtlasTexture",value:function(){if(this.atlasNeedsUpdate){var y=this.normalProgram.gl,m=this.atlasManager.getTextures();if(m.length!==0){var v=m[0];y.bindTexture(y.TEXTURE_2D,this.atlasTexture),y.texImage2D(y.TEXTURE_2D,0,y.RGBA,v.width,v.height,0,y.RGBA,y.UNSIGNED_BYTE,v.data),y.bindTexture(y.TEXTURE_2D,null),this.atlasNeedsUpdate=!1}}}},{key:"setUniforms",value:function(y,m){var v=m.gl,p=m.uniformLocations;v.uniformMatrix3fv(p.u_matrix,!1,y.matrix),v.uniform1f(p.u_sizeRatio,y.sizeRatio),v.uniform1f(p.u_correctionRatio,y.correctionRatio),v.uniform1f(p.u_cameraAngle,y.cameraAngle),v.uniform2f(p.u_resolution,y.width*y.pixelRatio,y.height*y.pixelRatio);var b=this.atlasManager.getTextures();b.length>0?v.uniform2f(p.u_atlasSize,b[0].width,b[0].height):v.uniform2f(p.u_atlasSize,1,1),v.activeTexture(v.TEXTURE0),v.bindTexture(v.TEXTURE_2D,this.atlasTexture),v.uniform1i(p.u_atlas,0),p.u_nodeDataTexture!==void 0&&v.uniform1i(p.u_nodeDataTexture,y.nodeDataTextureUnit),p.u_nodeDataTextureWidth!==void 0&&v.uniform1i(p.u_nodeDataTextureWidth,y.nodeDataTextureWidth),v.uniform1i(p.u_nodeFrameTexture,y.nodeFrameTextureUnit),v.uniform1i(p.u_nodeFrameTextureWidth,y.nodeFrameTextureWidth),v.uniform1f(p.u_gamma,this.gamma),v.uniform1f(p.u_sdfBuffer,this.sdfBuffer),v.uniform1f(p.u_pixelRatio,y.pixelRatio),v.uniform1f(p.u_zoomLabelSizeRatio,1/f.zoomToLabelSizeRatioFunction(y.zoomRatio)),v.uniform1f(p.u_labelPixelSnapping,y.labelPixelSnapping)}},{key:"renderProgram",value:function(y,m){this.updateAtlasTexture(),this.atlasManager.hasPendingGlyphs()&&(this.atlasManager.flush(),this.updateAtlasTexture()),Ee(f,"renderProgram",this,3)([y,m])}},{key:"registerFont",value:function(y){var m=arguments.length>1&&arguments[1]!==void 0?arguments[1]:"normal",v=arguments.length>2&&arguments[2]!==void 0?arguments[2]:"normal";return this.atlasManager.registerFont({family:y,weight:m,style:v})}},{key:"getAtlasManager",value:function(){return this.atlasManager}},{key:"measureLabel",value:function(y,m,v){var p=v||this.defaultFontKey;this.atlasManager.ensureGlyphs(y,p),this.atlasManager.hasPendingGlyphs()&&this.atlasManager.flush();var b=0,T=0,_=0,E=O(y),A;try{for(E.s();!(A=E.n()).done;){var w=A.value,S=w.codePointAt(0);if(S!==void 0){var C=this.atlasManager.getGlyph(S,p);C&&(b+=C.advance,T=Math.max(T,C.bearingY),_=Math.max(_,C.atlasHeight-C.bearingY))}}}catch(L){E.e(L)}finally{E.f()}var G=m/this.atlasFontSize;return{width:b*G,height:m,textHeight:(T+_)*G}}},{key:"ensureGlyphsReady",value:function(y,m){var v=m||this.defaultFontKey,p=O(y),b;try{for(p.s();!(b=p.n()).done;){var T=b.value;this.atlasManager.ensureGlyphs(T,v)}}catch(_){p.e(_)}finally{p.f()}this.atlasManager.flush()}},{key:"kill",value:function(){var y=this.normalProgram.gl;this.atlasTexture&&(y.deleteTexture(this.atlasTexture),this.atlasTexture=null),this.atlasManager.destroy(),this.labelGlyphCache.clear(),Ee(f,"kill",this,3)([])}}])})(Xo);return D(h,"labelMargin",l),D(h,"zoomToLabelSizeRatioFunction",u),new h(a,n,e)}var gh=`#version 300 es
precision highp float;

in float v_edgeDist;

// R32F target: only the .r channel is stored.
out vec4 fragColor;

void main() {
  fragColor = vec4(v_edgeDist, 0.0, 0.0, 0.0);
}
`;function vh(a,n,e){var t=pr(a),r=Rn(a).map(function(g){return"uniform ".concat(g.type," ").concat(g.name,";")}).join(`
`),i=Wd(a,e),o=i.code,s=i.multiShape,l=on(a,n),u=Object.keys(l.specs).map(function(g){return"float v_".concat(g,";")}).join(`
`),d=tn(l,{varPrefix:"nodeAttr",baseTexelExpr:"nodeIdx * u_layerAttributeTexelsPerNode",textureWidthUniform:"u_layerAttributeTextureWidth",textureSamplerUniform:"u_layerAttributeTexture"}),h=d.fetchCode,c=d.varyingAssignments,f=`#version 300 es
precision highp float;

uniform float u_cameraAngle;
uniform sampler2D u_nodeDataTexture;
uniform int u_nodeDataTextureWidth;
uniform float u_frameTextureWidth;
uniform float u_frameTextureHeight;
uniform sampler2D u_layerAttributeTexture;
uniform int u_layerAttributeTextureWidth;
uniform int u_layerAttributeTexelsPerNode;
`.concat(r,`

in float a_nodeIndex;     // node-data texture index (also the target frame texel)
in float a_positionMode;  // 0=right 1=left 2=above 3=below 4=over
in float a_labelAngle;    // intrinsic label angle (radians)

out float v_edgeDist;

// Shape attributes (plain globals: this pass is vertex-only)
`).concat(u,`

`).concat(lt,`
`).concat(Ct,`
`).concat(t,`
`).concat(o,`
`).concat(Ho,`

void main() {
  int nodeIdx = int(a_nodeIndex);
`).concat(h,`
`).concat(c,`
  `).concat(s?`// Multi-shape: the shape id lives in the node-data texture's .w channel:
  g_shapeId = int(readNodeData(u_nodeDataTexture, u_nodeDataTextureWidth, nodeIdx).w);`:"// Single-shape mode, shape id not needed",`

  // Per-node rotation alignment (0 = viewport, 1 = graph).
  vec4 nodeFlags = readNodeFlags(u_nodeDataTexture, u_nodeDataTextureWidth, nodeIdx);
  float nodeRotation = nodeFlags.r;
  float labelRotation = nodeFlags.g;

  // Effective angle: intrinsic (style-given) plus the camera angle when the label
  // is graph-aligned. The companions place the box at this same angle.
  float effectiveAngle = a_labelAngle - labelRotation * u_cameraAngle;

  // The "over" mode (4) sits on the node center, so it has no edge distance.
  float edgeDist = 0.0;
  if (a_positionMode < 4.0) {
    vec2 screenDir = getLabelDirection(a_positionMode);
    // Rotate by the effective label angle. Inlined rather than via rotate2D()
    // because the shape SDFs (getShapeGLSLForShapes) already define that helper
    // for multi-shape programs, and redefining it would be a GLSL error.
    float ea_c = cos(effectiveAngle);
    float ea_s = sin(effectiveAngle);
    vec2 rotatedScreenDir = mat2(ea_c, -ea_s, ea_s, ea_c) * screenDir;
    // Screen (Y-down) -> SDF (Y-up).
    vec2 sdfDir = vec2(rotatedScreenDir.x, -rotatedScreenDir.y);
    // Counter-rotate into the shape's local frame for graph-aligned nodes, so the
    // boundary is queried against the shape's actual on-screen orientation.
    float nodeCa = -u_cameraAngle * nodeRotation;
    float nc = cos(nodeCa), ns = sin(nodeCa);
    sdfDir = mat2(nc, -ns, ns, nc) * sdfDir;
    edgeDist = findEdgeDistance(sdfDir, 1.0);
  }
  v_edgeDist = edgeDist;

  // Scatter to this node's texel center in the frame texture.
  float x = mod(a_nodeIndex, u_frameTextureWidth);
  float y = floor(a_nodeIndex / u_frameTextureWidth);
  vec2 ndc = (vec2(x, y) + 0.5) / vec2(u_frameTextureWidth, u_frameTextureHeight) * 2.0 - 1.0;
  gl_Position = vec4(ndc, 0.0, 1.0);
  gl_PointSize = 1.0;
}
`);return f}var Yo=(function(){function a(n,e){te(this,a),D(this,"uniformLocations",{});var t=e.shapes,r=e.layers,i=e.shapeGlobalIds;if(t.length===0)throw new Error("NodeLabelFramePass: at least one shape must be provided");this.gl=n,this.shapeUniforms=Rn(t),this.hasAttributeData=Object.keys(on(t,r).offsets).length>0,this.vertexShader=fr(n,vh(t,r,i)),this.fragmentShader=gr(n,gh),this.program=vr(n,[this.vertexShader,this.fragmentShader]);var o=["u_cameraAngle","u_nodeDataTexture","u_nodeDataTextureWidth","u_frameTextureWidth","u_frameTextureHeight","u_layerAttributeTexture","u_layerAttributeTextureWidth","u_layerAttributeTexelsPerNode"].concat(Q(this.shapeUniforms.map(function(v){return v.name}))),s=O(o),l;try{for(s.s();!(l=s.n()).done;){var u=l.value;this.uniformLocations[u]=n.getUniformLocation(this.program,u)}}catch(v){s.e(v)}finally{s.f()}var d=a.FLOATS_PER_POINT*4;this.vao=n.createVertexArray(),this.buffer=n.createBuffer(),n.bindVertexArray(this.vao),n.bindBuffer(n.ARRAY_BUFFER,this.buffer);var h=O([["a_nodeIndex",0],["a_positionMode",4],["a_labelAngle",8]]),c;try{for(h.s();!(c=h.n()).done;){var f=ie(c.value,2),g=f[0],y=f[1],m=n.getAttribLocation(this.program,g);m>=0&&(n.enableVertexAttribArray(m),n.vertexAttribPointer(m,1,n.FLOAT,!1,d,y))}}catch(v){h.e(v)}finally{h.f()}n.bindVertexArray(null)}return ne(a,[{key:"run",value:function(e,t,r,i,o){if(t!==0){var s=this.gl;s.useProgram(this.program),s.bindVertexArray(this.vao),s.bindBuffer(s.ARRAY_BUFFER,this.buffer),s.bufferData(s.ARRAY_BUFFER,e.subarray(0,t*a.FLOATS_PER_POINT),s.DYNAMIC_DRAW);var l=this.uniformLocations;s.uniform1f(l.u_cameraAngle,i.cameraAngle),s.uniform1i(l.u_nodeDataTexture,i.nodeDataTextureUnit),s.uniform1i(l.u_nodeDataTextureWidth,i.nodeDataTextureWidth),s.uniform1f(l.u_frameTextureWidth,r.getTextureWidth()),s.uniform1f(l.u_frameTextureHeight,r.getTextureHeight()),this.hasAttributeData&&o&&(o.bind(pt),l.u_layerAttributeTexture&&s.uniform1i(l.u_layerAttributeTexture,pt),l.u_layerAttributeTextureWidth&&s.uniform1i(l.u_layerAttributeTextureWidth,o.getTextureWidth()),l.u_layerAttributeTexelsPerNode&&s.uniform1i(l.u_layerAttributeTexelsPerNode,o.getTexelsPerItem()));var u=O(this.shapeUniforms),d;try{for(u.s();!(d=u.n()).done;){var h=d.value;br(s,this.uniformLocations[h.name],h)}}catch(c){u.e(c)}finally{u.f()}r.bindAsRenderTarget(),s.disable(s.BLEND),s.disable(s.DEPTH_TEST),s.drawArrays(s.POINTS,0,t),s.bindFramebuffer(s.FRAMEBUFFER,null),s.bindVertexArray(null)}}},{key:"kill",value:function(){var e=this.gl;e.deleteProgram(this.program),e.deleteShader(this.vertexShader),e.deleteShader(this.fragmentShader),e.deleteBuffer(this.buffer),e.deleteVertexArray(this.vao)}}])})();D(Yo,"FLOATS_PER_POINT",3);function Ko(a,n,e,t,r){var i,o=t.label,s=o===void 0?{}:o,l=t.shapes;if(l.length===0)throw new Error("createNodeProgram: at least one shape must be provided in 'shapes'");var u={},d=[],h;l.forEach(function(A,w){var S=Cd(A);w===0&&(h=S),u[A.name]=w,d[w]=Dn(S)});var c=Q(t.layers),f=Lo({shapes:l,layers:c,shapeGlobalIds:l.length>1?d:void 0,antialias:r}),g=fh(a,null,e,{label:s}),y=nh(a,null,e,{shapes:l,layers:c,getAttributeTexture:function(){return E.getAttributeTexture()},label:s,shapeGlobalIds:l.length>1?d:void 0}),m=ih(a,n,e,{label:s}),v=t.labelAttachments&&Object.keys(t.labelAttachments).length>0?jd(a,null,e,{label:s}):null,p=new Yo(a,{shapes:l,layers:c,shapeGlobalIds:l.length>1?d:void 0}),b=Ra(l,c),T=$e(b),_=(i=(function(A){function w(S,C,G){var L;te(this,w),L=me(this,w,[S,C,G]),D(L,"layerLifecycles",new Map),D(L,"layersNeedingRegeneration",new Set),D(L,"attrDescriptors",[]),L._pickingBuffer=C;var N=_.layerTextures.get(S);N||(N=new wa(S,T),_.layerTextures.set(S,N)),L.layerAttributeTexture=N;var k=_.textureRefCounts.get(S)||0;_.textureRefCounts.set(S,k+1),L.packedAttributeData=new Float32Array(T.floatsPerItem),c.forEach(function(W,F){if(W.lifecycle){var x={gl:S,renderer:{refresh:function(){return G.refresh()}},getUniformLocation:function(z){return S.getUniformLocation(L.normalProgram.program,z)},requestShaderRegeneration:function(){L.layersNeedingRegeneration.add(F)},requestRefresh:function(){G.refresh()}},P=W.lifecycle(x);L.layerLifecycles.set(F,P)}}),L.layerLifecycles.forEach(function(W){var F;(F=W.init)===null||F===void 0||F.call(W)});var I=new Map;return L.layerLifecycles.forEach(function(W,F){W.getAttributeData&&I.set(F,W)}),L.attrDescriptors=Aa(b,T,I),L}return ye(w,A),ne(w,[{key:"getDefinition",value:function(){var C=WebGL2RenderingContext,G=C.FLOAT,L=C.TRIANGLE_STRIP;return{VERTICES:4,VERTEX_SHADER_SOURCE:f.vertexShader,FRAGMENT_SHADER_SOURCE:f.fragmentShader,METHOD:L,UNIFORMS:f.uniforms,ATTRIBUTES:f.attributes,CONSTANT_ATTRIBUTES:[{name:"a_quadCorner",size:2,type:G}],CONSTANT_DATA:[[-1,-1],[1,-1],[-1,1],[1,1]]}}},{key:"maybeRegenerateShaders",value:function(){var C=this;if(this.layersNeedingRegeneration.size!==0){c=c.map(function(F,x){if(C.layersNeedingRegeneration.has(x)){var P=C.layerLifecycles.get(x);if(P!=null&&P.regenerate){var U=P.regenerate();return H(H({},U),{},{lifecycle:F.lifecycle})}}return F}),this.layersNeedingRegeneration.clear(),f=Lo({shapes:l,layers:c,shapeGlobalIds:l.length>1?d:void 0,antialias:this.renderer.getSetting("antialiasNodes")});var G=this.normalProgram.gl,L=this.normalProgram,N=L.program,k=L.buffer,I=L.vertexShader,W=L.fragmentShader;G.deleteProgram(N),G.deleteBuffer(k),G.deleteShader(I),G.deleteShader(W),this.normalProgram=this.getProgramInfo("normal",G,f.vertexShader,f.fragmentShader,this._pickingBuffer)}}},{key:"allocateNode",value:function(C){this.layerAttributeTexture.allocate(C)}},{key:"freeNode",value:function(C){this.layerAttributeTexture.free(C)}},{key:"getAttributeTexture",value:function(){return this.layerAttributeTexture}},{key:"uploadLayerTexture",value:function(){this.layerAttributeTexture.upload()}},{key:"process",value:function(C,G,L,N,k){var I=G*this.STRIDE;if(L.visibility==="hidden"){for(var W=I+this.STRIDE;I<W;I++)this.floats[I]=0;this.floats[G*this.STRIDE]=Vo;return}this.processVisibleItem(Kt(C),I,L,N,k)}},{key:"processVisibleItem",value:function(C,G,L,N,k){var I,W=this.floats,F=this.ints;if(W[G++]=N,F[G++]=C,W[G++]=(I=L.opacity)!==null&&I!==void 0?I:1,T.floatsPerItem!==0){var x=this.packedAttributeData;Da(this.attrDescriptors,L,x,L.color,this.layerLifecycles,0),this.layerAttributeTexture.updateAllAttributes(k,x)}}},{key:"setUniforms",value:function(C,G){var L=this,N=G.gl,k=G.uniformLocations;k.u_matrix&&N.uniformMatrix3fv(k.u_matrix,!1,C.matrix),k.u_sizeRatio&&N.uniform1f(k.u_sizeRatio,C.sizeRatio),k.u_correctionRatio&&N.uniform1f(k.u_correctionRatio,C.correctionRatio),k.u_pickingPadding&&N.uniform1f(k.u_pickingPadding,C.nodePickingPadding),k.u_cameraAngle&&N.uniform1f(k.u_cameraAngle,C.cameraAngle),k.u_nodeDataTexture&&N.uniform1i(k.u_nodeDataTexture,C.nodeDataTextureUnit),k.u_nodeDataTextureWidth&&N.uniform1i(k.u_nodeDataTextureWidth,C.nodeDataTextureWidth),k.u_layerAttributeTexture&&(this.layerAttributeTexture.bind(pt),N.uniform1i(k.u_layerAttributeTexture,pt)),k.u_layerAttributeTextureWidth&&N.uniform1i(k.u_layerAttributeTextureWidth,this.layerAttributeTexture.getTextureWidth()),k.u_layerAttributeTexelsPerNode&&N.uniform1i(k.u_layerAttributeTexelsPerNode,this.layerAttributeTexture.getTexelsPerItem()),l.forEach(function(I){I.uniforms.forEach(function(W){L.setTypedUniform(W,G)})}),c.forEach(function(I){I.uniforms.forEach(function(W){L.setTypedUniform(W,G)})})}},{key:"render",value:function(C,G,L){this.maybeRegenerateShaders(),Ee(w,"render",this,3)([C,G,L])}},{key:"renderProgram",value:function(C,G){var L=G.gl,N=G.program;L.useProgram(N),G===this.normalProgram&&this.layerLifecycles.forEach(function(k){var I;(I=k.beforeRender)===null||I===void 0||I.call(k)}),Ee(w,"renderProgram",this,3)([C,G])}},{key:"kill",value:function(){this.layerLifecycles.forEach(function(L){var N;(N=L.kill)===null||N===void 0||N.call(L)}),this.layerLifecycles.clear();var C=this.normalProgram.gl,G=(_.textureRefCounts.get(C)||1)-1;G<=0?(this.layerAttributeTexture.kill(),_.layerTextures.delete(C),_.textureRefCounts.delete(C)):_.textureRefCounts.set(C,G),Ee(w,"kill",this,3)([])}}])})(Lt),D(i,"layerTextures",new WeakMap),D(i,"textureRefCounts",new WeakMap),i),E=new _(a,null,e);return{nodeProgram:E,labelProgram:g,backdropProgram:y,labelBackgroundProgram:m,attachmentProgram:v,framePass:p,shapeSlug:h,shapeNameToIndex:l.length>1?u:void 0,shapeGlobalIds:l.length>1?d:void 0}}var mt=6;function Ln(a){var n=a.offsets,e=a.specs,t=a.floatsPerItem,r=Object.keys(n);if(r.length===0||t===0)return{uniformDeclarations:"",uniformNames:[],vertexVaryingDeclarations:"",fragmentVaryingDeclarations:"",fetchCode:"",varyingAssignments:""};var i=`
uniform sampler2D u_edgeAttributeTexture;
uniform int u_edgeAttributeTextureWidth;
uniform int u_edgeAttributeTexelsPerEdge;`,o=["u_edgeAttributeTexture","u_edgeAttributeTextureWidth","u_edgeAttributeTexelsPerEdge"],s=r.map(function(f){var g=e[f].size===1?"float":"vec".concat(e[f].size);return"".concat(g," v_").concat(f,";")}),l=s.map(function(f){return"out ".concat(f)}).join(`
`),u=s.map(function(f){return"in ".concat(f)}).join(`
`),d=tn(a,{varPrefix:"attr",baseTexelExpr:"edgeIdx * u_edgeAttributeTexelsPerEdge",textureWidthUniform:"u_edgeAttributeTextureWidth",textureSamplerUniform:"u_edgeAttributeTexture"}),h=d.fetchCode,c=d.varyingAssignments;return{uniformDeclarations:i,uniformNames:o,vertexVaryingDeclarations:l,fragmentVaryingDeclarations:u,fetchCode:h,varyingAssignments:c}}function ph(a){return`
float findSourceClampT_`.concat(a,`(vec2 source, float sourceSize, int sourceShapeId, float sourceRotateAlign, vec2 target, float margin) {
  float lo = 0.0, hi = 0.5;
  float nodeExtent = sourceSize * u_correctionRatio / u_sizeRatio * 2.0;
  float effectiveSize = 1.0 - u_correctionRatio / nodeExtent;

  // Counter-rotate the query point so viewport-aligned nodes (rotateAlign=0) are
  // clamped against their on-screen orientation; graph-aligned nodes skip it.
  float ca = u_cameraAngle * (1.0 - sourceRotateAlign);
  float rc = cos(ca), rs = sin(ca);
  mat2 rot = mat2(rc, -rs, rs, rc);

  for (int i = 0; i < 12; i++) {
    float mid = (lo + hi) * 0.5;
    vec2 pos = path_`).concat(a,`_position(mid, source, target);
    vec2 localPos = rot * ((pos - source) / nodeExtent);
    float sdf = querySDF(sourceShapeId, localPos, effectiveSize);
    if (sdf < 0.0) lo = mid;
    else hi = mid;
  }

  float pathLen = path_`).concat(a,`_length(source, target);
  float marginT = (margin * u_correctionRatio / u_sizeRatio) / pathLen;
  return (lo + hi) * 0.5 + marginT;
}
`)}function mh(a){return`
float findTargetClampT_`.concat(a,`(vec2 source, vec2 target, float targetSize, int targetShapeId, float targetRotateAlign, float margin) {
  float lo = 0.5, hi = 1.0;
  float nodeExtent = targetSize * u_correctionRatio / u_sizeRatio * 2.0;
  float effectiveSize = 1.0 - u_correctionRatio / nodeExtent;

  // See findSourceClampT_ for the rotation rationale.
  float ca = u_cameraAngle * (1.0 - targetRotateAlign);
  float rc = cos(ca), rs = sin(ca);
  mat2 rot = mat2(rc, -rs, rs, rc);

  for (int i = 0; i < 12; i++) {
    float mid = (lo + hi) * 0.5;
    vec2 pos = path_`).concat(a,`_position(mid, source, target);
    vec2 localPos = rot * ((pos - target) / nodeExtent);
    float sdf = querySDF(targetShapeId, localPos, effectiveSize);
    if (sdf < 0.0) hi = mid;
    else lo = mid;
  }

  float pathLen = path_`).concat(a,`_length(source, target);
  float marginT = (margin * u_correctionRatio / u_sizeRatio) / pathLen;
  return (lo + hi) * 0.5 - marginT;
}
`)}function Zo(a){return`
// Auto-generated numerical tangent (from position via finite differences)
vec2 path_`.concat(a,`_tangent(float t, vec2 source, vec2 target) {
  float epsilon = 0.001;
  float t1 = max(0.0, t - epsilon);
  float t2 = min(1.0, t + epsilon);
  vec2 p1 = path_`).concat(a,`_position(t1, source, target);
  vec2 p2 = path_`).concat(a,`_position(t2, source, target);
  return normalize(p2 - p1);
}

// Auto-generated normal (perpendicular to tangent)
vec2 path_`).concat(a,`_normal(float t, vec2 source, vec2 target) {
  vec2 tangent = path_`).concat(a,`_tangent(t, source, target);
  return vec2(-tangent.y, tangent.x);
}
`)}function yh(a){return`
// Auto-generated path length (samples position 16 times)
float path_`.concat(a,`_length(vec2 source, vec2 target) {
  float len = 0.0;
  vec2 prev = path_`).concat(a,`_position(0.0, source, target);
  for (int i = 1; i <= 16; i++) {
    float t = float(i) / 16.0;
    vec2 curr = path_`).concat(a,`_position(t, source, target);
    len += length(curr - prev);
    prev = curr;
  }
  return len;
}
`)}function bh(a){return`
// Auto-generated closest_t (coarse sample + ternary search)
float path_`.concat(a,`_closest_t(vec2 p, vec2 source, vec2 target) {
  // Coarse search: find best among 10 samples
  float bestT = 0.0;
  float bestDist = 1e10;
  for (int i = 0; i <= 10; i++) {
    float t = float(i) / 10.0;
    vec2 pos = path_`).concat(a,`_position(t, source, target);
    float d = length(p - pos);
    if (d < bestDist) {
      bestDist = d;
      bestT = t;
    }
  }

  // Refine with ternary search
  float lo = max(0.0, bestT - 0.1);
  float hi = min(1.0, bestT + 0.1);
  for (int i = 0; i < 10; i++) {
    float mid1 = lo + (hi - lo) / 3.0;
    float mid2 = hi - (hi - lo) / 3.0;
    float d1 = length(p - path_`).concat(a,`_position(mid1, source, target));
    float d2 = length(p - path_`).concat(a,`_position(mid2, source, target));
    if (d1 < d2) {
      hi = mid2;
    } else {
      lo = mid1;
    }
  }
  return (lo + hi) * 0.5;
}
`)}function _h(a){return`
// Auto-generated signed distance (via closest_t + normal)
float path_`.concat(a,`_distance(vec2 p, vec2 source, vec2 target) {
  float closestT = path_`).concat(a,`_closest_t(p, source, target);
  vec2 closest = path_`).concat(a,`_position(closestT, source, target);
  vec2 diff = p - closest;
  float dist = length(diff);
  if (dist < 0.0001) return 0.0;

  // Get normal at closest point
  vec2 normal = path_`).concat(a,`_normal(closestT, source, target);
  return dist * sign(dot(diff, normal));
}
`)}function xh(a){return`
// Auto-generated t_at_distance (binary search)
float path_`.concat(a,`_t_at_distance(float targetDist, vec2 source, vec2 target) {
  if (targetDist <= 0.0) return 0.0;

  float totalLen = path_`).concat(a,`_length(source, target);
  if (targetDist >= totalLen) return 1.0;

  // Binary search for t
  float lo = 0.0, hi = 1.0;
  for (int i = 0; i < 12; i++) {
    float mid = (lo + hi) * 0.5;

    // Compute arc length from 0 to mid
    float arcLen = 0.0;
    vec2 prev = path_`).concat(a,`_position(0.0, source, target);
    for (int j = 1; j <= 8; j++) {
      float t = mid * float(j) / 8.0;
      vec2 curr = path_`).concat(a,`_position(t, source, target);
      arcLen += length(curr - prev);
      prev = curr;
    }

    if (arcLen < targetDist) {
      lo = mid;
    } else {
      hi = mid;
    }
  }
  return (lo + hi) * 0.5;
}
`)}function ba(a,n){var e=new RegExp("\\b(float|vec[234]|void|int|bool)\\s+".concat(n,"\\s*\\("));return e.test(a)}function Qo(a,n){var e=[];return ba(n,"path_".concat(a,"_length"))||e.push(yh(a)),ba(n,"path_".concat(a,"_closest_t"))||e.push(bh(a)),ba(n,"path_".concat(a,"_distance"))||e.push(_h(a)),ba(n,"path_".concat(a,"_t_at_distance"))||e.push(xh(a)),e.length>0?`
// ============================================================================
// Auto-generated fallback functions (path only provided position)
// ============================================================================
`.concat(e.join(`
`)):""}function Jo(a){var n,e,t,r=a.paths,i=a.layers,o=(n=a.extremities)!==null&&n!==void 0?n:[];if(r.length===0)throw new Error("At least one path is required in 'paths'");if(i.length===0)throw new Error("At least one layer is required in 'layers'");var s=(e=a.defaultHead)!==null&&e!==void 0?e:"none",l=(t=a.defaultTail)!==null&&t!==void 0?t:"none";return{paths:r,extremities:o,layers:i,path:r[0],layer:i[0],defaultHead:s,defaultTail:l}}var es=WebGL2RenderingContext,An=es.FLOAT,Fo=es.UNSIGNED_BYTE;function Th(a,n,e){var t=new Set(["u_matrix","u_sizeRatio","u_correctionRatio","u_zoomRatio","u_pixelRatio","u_cameraAngle","u_minEdgeThickness","u_pickingPadding","u_nodeDataTexture","u_nodeDataTextureWidth","u_edgeDataTexture","u_edgeDataTextureWidth","u_edgeFrameTexture","u_edgeFrameTextureWidth","u_edgeAttributeTexture","u_edgeAttributeTextureWidth","u_edgeAttributeTexelsPerEdge"]),r=new Set(t);return a.forEach(function(i){return i.uniforms.forEach(function(o){return r.add(o.name)})}),n.forEach(function(i){return i.uniforms.forEach(function(o){return r.add(o.name)})}),e.forEach(function(i){return i.uniforms.forEach(function(o){return r.add(o.name)})}),Array.from(r)}function _r(a){var n=new Set,e=[],t=O(a),r;try{for(t.s();!(r=t.n()).done;){var i=r.value;n.has(i.name)||(n.add(i.name),e.push("// Path: ".concat(i.name)),e.push(i.glsl),e.push(Zo(i.name)),e.push(Qo(i.name,i.glsl)))}}catch(o){t.e(o)}finally{t.f()}return e.join(`

`)}function Eh(a){var n=[],e=O(a),t;try{for(e.s();!(t=e.n()).done;){var r=t.value;n.push("// Extremity: ".concat(r.name)),n.push(r.glsl)}}catch(i){e.e(i)}finally{e.f()}return n.join(`

`)}var Sh=[{queryName:"queryPathPosition",pathFunc:"position",returnType:"vec2",params:"float t, vec2 source, vec2 target",args:"t, source, target"},{queryName:"queryPathTangent",pathFunc:"tangent",returnType:"vec2",params:"float t, vec2 source, vec2 target",args:"t, source, target"},{queryName:"queryPathNormal",pathFunc:"normal",returnType:"vec2",params:"float t, vec2 source, vec2 target",args:"t, source, target"},{queryName:"queryPathLength",pathFunc:"length",returnType:"float",params:"vec2 source, vec2 target",args:"source, target"},{queryName:"queryPathClosestT",pathFunc:"closest_t",returnType:"float",params:"vec2 p, vec2 source, vec2 target",args:"p, source, target"}];function wh(a,n){var e=n.queryName,t=n.pathFunc,r=n.returnType,i=n.params,o=n.args;if(a.length===1)return"".concat(r," ").concat(e,"(int pathId, ").concat(i,`) {
  return path_`).concat(a[0].name,"_").concat(t,"(").concat(o,`);
}`);var s=a.map(function(l,u){return"    case ".concat(u,": return path_").concat(l.name,"_").concat(t,"(").concat(o,");")}).join(`
`);return"".concat(r," ").concat(e,"(int pathId, ").concat(i,`) {
  switch (pathId) {
`).concat(s,`
    default: return path_`).concat(a[0].name,"_").concat(t,"(").concat(o,`);
  }
}`)}function xr(a){return Sh.map(function(n){return wh(a,n)}).join(`

`)}function Ah(a){if(a.length===1)return`float queryExtremitySDF(int extremityId, vec2 uv, float lengthRatio, float widthRatio) {
  return extremity_`.concat(a[0].name,`(uv, lengthRatio, widthRatio);
}`);var n=a.map(function(e,t){return"    case ".concat(t,": return extremity_").concat(e.name,"(uv, lengthRatio, widthRatio);")}).join(`
`);return`float queryExtremitySDF(int extremityId, vec2 uv, float lengthRatio, float widthRatio) {
  switch (extremityId) {
`.concat(n,`
    default: return extremity_`).concat(a[0].name,`(uv, lengthRatio, widthRatio);
  }
}`)}function Dh(a){var n=[],e=O(a),t;try{for(e.s();!(t=e.n()).done;){var r=t.value;n.push(ph(r.name)),n.push(mh(r.name))}}catch(s){e.e(s)}finally{e.f()}if(a.length===1)n.push(`
float queryFindSourceClampT(int pathId, vec2 source, float sourceSize, int sourceShapeId, float sourceRotateAlign, vec2 target, float margin) {
  return findSourceClampT_`.concat(a[0].name,`(source, sourceSize, sourceShapeId, sourceRotateAlign, target, margin);
}

float queryFindTargetClampT(int pathId, vec2 source, vec2 target, float targetSize, int targetShapeId, float targetRotateAlign, float margin) {
  return findTargetClampT_`).concat(a[0].name,`(source, target, targetSize, targetShapeId, targetRotateAlign, margin);
}`));else{var i=a.map(function(s,l){return"    case ".concat(l,": return findSourceClampT_").concat(s.name,"(source, sourceSize, sourceShapeId, sourceRotateAlign, target, margin);")}).join(`
`),o=a.map(function(s,l){return"    case ".concat(l,": return findTargetClampT_").concat(s.name,"(source, target, targetSize, targetShapeId, targetRotateAlign, margin);")}).join(`
`);n.push(`
float queryFindSourceClampT(int pathId, vec2 source, float sourceSize, int sourceShapeId, float sourceRotateAlign, vec2 target, float margin) {
  switch (pathId) {
`.concat(i,`
    default: return findSourceClampT_`).concat(a[0].name,`(source, sourceSize, sourceShapeId, sourceRotateAlign, target, margin);
  }
}

float queryFindTargetClampT(int pathId, vec2 source, vec2 target, float targetSize, int targetShapeId, float targetRotateAlign, float margin) {
  switch (pathId) {
`).concat(o,`
    default: return findTargetClampT_`).concat(a[0].name,`(source, target, targetSize, targetShapeId, targetRotateAlign, margin);
  }
}`))}return n.join(`

`)}function Rh(a,n,e,t,r){var i=$e([].concat(Q(a),Q(e))),o=Ln(i),s=on(t,r),l=Object.keys(s.offsets),u=function(A){var w=s.specs[A].size;return w===1?"float":"vec".concat(w)},d=l.map(function(E){return"".concat(u(E)," v_source_").concat(E,`;
`).concat(u(E)," v_target_").concat(E,";")}).join(`
`),h=tn(s,{varPrefix:"srcNodeAttr",baseTexelExpr:"srcIdx * u_layerAttributeTexelsPerNode",textureWidthUniform:"u_layerAttributeTextureWidth",textureSamplerUniform:"u_layerAttributeTexture",outputPrefix:"v_source_"}),c=tn(s,{varPrefix:"tgtNodeAttr",baseTexelExpr:"tgtIdx * u_layerAttributeTexelsPerNode",textureWidthUniform:"u_layerAttributeTextureWidth",textureSamplerUniform:"u_layerAttributeTexture",outputPrefix:"v_target_"}),f=l.map(function(E){return"".concat(u(E)," g_").concat(E,";")}).join(`
`),g=l.map(function(E){return"  g_".concat(E," = v_source_").concat(E,";")}).join(`
`),y=l.map(function(E){return"  g_".concat(E," = v_target_").concat(E,";")}).join(`
`),m=new Set,v=[],p=function(A){m.has(A.name)||(m.add(A.name),v.push("uniform ".concat(A.type," ").concat(A.name,";")))};a.forEach(function(E){return E.uniforms.forEach(p)}),n.forEach(function(E){return E.uniforms.forEach(p)});var b=n.map(function(E){return xe(E.widthFactor)}).join(", "),T=Math.max.apply(Math,Q(a.map(function(E){return E.minBodyLengthRatio||0}))),_=`#version 300 es

// Node and edge data textures
uniform sampler2D u_nodeDataTexture;
uniform int u_nodeDataTextureWidth;
uniform sampler2D u_edgeDataTexture;
uniform int u_edgeDataTextureWidth;

// Edge attribute texture (for path-specific attributes like curvature)
`.concat(o.uniformDeclarations,`

// Node attribute texture (for node shape attributes)
uniform sampler2D u_layerAttributeTexture;
uniform int u_layerAttributeTextureWidth;
uniform int u_layerAttributeTexelsPerNode;

// Render params needed for clamping
uniform float u_sizeRatio;
uniform float u_correctionRatio;
uniform float u_cameraAngle;
uniform float u_minEdgeThickness;

// Edge-frame texture dimensions, for scattering each point to its texel
uniform float u_frameTextureWidth;
uniform float u_frameTextureHeight;

// Custom path/extremity uniforms
`).concat(v.join(`
`),`

// Path attribute varyings \u2014 assigned so path functions can read them as globals
`).concat(o.vertexVaryingDeclarations,`

// Node size varyings \u2014 read by path functions like loop
out float v_sourceNodeSize;
out float v_targetNodeSize;

// Node shape attributes per endpoint, and the ones querySDF reads
`).concat(d,`
`).concat(f,`

// Scattered output written to the edge-frame texel: [tStart, tEnd, straightenFactor, pathLength]
out vec4 v_clamp;

// Extremity width factor array (needed for extremityScale computation)
const float EXTREMITY_WIDTH_FACTORS[`).concat(n.length,"] = float[](").concat(b,`);

// Node-data fetch helpers (geometry texel + rotation-flags texel)
`).concat(lt,`
`).concat(Ct,`

// Shape SDFs for node boundary clamping
`).concat(Ld(),`
`).concat(kd(new Set(l)),`

// Path functions
`).concat(_r(a),`
`).concat(xr(a),`
`).concat(Dh(a),`

void main() {
  // One point per edge-data row; the row index is the edge-frame texel target.
  int edgeIdx = gl_VertexID;
  int texel0Idx = edgeIdx * 2;
  int texel1Idx = edgeIdx * 2 + 1;
  ivec2 edgeTexCoord0 = ivec2(texel0Idx % u_edgeDataTextureWidth, texel0Idx / u_edgeDataTextureWidth);
  ivec2 edgeTexCoord1 = ivec2(texel1Idx % u_edgeDataTextureWidth, texel1Idx / u_edgeDataTextureWidth);
  vec4 edgeData0 = texelFetch(u_edgeDataTexture, edgeTexCoord0, 0);
  vec4 edgeData1 = texelFetch(u_edgeDataTexture, edgeTexCoord1, 0);

  int srcIdx = int(edgeData0.x);
  int tgtIdx = int(edgeData0.y);
  float a_thickness = edgeData0.z;
  float a_headLengthRatio = edgeData1.x;
  float a_tailLengthRatio = edgeData1.y;
  int pathId = int(edgeData1.z);
  int extremityPacked = int(edgeData1.w);
  int headId = extremityPacked >> 4;
  int tailId = extremityPacked & 15;

  // Fetch path/layer attributes and assign to path-function globals
`).concat(o.fetchCode,`
`).concat(o.varyingAssignments,`

  // Fetch node shape attributes for both endpoints
`).concat(h.fetchCode,`
`).concat(h.varyingAssignments,`
`).concat(c.fetchCode,`
`).concat(c.varyingAssignments,`

  // Fetch node geometry (texel 0) and rotation flags (texel 1).
  vec4 srcNodeData = readNodeData(u_nodeDataTexture, u_nodeDataTextureWidth, srcIdx);
  vec4 tgtNodeData = readNodeData(u_nodeDataTexture, u_nodeDataTextureWidth, tgtIdx);

  vec2 a_source = srcNodeData.xy;
  vec2 a_target = tgtNodeData.xy;
  float a_sourceSize = srcNodeData.z;
  float a_targetSize = tgtNodeData.z;
  float a_sourceShapeId = srcNodeData.w;
  float a_targetShapeId = tgtNodeData.w;
  // Per-node rotation alignment (0 = viewport, 1 = graph), for boundary clamping.
  float a_sourceRotateAlign = readNodeFlags(u_nodeDataTexture, u_nodeDataTextureWidth, srcIdx).r;
  float a_targetRotateAlign = readNodeFlags(u_nodeDataTexture, u_nodeDataTextureWidth, tgtIdx).r;

  v_sourceNodeSize = a_sourceSize;
  v_targetNodeSize = a_targetSize;

  float headLengthRatio = a_headLengthRatio;
  float tailLengthRatio = a_tailLengthRatio;
  float headWidthFactor = EXTREMITY_WIDTH_FACTORS[headId];
  float tailWidthFactor = EXTREMITY_WIDTH_FACTORS[tailId];
  float minBodyLengthRatio = `).concat(xe(T),`;

  // Thickness in WebGL units (needed to compute clamping margin and extremity lengths)
  float pixelsThickness = max(a_thickness, u_minEdgeThickness * u_sizeRatio);
  float webGLThickness = pixelsThickness * u_correctionRatio / u_sizeRatio;

  // SDF clamping: find where the edge body meets the node boundaries. Always
  // searched (ungated) so labels get a true boundary clamp; the body re-applies
  // its extremity gating in-shader.
`).concat(g,`
  float tStart = queryFindSourceClampT(pathId, a_source, a_sourceSize, int(a_sourceShapeId), a_sourceRotateAlign, a_target, 0.0);
`).concat(y,`
  float tEnd = queryFindTargetClampT(pathId, a_source, a_target, a_targetSize, int(a_targetShapeId), a_targetRotateAlign, 0.0);

  // straightenFactor (frame .z) is consumed only by the body, which runs to the
  // node center when an extremity is absent. Derive the straightening math from
  // these gated clamps \u2014 not the ungated boundary ones above \u2014 so it matches the
  // geometry it drives. The ungated tStart/tEnd remain what labels read.
  float bodyTStart = tailLengthRatio > 0.0 ? tStart : 0.0;
  float bodyTEnd = headLengthRatio > 0.0 ? tEnd : 1.0;

  // Path length and zone boundaries (needed for straightening check)
  float pathLength = queryPathLength(pathId, a_source, a_target);
  float visibleLength = pathLength * (bodyTEnd - bodyTStart);

  float headLength = headLengthRatio * webGLThickness;
  float tailLength = tailLengthRatio * webGLThickness;
  float minBodyLength = minBodyLengthRatio * webGLThickness;

  float totalNeededLength = headLength + tailLength + minBodyLength;
  float extremityScale = 1.0;
  if (totalNeededLength > visibleLength && totalNeededLength > 0.0001) {
    extremityScale = visibleLength / totalNeededLength;
    headLength *= extremityScale;
    tailLength *= extremityScale;
  }

  float headLengthT = pathLength > 0.0001 ? headLength / pathLength : 0.0;
  float tailLengthT = pathLength > 0.0001 ? tailLength / pathLength : 0.0;

  float tTailEnd = bodyTStart + tailLengthT;
  float tHeadStart = bodyTEnd - headLengthT;
  if (tTailEnd > tHeadStart) {
    float mid = (bodyTStart + bodyTEnd) * 0.5;
    tTailEnd = mid;
    tHeadStart = mid;
  }

  // Straighten factor: blend toward straight line when path twists in extremity zones
  float straightenFactor = 0.0;
  {
    float maxDeviation = 0.0;
    if (tailLengthT > 0.0001) {
      vec2 tailTang = queryPathTangent(pathId, tTailEnd, a_source, a_target);
      vec2 tailChord = queryPathPosition(pathId, bodyTStart, a_source, a_target)
                     - queryPathPosition(pathId, tTailEnd, a_source, a_target);
      float tailChordLen = length(tailChord);
      if (tailChordLen > 0.0001) {
        maxDeviation = max(maxDeviation, 1.0 - dot(-tailTang, tailChord / tailChordLen));
      }
    }
    if (headLengthT > 0.0001) {
      vec2 headTang = queryPathTangent(pathId, tHeadStart, a_source, a_target);
      vec2 headChord = queryPathPosition(pathId, bodyTEnd, a_source, a_target)
                     - queryPathPosition(pathId, tHeadStart, a_source, a_target);
      float headChordLen = length(headChord);
      if (headChordLen > 0.0001) {
        maxDeviation = max(maxDeviation, 1.0 - dot(headTang, headChord / headChordLen));
      }
    }
    straightenFactor = smoothstep(0.035, 0.5, maxDeviation);
  }

  // When straightening, blend the ungated tStart/tEnd (the label-facing clamps)
  // toward straight-line clamp positions.
  if (straightenFactor > 0.001) {
    if (tailLengthRatio > 0.0) {
`).concat(g,`
      float srcExtent = a_sourceSize * u_correctionRatio / u_sizeRatio * 2.0;
      float srcEffective = 1.0 - u_correctionRatio / srcExtent;
      float srcCa = u_cameraAngle * (1.0 - a_sourceRotateAlign);
      mat2 srcRot = mat2(cos(srcCa), -sin(srcCa), sin(srcCa), cos(srcCa));
      float lo = 0.0, hi = 0.5;
      for (int i = 0; i < 12; i++) {
        float mid = (lo + hi) * 0.5;
        vec2 pos = mix(a_source, a_target, mid);
        vec2 localPos = srcRot * ((pos - a_source) / srcExtent);
        float sdf = querySDF(int(a_sourceShapeId), localPos, srcEffective);
        if (sdf < 0.0) lo = mid; else hi = mid;
      }
      tStart = mix(tStart, (lo + hi) * 0.5, straightenFactor);
    }
    if (headLengthRatio > 0.0) {
`).concat(y,`
      float tgtExtent = a_targetSize * u_correctionRatio / u_sizeRatio * 2.0;
      float tgtEffective = 1.0 - u_correctionRatio / tgtExtent;
      float tgtCa = u_cameraAngle * (1.0 - a_targetRotateAlign);
      mat2 tgtRot = mat2(cos(tgtCa), -sin(tgtCa), sin(tgtCa), cos(tgtCa));
      float lo = 0.5, hi = 1.0;
      for (int i = 0; i < 12; i++) {
        float mid = (lo + hi) * 0.5;
        vec2 pos = mix(a_source, a_target, mid);
        vec2 localPos = tgtRot * ((pos - a_target) / tgtExtent);
        float sdf = querySDF(int(a_targetShapeId), localPos, tgtEffective);
        if (sdf < 0.0) hi = mid; else lo = mid;
      }
      tEnd = mix(tEnd, (lo + hi) * 0.5, straightenFactor);
    }
  }

  v_clamp = vec4(tStart, tEnd, straightenFactor, pathLength);

  // Scatter this point to its edge's texel center in the frame texture.
  float x = mod(float(edgeIdx), u_frameTextureWidth);
  float y = floor(float(edgeIdx) / u_frameTextureWidth);
  vec2 ndc = (vec2(x, y) + 0.5) / vec2(u_frameTextureWidth, u_frameTextureHeight) * 2.0 - 1.0;
  gl_Position = vec4(ndc, 0.0, 1.0);
  gl_PointSize = 1.0;
}
`);return _}var _a=0,Io=1,xa=2;function Ch(a,n,e){var t=[];e&&(t.push([_a,0,-1],[_a,0,1]),t.push([_a,1,-1],[_a,1,1]));for(var r=0;r<=a;r++){var i=r/a;t.push([Io,i,-1],[Io,i,1])}return n&&(t.push([xa,0,-1],[xa,0,1]),t.push([xa,1,-1],[xa,1,1])),{data:t,attributes:[{name:"a_zone",size:1,type:An},{name:"a_zoneT",size:1,type:An},{name:"a_side",size:1,type:An}],verticesPerEdge:t.length}}function Lh(a,n,e,t){var r=$e([].concat(Q(a),Q(e))),i=Ln(r),o=new Set(["u_matrix","u_sizeRatio","u_correctionRatio","u_zoomRatio","u_pixelRatio","u_cameraAngle","u_minEdgeThickness","u_pickingPadding","u_nodeDataTexture"]),s=new Set,l=[],u=function(v){!o.has(v.name)&&!s.has(v.name)&&(s.add(v.name),l.push("uniform ".concat(v.type," ").concat(v.name,";")))};a.forEach(function(m){return m.uniforms.forEach(u)}),n.forEach(function(m){return m.uniforms.forEach(u)}),e.forEach(function(m){return m.uniforms.forEach(u)});var d=t.map(function(m){var v=m.size===1?"float":"vec".concat(m.size);return"in ".concat(v," ").concat(m.name,";")}).join(`
`),h=n.map(function(m){return xe(m.widthFactor)}).join(", "),c=Math.max.apply(Math,Q(a.map(function(m){return m.minBodyLengthRatio||0}))),f=e.some(function(m){return m.needsNodeColors}),g=a.some(function(m){return m.needsNodeSize}),y=`#version 300 es

// Constant attributes (per vertex)
`.concat(d,`

// Per-edge attributes
// Edge data (source/target indices, thickness, extremity ratios, path/extremity IDs)
// is fetched from edge data texture via edge index
in float a_edgeIndex;   // Index into edge data texture
in vec4 a_color;        // Edge color
in vec4 a_id;           // Edge ID for picking
in float a_opacity;     // Edge opacity

// Standard uniforms
uniform mat3 u_matrix;
uniform float u_sizeRatio;
uniform float u_correctionRatio;
uniform float u_zoomRatio;
uniform float u_pixelRatio;
uniform float u_cameraAngle;
uniform float u_minEdgeThickness;
#ifdef PICKING_MODE
uniform float u_pickingPadding;
#endif
uniform sampler2D u_nodeDataTexture;
uniform int u_nodeDataTextureWidth;
uniform sampler2D u_edgeDataTexture;
uniform int u_edgeDataTextureWidth;
uniform sampler2D u_edgeFrameTexture;
uniform int u_edgeFrameTextureWidth;

// Edge path attribute texture uniforms
`).concat(i.uniformDeclarations,`

// Custom uniforms
`).concat(l.join(`
`),`

// Standard varyings
out vec4 v_color;
out float v_opacity;
out vec4 v_id;
out float v_thickness;       // Edge body thickness (in consistent units)
out float v_t;
out float v_tStart;
out float v_tEnd;
out float v_side;
out float v_antialiasingWidth;  // Anti-aliasing width (normalized: u_correctionRatio / thickness)
out vec2 v_source;
out vec2 v_target;
out float v_edgeLength;
`).concat(g?`
out float v_sourceNodeSize;  // Source node size (mirrored in labels/generator.ts as plain float)
out float v_targetNodeSize;  // Target node size (mirrored in labels/generator.ts as plain float)`:"",`
`).concat(f?`
out vec4 v_sourceColor;
out vec4 v_targetColor;`:"",`
// Zone varyings
out float v_zone;            // 0=tail, 1=body, 2=head
out float v_zoneT;           // Position within zone [0,1]
out float v_headLengthRatio; // Head length as ratio of thickness
out float v_tailLengthRatio; // Tail length as ratio of thickness
out float v_headWidthRatio;  // Head width factor
out float v_tailWidthRatio;  // Tail width factor

// Multi-path/extremity varyings
flat out int v_pathId;
flat out int v_headId;
flat out int v_tailId;

// Path/layer attribute varyings (fetched from edge attribute texture)
`).concat(i.vertexVaryingDeclarations,`

const float bias = 255.0 / 254.0;

// Width factor array for extremities (shared pool for head/tail)
const float EXTREMITY_WIDTH_FACTORS[`).concat(n.length,"] = float[](").concat(h,`);

// All path functions
`).concat(_r(a),`

// Path selector functions
`).concat(xr(a),`

// Node-data fetch helper (geometry texel of the two-texel node stride)
`).concat(lt,`
`).concat(f?Md:"",`
// Per-edge clamp from the frame-pass (tStart, tEnd, straightenFactor, pathLength)
`).concat(rn,`

void main() {
  // Fetch edge data from edge texture (2 texels per edge)
  // Texel 0: sourceNodeIndex, targetNodeIndex, thickness, reserved
  // Texel 1: headLengthRatio, tailLengthRatio, pathId, (headId << 4) | tailId
  int edgeIdx = int(a_edgeIndex);

  // Hidden edges are flagged with a negative row by EdgeProgram.process(). Push
  // the whole primitive outside the clip volume: every vertex lands at the same
  // out-of-range position, so it is fully clipped and rasterizes nothing \u2014
  // neither to the frame buffer nor to the picking buffer.
  if (edgeIdx < 0) {
    gl_Position = vec4(2.0, 0.0, 0.0, 1.0);
    v_color = vec4(0.0);
    v_id = vec4(0.0);
    return;
  }

  int texel0Idx = edgeIdx * 2;
  int texel1Idx = edgeIdx * 2 + 1;
  ivec2 edgeTexCoord0 = ivec2(texel0Idx % u_edgeDataTextureWidth, texel0Idx / u_edgeDataTextureWidth);
  ivec2 edgeTexCoord1 = ivec2(texel1Idx % u_edgeDataTextureWidth, texel1Idx / u_edgeDataTextureWidth);
  vec4 edgeData0 = texelFetch(u_edgeDataTexture, edgeTexCoord0, 0);
  vec4 edgeData1 = texelFetch(u_edgeDataTexture, edgeTexCoord1, 0);

  // Unpack edge data
  int srcIdx = int(edgeData0.x);
  int tgtIdx = int(edgeData0.y);
  float a_thickness = edgeData0.z;
  // edgeData0.w is now reserved (curvature moved to path attribute texture)
  float a_headLengthRatio = edgeData1.x;
  float a_tailLengthRatio = edgeData1.y;
  int pathId = int(edgeData1.z);
  int extremityPacked = int(edgeData1.w);
  int headId = extremityPacked >> 4;
  int tailId = extremityPacked & 15;

  // Fetch path/layer attributes from edge attribute texture
`).concat(i.fetchCode,`

  // Assign path/layer attribute varyings
`).concat(i.varyingAssignments,`

  // Fetch source and target node geometry (texel 0 of the two-texel node stride)
  vec4 srcNodeData = readNodeData(u_nodeDataTexture, u_nodeDataTextureWidth, srcIdx);
  vec4 tgtNodeData = readNodeData(u_nodeDataTexture, u_nodeDataTextureWidth, tgtIdx);

  vec2 a_source = srcNodeData.xy;
  vec2 a_target = tgtNodeData.xy;
`).concat(g?`
  // Assign node size varyings early (path functions like loops need them during clamping)
  v_sourceNodeSize = srcNodeData.z;
  v_targetNodeSize = tgtNodeData.z;`:"",`
`).concat(f?`
  v_sourceColor = readNodeColor(u_nodeDataTexture, u_nodeDataTextureWidth, srcIdx);
  v_targetColor = readNodeColor(u_nodeDataTexture, u_nodeDataTextureWidth, tgtIdx);`:"",`

  // Convert thickness to WebGL units
  float minThickness = u_minEdgeThickness;
  float pixelsThickness = max(a_thickness, minThickness * u_sizeRatio);
  float webGLThickness = pixelsThickness * u_correctionRatio / u_sizeRatio;

  // Extremity parameters from ID lookups (shared pool)
  float headLengthRatio = a_headLengthRatio;
  float tailLengthRatio = a_tailLengthRatio;
  float headWidthFactor = EXTREMITY_WIDTH_FACTORS[headId];
  float tailWidthFactor = EXTREMITY_WIDTH_FACTORS[tailId];
  float minBodyLengthRatio = `).concat(xe(c),`;

  // Per-edge values from the frame-pass texture (read by edge index).
  // tStart/tEnd are the ungated boundary clamps: re-apply the body's extremity
  // gating here (no extremity \u2192 body runs to the node center, 0/1).
  vec4 frameClamp = readFrameTexel(u_edgeFrameTexture, u_edgeFrameTextureWidth, edgeIdx);
  float tStart           = a_tailLengthRatio > 0.0 ? frameClamp.x : 0.0;
  float tEnd             = a_headLengthRatio > 0.0 ? frameClamp.y : 1.0;
  float straightenFactor = frameClamp.z;
  float pathLength       = frameClamp.w;

  // Anti-aliasing width (~1 pixel, normalized by thickness)
  float antialiasingWidth = u_correctionRatio / webGLThickness;

  float visibleLength = pathLength * (tEnd - tStart);

  // Compute extremity lengths in world units
  float headLength = headLengthRatio * webGLThickness;
  float tailLength = tailLengthRatio * webGLThickness;
  float minBodyLength = minBodyLengthRatio * webGLThickness;

  // Handle short edges: scale down extremities if needed
  float totalNeededLength = headLength + tailLength + minBodyLength;
  float extremityScale = 1.0;
  if (totalNeededLength > visibleLength && totalNeededLength > 0.0001) {
    extremityScale = visibleLength / totalNeededLength;
    headLength *= extremityScale;
    tailLength *= extremityScale;
  }

  // Convert lengths to t-values
  float headLengthT = pathLength > 0.0001 ? headLength / pathLength : 0.0;
  float tailLengthT = pathLength > 0.0001 ? tailLength / pathLength : 0.0;

  // Zone boundaries in t-space
  float tTailEnd = tStart + tailLengthT;
  float tHeadStart = tEnd - headLengthT;

  // Ensure body has non-negative length
  if (tTailEnd > tHeadStart) {
    float mid = (tStart + tEnd) * 0.5;
    tTailEnd = mid;
    tHeadStart = mid;
  }

  // Convert to webGL units for geometry expansion
  float aaWidthWebGL = antialiasingWidth * webGLThickness;

  // Extra geometry width for picking padding (0 in visual mode)
  #ifdef PICKING_MODE
    float pickingPaddingWebGL = u_pickingPadding * u_correctionRatio;
  #else
    float pickingPaddingWebGL = 0.0;
  #endif

  // Straight-line direction and normal (for blending when straightenFactor > 0)
  vec2 straightDir = length(a_target - a_source) > 0.0001
    ? normalize(a_target - a_source) : vec2(1.0, 0.0);
  vec2 straightNormal = vec2(-straightDir.y, straightDir.x);

  // Zone-based vertex processing using path selectors
  vec2 position;
  vec2 normal;
  float t;
  float zone = a_zone;
  float zoneT = a_zoneT;
  float side = a_side;

  // Scaled extremity width factors (geometry must be at least as wide as body)
  float scaledTailWidth = max(tailWidthFactor * extremityScale, 1.0);
  float scaledHeadWidth = max(headWidthFactor * extremityScale, 1.0);

  if (zone < 0.5) {
    // TAIL ZONE: rectangular quad with scaled width
    vec2 tang = queryPathTangent(pathId, tTailEnd, a_source, a_target);
    normal = vec2(-tang.y, tang.x);
    vec2 centerPos = mix(queryPathPosition(pathId, tStart, a_source, a_target),
                         queryPathPosition(pathId, tTailEnd, a_source, a_target), zoneT);
    float halfWidth = webGLThickness * scaledTailWidth * 0.5 + aaWidthWebGL + pickingPaddingWebGL;
    position = centerPos + normal * side * halfWidth;
    t = mix(tStart, tTailEnd, zoneT);

  } else if (zone < 1.5) {
    // BODY ZONE: follows path curvature with width = 1.0
    t = mix(tTailEnd, tHeadStart, zoneT);
    normal = queryPathNormal(pathId, t, a_source, a_target);
    float halfWidth = webGLThickness * 0.5 + aaWidthWebGL + pickingPaddingWebGL;
    position = queryPathPosition(pathId, t, a_source, a_target) + normal * side * halfWidth;

  } else {
    // HEAD ZONE: rectangular quad with scaled width
    vec2 tang = queryPathTangent(pathId, tHeadStart, a_source, a_target);
    normal = vec2(-tang.y, tang.x);
    vec2 centerPos = mix(queryPathPosition(pathId, tHeadStart, a_source, a_target),
                         queryPathPosition(pathId, tEnd, a_source, a_target), zoneT);
    float halfWidth = webGLThickness * scaledHeadWidth * 0.5 + aaWidthWebGL + pickingPaddingWebGL;
    position = centerPos + normal * side * halfWidth;
    t = mix(tHeadStart, tEnd, zoneT);
  }

  // Blend toward straight line based on path twist in extremity zones
  if (straightenFactor > 0.001) {
    float zoneWidth = zone < 0.5 ? webGLThickness * scaledTailWidth * 0.5 + aaWidthWebGL + pickingPaddingWebGL :
                      zone < 1.5 ? webGLThickness * 0.5 + aaWidthWebGL + pickingPaddingWebGL :
                      webGLThickness * scaledHeadWidth * 0.5 + aaWidthWebGL + pickingPaddingWebGL;
    vec2 straightPos = mix(a_source, a_target, t) + straightNormal * side * zoneWidth;
    position = mix(position, straightPos, straightenFactor);
  }

  gl_Position = vec4((u_matrix * vec3(position, 1.0)).xy, 0.0, 1.0);

  // Pass varyings to fragment shader
  v_color = a_color;
  v_color.a *= bias;
  v_opacity = a_opacity;
  v_id = a_id;
  v_thickness = webGLThickness;
  v_t = t;
  v_tStart = tStart;
  v_tEnd = tEnd;
  v_side = side;
  v_antialiasingWidth = antialiasingWidth;
  v_source = a_source;
  v_target = a_target;
  v_edgeLength = pathLength;

  // Zone varyings
  v_zone = zone;
  v_zoneT = zoneT;
  v_headLengthRatio = headLengthRatio * extremityScale;
  v_tailLengthRatio = tailLengthRatio * extremityScale;
  // Scale extremity width proportionally with length when crushed
  v_headWidthRatio = headWidthFactor * extremityScale;
  v_tailWidthRatio = tailWidthFactor * extremityScale;

  // Multi-path varyings
  v_pathId = pathId;
  v_headId = headId;
  v_tailId = tailId;
}
`);return y}function kh(a,n,e,t){var r=$e([].concat(Q(a),Q(e))),i=Ln(r),o=new Set(["u_matrix","u_sizeRatio","u_correctionRatio","u_zoomRatio","u_pixelRatio","u_cameraAngle","u_minEdgeThickness","u_pickingPadding"]),s=new Set,l=[],u=function(p){!o.has(p.name)&&!s.has(p.name)&&(s.add(p.name),l.push("uniform ".concat(p.type," ").concat(p.name,";")))};a.forEach(function(v){return v.uniforms.forEach(u)}),n.forEach(function(v){return v.uniforms.forEach(u)}),e.forEach(function(v){return v.uniforms.forEach(u)});var d=n.map(function(v){var p;return xe((p=v.baseRatio)!==null&&p!==void 0?p:.5)}).join(", "),h=function(p){var b,T;return n.length>1?"EXTREMITY_BASE_RATIOS[".concat(p,"]"):xe((b=(T=n[0])===null||T===void 0?void 0:T.baseRatio)!==null&&b!==void 0?b:.5)},c=n.some(function(v){return ot(v.length)?!0:v.length>0}),f=e.some(function(v){return v.needsNodeColors}),g=a.some(function(v){return v.needsNodeSize}),y=e.map(function(v,p){return"  // Layer ".concat(p+1,": ").concat(v.name,`
  color = blendOver(color, layer_`).concat(v.name,"(context));")}).join(`

`),m=`#version 300 es
precision highp float;

// Standard varyings
in vec4 v_color;
in float v_opacity;
in vec4 v_id;
in float v_thickness;       // Edge body thickness
in float v_t;
in float v_tStart;
in float v_tEnd;
in float v_side;
in float v_antialiasingWidth;  // Anti-aliasing width (normalized: u_correctionRatio / thickness)
in vec2 v_source;
in vec2 v_target;
in float v_edgeLength;
`.concat(g?`
in float v_sourceNodeSize;   // Source node size (mirrored in labels/generator.ts as plain float)
in float v_targetNodeSize;   // Target node size (mirrored in labels/generator.ts as plain float)`:"",`
`).concat(f?`
in vec4 v_sourceColor;
in vec4 v_targetColor;`:"",`
// Zone varyings
in float v_zone;            // 0=tail, 1=body, 2=head
in float v_zoneT;           // Position within zone [0,1]
in float v_headLengthRatio; // Head length as ratio of thickness (scaled for short edges)
in float v_tailLengthRatio; // Tail length as ratio of thickness (scaled for short edges)
in float v_headWidthRatio;  // Head width factor
in float v_tailWidthRatio;  // Tail width factor

// Multi-path/extremity varyings
flat in int v_pathId;
flat in int v_headId;
flat in int v_tailId;

// Path/layer attribute varyings (from vertex shader texture fetch)
`).concat(i.fragmentVaryingDeclarations,`

// Standard uniforms (needed by some path types)
uniform float u_sizeRatio;
uniform float u_correctionRatio;
uniform float u_cameraAngle;
#ifdef PICKING_MODE
uniform float u_pickingPadding;
#endif

// Custom uniforms
`).concat(l.join(`
`),`

// Fragment output (single target - picking handled via separate pass)
out vec4 fragColor;

`).concat(n.length>1?`// Base ratio array for extremities (shared pool for head/tail)
const float EXTREMITY_BASE_RATIOS[`.concat(n.length,"] = float[](").concat(d,");"):"",`

// EdgeContext struct
struct EdgeContext {
  float t;                   // Position along path [0, 1]
  float sdf;                 // Signed distance from centerline
  vec2 position;             // World position
  vec2 tangent;              // Path tangent
  vec2 normal;               // Path normal
  float thickness;           // Edge thickness
  float aaWidth;             // Anti-aliasing width
  float edgeLength;          // Total path length
  float tStart;              // Clamped start t
  float tEnd;                // Clamped end t
  float distanceFromSource;  // Arc distance from source
  float distanceToTarget;    // Arc distance to target
};

EdgeContext context;

// Alpha "over" compositing for layer blending
vec4 blendOver(vec4 bg, vec4 fg) {
  float a = fg.a;
  return vec4(mix(bg.rgb, fg.rgb, a), bg.a + a * (1.0 - bg.a));
}

// All path functions
`).concat(_r(a),`

// Path selector functions
`).concat(xr(a),`

// All extremity functions
`).concat(Eh(n),`

// Extremity SDF selector (shared pool for head/tail)
`).concat(Ah(n),`

// Layer functions
`).concat(e.map(function(v){return v.glsl}).join(`

`),`

// Helper: Compute arc length using path selector
float computeArcLengthMulti(int pathId, float t0, float t1, vec2 source, vec2 target, int samples) {
  float arcLen = 0.0;
  vec2 prev = queryPathPosition(pathId, t0, source, target);
  for (int i = 1; i <= samples; i++) {
    float t = t0 + (t1 - t0) * float(i) / float(samples);
    vec2 curr = queryPathPosition(pathId, t, source, target);
    arcLen += length(curr - prev);
    prev = curr;
  }
  return arcLen;
}

void main() {
  // Compute normalized t within visible edge (0 = start, 1 = end)
  float tNorm = (v_t - v_tStart) / max(v_tEnd - v_tStart, 0.0001);

  // Edge body half-thickness
  float halfThickness = v_thickness * 0.5;

  // Convert normalized AA width to webGL units (~1 pixel)
  float aaWidthWebGL = v_antialiasingWidth * v_thickness;

  // Distance from centerline based on v_side interpolation
  float zoneWidthFactor = v_zone < 0.5 ? v_tailWidthRatio :
                          v_zone < 1.5 ? 1.0 :
                          v_headWidthRatio;
  // In PICKING_MODE, inflate halfGeometryWidth to match the inflated vertex geometry
  #ifdef PICKING_MODE
    float halfGeometryWidth = halfThickness * zoneWidthFactor + aaWidthWebGL + u_pickingPadding * aaWidthWebGL;
  #else
    float halfGeometryWidth = halfThickness * zoneWidthFactor + aaWidthWebGL;
  #endif
  float distFromCenter = abs(v_side) * halfGeometryWidth;

  // Populate EdgeContext (for layer functions)
  context.t = tNorm;
  context.sdf = distFromCenter - halfThickness;
  context.position = queryPathPosition(v_pathId, v_t, v_source, v_target);
  context.tangent = queryPathTangent(v_pathId, v_t, v_source, v_target);
  context.normal = vec2(-context.tangent.y, context.tangent.x);
  context.thickness = v_thickness;
  context.aaWidth = aaWidthWebGL;
  context.edgeLength = v_edgeLength;
  context.tStart = v_tStart;
  context.tEnd = v_tEnd;

  // Compute arc distances
  float visibleLength = v_edgeLength * (v_tEnd - v_tStart);
  float pathT = v_t;
  float pathTNorm = tNorm;
`).concat(a.every(function(v){return v.linearParameterization})?`  // All paths have linear parameterization: t maps directly to arc distance
  context.distanceFromSource = pathTNorm * visibleLength;
  context.distanceToTarget = (1.0 - pathTNorm) * visibleLength;`:a.every(function(v){return!v.linearParameterization})?`  // No paths have linear parameterization: use numerical integration
  context.distanceFromSource = computeArcLengthMulti(v_pathId, v_tStart, pathT, v_source, v_target, 16);
  context.distanceToTarget = computeArcLengthMulti(v_pathId, pathT, v_tEnd, v_source, v_target, 16);`:`  // Mixed parameterization: use analytical for linear paths, numerical for others
  if (`.concat(a.filter(function(v){return v.linearParameterization}).map(function(v){return"v_pathId == ".concat(a.indexOf(v))}).join(" || "),`) {
    context.distanceFromSource = pathTNorm * visibleLength;
    context.distanceToTarget = (1.0 - pathTNorm) * visibleLength;
  } else {
    context.distanceFromSource = computeArcLengthMulti(v_pathId, v_tStart, pathT, v_source, v_target, 16);
    context.distanceToTarget = computeArcLengthMulti(v_pathId, pathT, v_tEnd, v_source, v_target, 16);
  }`),`

  // Compute SDF based on zone using extremity selector (shared pool)
  float bodySDF = distFromCenter - halfThickness;
  float finalSDF;

`).concat(c?`  // Base ratios, from baseRatioLookup
  float headBaseRatio = `.concat(h("v_headId"),`;
  float tailBaseRatio = `).concat(h("v_tailId"),`;

  if (v_zone < 0.5) {
    // TAIL ZONE: v_zoneT goes 0 (tip) to 1 (base)
    vec2 uv = vec2((1.0 - v_zoneT) * v_tailLengthRatio, v_side * v_tailWidthRatio * 0.5);
    float tailSDF = queryExtremitySDF(v_tailId, uv, v_tailLengthRatio, v_tailWidthRatio) * v_thickness;

    // Apply union only near base (v_zoneT > 1 - baseRatio)
    if (v_zoneT > 1.0 - tailBaseRatio) {
      finalSDF = min(tailSDF, bodySDF);
    } else {
      finalSDF = tailSDF;
    }
  } else if (v_zone < 1.5) {
    // BODY ZONE: distance from centerline
    finalSDF = bodySDF;
  } else {
    // HEAD ZONE: v_zoneT goes 0 (base) to 1 (tip)
    vec2 uv = vec2(v_zoneT * v_headLengthRatio, v_side * v_headWidthRatio * 0.5);
    float headSDF = queryExtremitySDF(v_headId, uv, v_headLengthRatio, v_headWidthRatio) * v_thickness;

    // Apply union only near base (v_zoneT < baseRatio)
    if (v_zoneT < headBaseRatio) {
      finalSDF = min(headSDF, bodySDF);
    } else {
      finalSDF = headSDF;
    }
  }`):`  // No extremity draws tail/head geometry, so every vertex is body zone.
  finalSDF = bodySDF;`,`

  #ifdef PICKING_MODE
    // Picking pass: output edge ID for pixels within the picking area
    if (finalSDF > u_pickingPadding * aaWidthWebGL) discard;
    fragColor = v_id;
  #else
`).concat(t?`    // Visual pass: anti-aliased edge with layers, edge opacity applied once
    float alpha = smoothstep(aaWidthWebGL, -aaWidthWebGL, finalSDF) * v_opacity;`:`    // Visual pass: hard-edged (no anti-aliasing gradient) edge with layers, edge opacity applied once
    float alpha = (finalSDF < 0.0 ? 1.0 : 0.0) * v_opacity;`,`
    if (alpha < 0.01) discard;

    // Apply layers sequentially with "over" compositing
    vec4 color = vec4(0.0);

`).concat(y,`

    // Mix with transparent to fade both color AND alpha (pre-multiplied alpha for correct blending)
    fragColor = mix(vec4(0.0), color, alpha);
  #endif
}
`);return m}function Ph(a,n,e){var t=ot(n.length)?!0:n.length>0,r=ot(e.length)?!0:e.length>0;if(a.generateConstantData){var i=a.generateConstantData();return{data:i.data,attributes:i.attributes,verticesPerEdge:i.verticesPerEdge}}return Ch(a.segments,t,r)}function Go(a){var n,e=Jo(a),t=e.paths,r=e.extremities,i=e.layers,o=(n=a.antialias)!==null&&n!==void 0?n:!0,s=new Map,l=new Map,u=new Map,d=O(t),h;try{for(d.s();!(h=d.n()).done;){var c=h.value,f=O(r),g;try{for(f.s();!(g=f.n()).done;){var y=g.value,m=O(r),v;try{for(m.s();!(v=m.n()).done;){var p=v.value,b="".concat(c.name,":").concat(y.name,":").concat(p.name),T=Ph(c,y,p);s.set(b,T.verticesPerEdge),l.set(b,T.data);var _=O(T.attributes),E;try{for(_.s();!(E=_.n()).done;){var A=E.value;u.has(A.name)||u.set(A.name,A)}}catch(q){_.e(q)}finally{_.f()}}}catch(q){m.e(q)}finally{m.f()}}}catch(q){f.e(q)}finally{f.f()}}}catch(q){d.e(q)}finally{d.f()}var w=Array.from(u.values()),S={};w.forEach(function(q,Z){S[q.name]=Z});var C=0,G="",L=O(s),N;try{for(L.s();!(N=L.n()).done;){var k=ie(N.value,2),I=k[0],W=k[1];W>C&&(C=W,G=I)}}catch(q){L.e(q)}finally{L.f()}var F=l.get(G)||[],x=G.split(":"),P=ie(x,1),U=P[0],z=t.find(function(q){return q.name===U}),R=[];z!=null&&z.generateConstantData?R=z.generateConstantData().attributes:R=[{name:"a_zone"},{name:"a_zoneT"},{name:"a_side"}];var j=F.map(function(q){var Z=new Array(w.length).fill(0);return R.forEach(function(Se,de){var K=S[Se.name];K!==void 0&&de<q.length&&(Z[K]=q[de])}),Z});return{vertexShader:Lh(t,r,i,w),fragmentShader:kh(t,r,i,o),uniforms:Th(t,r,i),attributes:Fh(),verticesPerEdge:C,constantData:j,constantAttributes:w,vertexCountsPerCombination:s,constantDataPerCombination:l}}function Fh(a,n,e){return[{name:"a_edgeIndex",size:1,type:An},{name:"a_color",size:4,type:Fo,normalized:!0},{name:"a_id",size:4,type:Fo,normalized:!0},{name:"a_opacity",size:1,type:An}]}var Ih=`#version 300 es
precision highp float;

in vec4 v_clamp;

// RGBA32F target: stores (tStart, tEnd, straightenFactor, pathLength).
out vec4 fragColor;

void main() {
  fragColor = v_clamp;
}
`,Gh=(function(){function a(n,e){te(this,a),D(this,"uniformLocations",{});var t=e.paths,r=e.extremities,i=e.layers,o=e.nodeShapes,s=e.nodeLayers;this.gl=n,this.hasAttributeData=$e([].concat(Q(t),Q(i))).floatsPerItem>0,this.hasNodeAttributeData=Object.keys(on(o,s).offsets).length>0,this.vertexShader=fr(n,Rh(t,r,i,o,s)),this.fragmentShader=gr(n,Ih),this.program=vr(n,[this.vertexShader,this.fragmentShader]);var l=new Set;this.customUniforms=[];for(var u=0,d=[].concat(Q(t),Q(r));u<d.length;u++){var h=d[u],c=O(h.uniforms),f;try{for(c.s();!(f=c.n()).done;){var g=f.value;l.has(g.name)||(l.add(g.name),this.customUniforms.push(g))}}catch(b){c.e(b)}finally{c.f()}}var y=["u_sizeRatio","u_correctionRatio","u_cameraAngle","u_minEdgeThickness","u_nodeDataTexture","u_nodeDataTextureWidth","u_edgeDataTexture","u_edgeDataTextureWidth","u_edgeAttributeTexture","u_edgeAttributeTextureWidth","u_edgeAttributeTexelsPerEdge","u_layerAttributeTexture","u_layerAttributeTextureWidth","u_layerAttributeTexelsPerNode","u_frameTextureWidth","u_frameTextureHeight"].concat(Q(this.customUniforms.map(function(b){return b.name}))),m=O(y),v;try{for(m.s();!(v=m.n()).done;){var p=v.value;this.uniformLocations[p]=n.getUniformLocation(this.program,p)}}catch(b){m.e(b)}finally{m.f()}this.vao=n.createVertexArray()}return ne(a,[{key:"run",value:function(e,t,r,i,o){if(r!==0){var s=this.gl,l=this.uniformLocations;s.useProgram(this.program),s.bindVertexArray(this.vao),l.u_sizeRatio&&s.uniform1f(l.u_sizeRatio,e.sizeRatio),l.u_correctionRatio&&s.uniform1f(l.u_correctionRatio,e.correctionRatio),l.u_cameraAngle&&s.uniform1f(l.u_cameraAngle,e.cameraAngle),l.u_minEdgeThickness&&s.uniform1f(l.u_minEdgeThickness,e.minEdgeThickness),l.u_nodeDataTexture&&s.uniform1i(l.u_nodeDataTexture,e.nodeDataTextureUnit),l.u_nodeDataTextureWidth&&s.uniform1i(l.u_nodeDataTextureWidth,e.nodeDataTextureWidth),l.u_edgeDataTexture&&s.uniform1i(l.u_edgeDataTexture,e.edgeDataTextureUnit),l.u_edgeDataTextureWidth&&s.uniform1i(l.u_edgeDataTextureWidth,e.edgeDataTextureWidth),l.u_frameTextureWidth&&s.uniform1f(l.u_frameTextureWidth,t.getTextureWidth()),l.u_frameTextureHeight&&s.uniform1f(l.u_frameTextureHeight,t.getTextureHeight()),this.hasAttributeData&&i&&(i.bind(mt),l.u_edgeAttributeTexture&&s.uniform1i(l.u_edgeAttributeTexture,mt),l.u_edgeAttributeTextureWidth&&s.uniform1i(l.u_edgeAttributeTextureWidth,i.getTextureWidth()),l.u_edgeAttributeTexelsPerEdge&&s.uniform1i(l.u_edgeAttributeTexelsPerEdge,i.getTexelsPerItem())),this.hasNodeAttributeData&&o&&(o.bind(pt),l.u_layerAttributeTexture&&s.uniform1i(l.u_layerAttributeTexture,pt),l.u_layerAttributeTextureWidth&&s.uniform1i(l.u_layerAttributeTextureWidth,o.getTextureWidth()),l.u_layerAttributeTexelsPerNode&&s.uniform1i(l.u_layerAttributeTexelsPerNode,o.getTexelsPerItem()));var u=O(this.customUniforms),d;try{for(u.s();!(d=u.n()).done;){var h=d.value;br(s,this.uniformLocations[h.name],h)}}catch(c){u.e(c)}finally{u.f()}t.bindAsRenderTarget(),s.disable(s.BLEND),s.disable(s.DEPTH_TEST),s.drawArrays(s.POINTS,0,r),s.bindFramebuffer(s.FRAMEBUFFER,null),s.bindVertexArray(null)}}},{key:"kill",value:function(){var e=this.gl;e.deleteProgram(this.program),e.deleteShader(this.vertexShader),e.deleteShader(this.fragmentShader),e.deleteVertexArray(this.vao)}}])})();function Sn(a,n,e,t,r,i){if(a.length===1)return"".concat(t," ").concat(n,"(int pathId, ").concat(r,`) {
  return path_`).concat(a[0].name,"_").concat(e,"(").concat(i,`);
}`);var o=a.map(function(s,l){return"    case ".concat(l,": return path_").concat(s.name,"_").concat(e,"(").concat(i,");")}).join(`
`);return"".concat(t," ").concat(n,"(int pathId, ").concat(r,`) {
  switch (pathId) {
`).concat(o,`
    default: return path_`).concat(a[0].name,"_").concat(e,"(").concat(i,`);
  }
}`)}var zh=`
vec3 computeEdgeLabelBodyBounds(
  float tStart, float tEnd, float pathLength,
  float webGLThickness, float headLengthRatio, float tailLengthRatio
) {
  float visibleLength = pathLength * (tEnd - tStart);

  float headLength = headLengthRatio * webGLThickness;
  float tailLength = tailLengthRatio * webGLThickness;
  float totalNeededLength = headLength + tailLength;
  if (totalNeededLength > visibleLength && totalNeededLength > 0.0001) {
    float extremityScale = visibleLength / totalNeededLength;
    headLength *= extremityScale;
    tailLength *= extremityScale;
  }

  float bodyStartDist = tStart * pathLength + tailLength;
  float bodyEndDist = tEnd * pathLength - headLength;
  return vec3(bodyStartDist, bodyEndDist, max(bodyEndDist - bodyStartDist, 0.0));
}
`;function Nh(a,n){var e=xe(a),t=xe(n);return`
float computeEdgeLabelAlpha(float bodyLength, float textWidthWebGL) {
  float ratio = textWidthWebGL > 0.0001 ? min(bodyLength / textWidthWebGL, 1.0) : 1.0;
  if (ratio < `.concat(e,`) return 0.0;
  if (ratio < `).concat(t,") return (ratio - ").concat(e,") / (").concat(t," - ").concat(e,`);
  return 1.0;
}
`)}var Mh=`
float computeEdgeLabelScreenDir(int pathId, float t, vec2 source, vec2 target, mat3 matrix) {
  vec2 tangent = queryPathTangent(pathId, t, source, target);
  return (matrix * vec3(tangent, 0.0)).x < 0.0 ? -1.0 : 1.0;
}
`,Wh=`
float computeEdgeLabelPerpOffset(
  float positionMode,
  float halfThickness, float marginWebGL, float halfTextHeight,
  float readingSign, float screenDir
) {
  float magnitude = halfThickness + marginWebGL + halfTextHeight;
  if (positionMode == 1.0) return magnitude * readingSign;
  if (positionMode == 2.0) return -magnitude * readingSign;
  if (positionMode == 3.0) return magnitude * screenDir;
  return 0.0;
}
`;function ts(a){var n=a.paths,e=a.minVisibilityThreshold,t=a.fullVisibilityThreshold,r=n.some(function(s){return s.hasSharpCorners}),i=n.map(function(s){return"// --- Path: ".concat(s.name,` ---
`).concat(s.glsl,`

// Tangent/normal functions: analytical if provided, otherwise numerical
`).concat(s.analyticalTangentGlsl||Zo(s.name),`

// Auto-generated fallbacks for any missing path functions
`).concat(Qo(s.name,s.glsl),`

// Corner skip helpers (for paths with sharp corners like step/taxi)
`).concat(s.cornerSkipGlsl||"",`
`)}).join(`
`),o=r?`// Corner function selectors (only some paths have sharp corners)
vec2 queryGetCornerTs(int pathId, vec2 source, vec2 target) {
  switch (pathId) {
`.concat(n.map(function(s,l){return s.hasSharpCorners?"    case ".concat(l,": return path_").concat(s.name,"_getCornerTs(source, target);"):"    case ".concat(l,": return vec2(-1.0, -1.0); // No corners for ").concat(s.name)}).join(`
`),`
    default: return vec2(-1.0, -1.0);
  }
}

vec2 queryGetCornerConcavity(int pathId, vec2 source, vec2 target, float perpOffset) {
  switch (pathId) {
`).concat(n.map(function(s,l){return s.hasSharpCorners?"    case ".concat(l,": return path_").concat(s.name,"_getCornerConcavity(source, target, perpOffset);"):"    case ".concat(l,": return vec2(0.0, 0.0); // No corners for ").concat(s.name)}).join(`
`),`
    default: return vec2(0.0, 0.0);
  }
}`):"";return`
// ============================================================================
// Node data fetch (geometry texel) and per-edge clamp fetch (edge-frame texture)
// ============================================================================

`.concat(lt,`
`).concat(rn,`

// ============================================================================
// Path Functions (one block per path)
// ============================================================================

`).concat(i,`

// ============================================================================
// Path Query Selectors (dispatch by pathId)
// ============================================================================

`).concat(Sn(n,"queryPathPosition","position","vec2","float t, vec2 source, vec2 target","t, source, target"),`

`).concat(Sn(n,"queryPathTangent","tangent","vec2","float t, vec2 source, vec2 target","t, source, target"),`

`).concat(Sn(n,"queryPathNormal","normal","vec2","float t, vec2 source, vec2 target","t, source, target"),`

`).concat(Sn(n,"queryPathLength","length","float","vec2 source, vec2 target","source, target"),`

`).concat(Sn(n,"queryPathTAtDistance","t_at_distance","float","float dist, vec2 source, vec2 target","dist, source, target"),`

`).concat(o,`

// ============================================================================
// Shared helpers (body bounds, alpha ramp, screen direction, perpendicular offset)
// ============================================================================

`).concat(zh,`
`).concat(Nh(e,t),`
`).concat(Mh,`
`).concat(Wh,`
`)}var Uh=Je.fontSize,Oh=new Map,ns=24,zo=(ns+1)*2;function Bh(a){var n=a.paths,e=a.fontSizeMode,t=a.headLengthRatio,r=a.tailLengthRatio,i=a.minVisibilityThreshold,o=a.fullVisibilityThreshold,s=a.keepUpright,l=e==="scaled",u=At(),d=$e([].concat(Q(n),[u])),h=Ln(d),c=`#version 300 es

// Per-instance attributes
in float a_edgeIndex;
in float a_edgeAttrIndex;
in float a_baseFontSize;
in float a_totalTextWidth;
in float a_positionMode;
in float a_margin;
in float a_padding;
in vec4 a_color;
in vec4 a_id;

// Per-vertex (constant) attribute: strip vertex index
in float a_vertexIndex;

uniform mat3 u_matrix;
uniform float u_sizeRatio;
uniform float u_correctionRatio;
uniform float u_pixelRatio;
uniform float u_cameraAngle;
uniform vec2 u_resolution;
uniform sampler2D u_nodeDataTexture;
uniform int u_nodeDataTextureWidth;
uniform sampler2D u_edgeDataTexture;
uniform int u_edgeDataTextureWidth;
uniform sampler2D u_edgeFrameTexture; // Per-edge clamp (tStart, tEnd, straightenFactor, pathLength)
uniform int u_edgeFrameTextureWidth;
`.concat(l?"uniform float u_zoomSizeRatio;":"",`

`).concat(h.uniformDeclarations,`

out vec4 v_color;
out vec4 v_id;
out float v_alphaModifier;

const float ATLAS_FONT_SIZE = `).concat(xe(Uh),`;
const float HEAD_RATIO = `).concat(xe(t),`;
const float TAIL_RATIO = `).concat(xe(r),`;
const int RIBBON_SEGMENTS = `).concat(ns,`;

// Path attribute varyings (declared as plain locals since this shader has no FS inputs for them)
`).concat(h.vertexVaryingDeclarations.replace(/out /g,""),`

// Node size variables used by some path functions (self-loops, etc.)
float v_sourceNodeSize;
float v_targetNodeSize;

// Shared preamble: shape SDFs, path functions + selectors, clamp, helpers.
`).concat(ts({paths:n,minVisibilityThreshold:i,fullVisibilityThreshold:o}),`

void main() {
  int vIdx = int(a_vertexIndex);
  int pairIdx = vIdx / 2;
  int side = vIdx - pairIdx * 2; // 0 = left/bottom, 1 = right/top

  // --- Fetch edge data (2 texels per edge) ---
  int edgeIdx = int(a_edgeIndex);
  int texel0Idx = edgeIdx * 2;
  int texel1Idx = edgeIdx * 2 + 1;
  ivec2 e0 = ivec2(texel0Idx % u_edgeDataTextureWidth, texel0Idx / u_edgeDataTextureWidth);
  ivec2 e1 = ivec2(texel1Idx % u_edgeDataTextureWidth, texel1Idx / u_edgeDataTextureWidth);
  vec4 edgeData0 = texelFetch(u_edgeDataTexture, e0, 0);
  vec4 edgeData1 = texelFetch(u_edgeDataTexture, e1, 0);

  int srcIdx = int(edgeData0.x);
  int tgtIdx = int(edgeData0.y);
  float thickness = edgeData0.z;
  int pathId = int(edgeData1.z);

  // --- Fetch path attributes (curvature, etc.) ---
  {
    int edgeIdx = int(a_edgeAttrIndex);
`).concat(h.fetchCode,`
`).concat(h.varyingAssignments,`
  }

  // --- Fetch node data: geometry (texel 0) + rotation flags (texel 1) ---
  vec4 srcN = readNodeData(u_nodeDataTexture, u_nodeDataTextureWidth, srcIdx);
  vec4 tgtN = readNodeData(u_nodeDataTexture, u_nodeDataTextureWidth, tgtIdx);

  vec2 source = srcN.xy;
  vec2 target = tgtN.xy;
  float sourceSize = srcN.z;
  float targetSize = tgtN.z;
  v_sourceNodeSize = sourceSize;
  v_targetNodeSize = targetSize;

  // --- Pixel-to-graph conversion (fixed font mode) ---
  float matrixScaleX = length(vec2(u_matrix[0][0], u_matrix[1][0]));
  float pixelToGraph = 2.0 / (matrixScaleX * u_resolution.x);

  float webGLThickness = thickness * u_correctionRatio / u_sizeRatio;

  // --- Body bounds (shared with edge label shader) ---
  vec4 edgeClamp = readFrameTexel(u_edgeFrameTexture, u_edgeFrameTextureWidth, edgeIdx);
  vec3 bodyBounds = computeEdgeLabelBodyBounds(
    edgeClamp.x, edgeClamp.y, edgeClamp.w,
    webGLThickness, HEAD_RATIO, TAIL_RATIO
  );
  float bodyStartDist = bodyBounds.x;
  float bodyEndDist = bodyBounds.y;
  float bodyLength = bodyBounds.z;

  // --- Text dimensions ---
  float baseFontSize = a_baseFontSize;
  `).concat(l?`float fontScale = baseFontSize / ATLAS_FONT_SIZE * u_zoomSizeRatio;
  float textWidthWebGL = a_totalTextWidth * fontScale * u_correctionRatio / u_sizeRatio;
  float halfTextHeight = baseFontSize * 0.35 * u_zoomSizeRatio * u_correctionRatio / u_sizeRatio;
  float marginWebGL = a_margin * u_zoomSizeRatio * u_correctionRatio / u_sizeRatio;`:`float fontScale = baseFontSize / ATLAS_FONT_SIZE;
  float textWidthWebGL = a_totalTextWidth * fontScale * pixelToGraph;
  float halfTextHeight = baseFontSize * 0.35 * pixelToGraph;
  float marginWebGL = a_margin * pixelToGraph;`,`
  float paddingWebGL = a_padding * pixelToGraph;

  // --- Alpha modifier (shared with edge label shader) ---
  float alphaModifier = computeEdgeLabelAlpha(bodyLength, textWidthWebGL);
  if (alphaModifier <= 0.0 || textWidthWebGL <= 0.0) {
    gl_Position = vec4(2.0, 0.0, 0.0, 1.0);
    v_color = vec4(0.0);
    v_id = vec4(0.0);
    v_alphaModifier = 0.0;
    return;
  }

  // --- Perpendicular offset (shared with edge label shader) ---
  float bodyCenterDist = (bodyStartDist + bodyEndDist) * 0.5;
  float centerT = queryPathTAtDistance(pathId, bodyCenterDist, source, target);
  float screenDir = computeEdgeLabelScreenDir(pathId, centerT, source, target, u_matrix);
  float readingSign = `).concat(s?"screenDir":"1.0",`;
  float halfThickness = webGLThickness * 0.5;
  float perpOffset = computeEdgeLabelPerpOffset(
    a_positionMode, halfThickness, marginWebGL, halfTextHeight, readingSign, screenDir
  );

  // --- Ribbon span (clipped to body) ---
  float halfTextWebGL = textWidthWebGL * 0.5;
  float labelStartDist = max(bodyCenterDist - halfTextWebGL, bodyStartDist);
  float labelEndDist = min(bodyCenterDist + halfTextWebGL, bodyEndDist);

  // Sample centerline at this pair, then apply perpendicular offset.
  // The ribbon follows the centerline path (simple & robust); for curved edges
  // this closely matches the offset path the characters sit on.
  float u = float(pairIdx) / float(RIBBON_SEGMENTS);
  float arcDist = mix(labelStartDist, labelEndDist, u);
  float t = queryPathTAtDistance(pathId, arcDist, source, target);
  vec2 pos = queryPathPosition(pathId, t, source, target);
  vec2 tan = queryPathTangent(pathId, t, source, target);
  vec2 perp = vec2(-tan.y, tan.x);

  vec2 centerPos = pos + perp * perpOffset;

  float halfRibbon = halfTextHeight + paddingWebGL;
  float sideSign = side == 0 ? -1.0 : 1.0;
  vec2 ribbonPos = centerPos + perp * (sideSign * halfRibbon);

  vec3 clipPos = u_matrix * vec3(ribbonPos, 1.0);
  gl_Position = vec4(clipPos.xy, 0.0, 1.0);

  v_color = a_color;
  v_id = a_id;
  v_alphaModifier = alphaModifier;
}
`);return c}var Hh=`#version 300 es
precision highp float;

in vec4 v_color;
in vec4 v_id;
in float v_alphaModifier;

out vec4 fragColor;

void main() {
#ifdef PICKING_MODE
  if (v_alphaModifier <= 0.0) discard;
  fragColor = v_id;
#else
  float alpha = v_color.a * v_alphaModifier;
  if (alpha <= 0.0) discard;
  fragColor = vec4(v_color.rgb * alpha, alpha);
#endif
}
`;function $h(a,n,e,t){var r=t.shaderConfig,i=r.paths,o=r.fontSizeMode;if(i.length===0)throw new Error("createEdgeLabelBackgroundProgram: shaderConfig must declare at least one path");var s=At(),l=$e([].concat(Q(i),[s])),u=Aa([].concat(Q(i),[s]),l),d=Bh(r),h=(function(c){function f(g,y,m){var v;return te(this,f),v=me(this,f,[g,y,m]),D(v,"totalCount",0),D(v,"bufferCapacity",0),D(v,"edgeAttributeTexture",null),v.edgeAttributeTexture=new wa(g,l),v.packedAttributeData=new Float32Array(l.floatsPerItem),v}return ye(f,c),ne(f,[{key:"getDefinition",value:function(){for(var y=WebGL2RenderingContext,m=y.FLOAT,v=y.UNSIGNED_BYTE,p=y.TRIANGLE_STRIP,b=[],T=0;T<zo;T++)b.push([T]);var _=["u_matrix","u_sizeRatio","u_correctionRatio","u_pixelRatio","u_cameraAngle","u_resolution","u_nodeDataTexture","u_nodeDataTextureWidth","u_edgeDataTexture","u_edgeDataTextureWidth","u_edgeFrameTexture","u_edgeFrameTextureWidth"];return o==="scaled"&&_.push("u_zoomSizeRatio"),l.floatsPerItem>0&&_.push("u_edgeAttributeTexture","u_edgeAttributeTextureWidth","u_edgeAttributeTexelsPerEdge"),{VERTICES:zo,VERTEX_SHADER_SOURCE:d,FRAGMENT_SHADER_SOURCE:Hh,METHOD:p,UNIFORMS:_,ATTRIBUTES:[{name:"a_edgeIndex",size:1,type:m},{name:"a_edgeAttrIndex",size:1,type:m},{name:"a_baseFontSize",size:1,type:m},{name:"a_totalTextWidth",size:1,type:m},{name:"a_positionMode",size:1,type:m},{name:"a_margin",size:1,type:m},{name:"a_padding",size:1,type:m},{name:"a_color",size:4,type:v,normalized:!0},{name:"a_id",size:4,type:v,normalized:!0}],CONSTANT_ATTRIBUTES:[{name:"a_vertexIndex",size:1,type:m}],CONSTANT_DATA:b}}},{key:"processEdgeLabelBackground",value:function(y,m,v){var p=0;if(this.edgeAttributeTexture&&l.floatsPerItem>0){p=this.edgeAttributeTexture.allocate(m);var b=this.packedAttributeData;Da(u,v.edgeAttributes,b,"",Oh,0),this.edgeAttributeTexture.updateAllAttributes(m,b)}var T=this.floats,_=this.ints,E=y*this.STRIDE;T[E++]=v.edgeIndex,T[E++]=p,T[E++]=v.baseFontSize,T[E++]=v.totalTextWidth,T[E++]=v.positionMode,T[E++]=v.margin,T[E++]=v.padding,T[E++]=v.color,_[E++]=v.id}},{key:"setUniforms",value:function(y,m){var v=m.gl,p=m.uniformLocations;if(v.uniformMatrix3fv(p.u_matrix,!1,y.matrix),v.uniform1f(p.u_sizeRatio,y.sizeRatio),v.uniform1f(p.u_correctionRatio,y.correctionRatio),v.uniform1f(p.u_pixelRatio,y.pixelRatio),v.uniform1f(p.u_cameraAngle,y.cameraAngle),v.uniform2f(p.u_resolution,y.width,y.height),p.u_nodeDataTexture!==void 0&&v.uniform1i(p.u_nodeDataTexture,y.nodeDataTextureUnit),p.u_nodeDataTextureWidth!==void 0&&v.uniform1i(p.u_nodeDataTextureWidth,y.nodeDataTextureWidth),p.u_edgeDataTexture!==void 0&&v.uniform1i(p.u_edgeDataTexture,y.edgeDataTextureUnit),p.u_edgeDataTextureWidth!==void 0&&v.uniform1i(p.u_edgeDataTextureWidth,y.edgeDataTextureWidth),p.u_edgeFrameTexture!==void 0&&v.uniform1i(p.u_edgeFrameTexture,y.edgeFrameTextureUnit),p.u_edgeFrameTextureWidth!==void 0&&v.uniform1i(p.u_edgeFrameTextureWidth,y.edgeFrameTextureWidth),o==="scaled"&&p.u_zoomSizeRatio!==void 0){var b=this.renderer.getSetting("zoomToSizeRatioFunction");v.uniform1f(p.u_zoomSizeRatio,1/b(y.zoomRatio))}this.edgeAttributeTexture&&l.floatsPerItem>0&&p.u_edgeAttributeTexture!==void 0&&(this.edgeAttributeTexture.bind(mt),v.uniform1i(p.u_edgeAttributeTexture,mt),v.uniform1i(p.u_edgeAttributeTextureWidth,this.edgeAttributeTexture.getTextureWidth()),v.uniform1i(p.u_edgeAttributeTexelsPerEdge,this.edgeAttributeTexture.getTexelsPerItem()))}},{key:"renderProgram",value:function(y,m){this.edgeAttributeTexture&&l.floatsPerItem>0&&this.edgeAttributeTexture.upload(),Ee(f,"renderProgram",this,3)([y,m])}},{key:"kill",value:function(){this.edgeAttributeTexture&&(this.edgeAttributeTexture.kill(),this.edgeAttributeTexture=null),Ee(f,"kill",this,3)([])}},{key:"drawWebGL",value:function(y,m){var v=m.gl;this.totalCount!==0&&v.drawArraysInstanced(v.TRIANGLE_STRIP,0,this.VERTICES,this.totalCount)}},{key:"reallocate",value:function(y){this.totalCount=y,y>this.bufferCapacity&&(this.bufferCapacity=Math.max(y,Math.ceil(this.bufferCapacity*1.5)||10),Ee(f,"reallocate",this,3)([this.bufferCapacity]))}}])})(Lt);return new h(a,n,e)}function as(a){var n,e,t,r,i,o;return{paths:a.paths,headLengthRatio:(n=a.headLengthRatio)!==null&&n!==void 0?n:0,tailLengthRatio:(e=a.tailLengthRatio)!==null&&e!==void 0?e:0,fontSizeMode:(t=a.fontSizeMode)!==null&&t!==void 0?t:"fixed",minVisibilityThreshold:(r=a.minVisibilityThreshold)!==null&&r!==void 0?r:.7,fullVisibilityThreshold:(i=a.fullVisibilityThreshold)!==null&&i!==void 0?i:.8,keepUpright:(o=a.keepUpright)!==null&&o!==void 0?o:!0}}var Vh=Je.fontSize,qh=17/64;function jh(a){var n=a.paths,e=a.hasBorder,t=e===void 0?!1:e,r=a.fontSizeMode,i=r===void 0?"fixed":r,o=a.minVisibilityThreshold,s=o===void 0?.5:o,l=a.fullVisibilityThreshold,u=l===void 0?.6:l,d=a.keepUpright,h=d===void 0?!0:d,c=i==="scaled",f=n.some(function(p){return p.hasSharpCorners}),g=At(),y=$e([].concat(Q(n),[g])),m=Ln(y),v=`#version 300 es

// ============================================================================
// Attributes - Per Character (Instanced)
// ============================================================================

// Edge geometry: indices for texture lookup
// Edge data (source/target node indices, thickness, head/tail ratios) is fetched from edge data texture
// Edge path attributes (curvature, etc.) are fetched from edge attribute texture
in float a_edgeIndex;       // Index into edge data texture
in float a_edgeAttrIndex;   // Index into edge attribute texture (for curvature, etc.)
in float a_baseFontSize;    // Base font size in pixels (per-label)

// Character metrics (in glyph units = atlas font size pixels)
in vec4 a_charMetrics;      // (charTextOffset, charAdvance, totalTextWidth, positionMode)
in vec4 a_charDims;         // (charSize.x, charSize.y, charOffset.x, charOffset.y)

// Atlas texture coordinates
in vec4 a_texCoords;        // (x, y, width, height) in atlas pixels

// Label parameters
in vec2 a_labelParams;      // (margin, unused)

// Appearance
in vec4 a_color;            // Character color (RGBA, normalized)
`.concat(t?"in vec4 a_borderColor;      // Border color (RGBA, normalized)":"",`

// ============================================================================
// Attributes - Per Vertex (Constant)
// ============================================================================

in vec2 a_quadCorner;       // Quad corner: (0,0), (1,0), (0,1), (1,1)

// ============================================================================
// Uniforms
// ============================================================================

uniform mat3 u_matrix;
uniform float u_sizeRatio;
uniform float u_correctionRatio;
uniform float u_pixelRatio;
uniform float u_cameraAngle;    // Required by node shape SDFs
// u_sdfBufferPixels kept for ABI compatibility but unused in shader
uniform float u_sdfBufferPixels;
uniform vec2 u_resolution;
uniform vec2 u_atlasSize;
uniform sampler2D u_nodeDataTexture; // Shared texture with node position/size/shape data
uniform int u_nodeDataTextureWidth;  // Width of 2D node data texture for coordinate calculation
uniform sampler2D u_edgeDataTexture; // Shared texture with edge data
uniform int u_edgeDataTextureWidth;  // Width of 2D edge data texture for coordinate calculation
uniform sampler2D u_edgeFrameTexture; // Per-edge clamp (tStart, tEnd, straightenFactor, pathLength)
uniform int u_edgeFrameTextureWidth;
`).concat(c?"uniform float u_zoomSizeRatio;  // Zoom-based size ratio from zoomToSizeRatioFunction":"",`

// Edge path attribute texture uniforms (for curvature and other path attributes)
`).concat(m.uniformDeclarations,`

// ============================================================================
// Varyings
// ============================================================================

out vec2 v_texCoord;
out vec4 v_color;
`).concat(t?"out vec4 v_borderColor;":"",`
out float v_edgeFade;  // 0 = fully visible, 1 = fully faded (outside body)
out float v_alphaModifier;  // 0-1 based on label visibility ratio
out float v_fontScale;  // Ratio of rendered font size to atlas font size
`).concat(t?"out float v_positionMode;  // Position mode for conditional border (0=over needs border)":"",`

// ============================================================================
// Constants
// ============================================================================

const float bias = 255.0 / 254.0;
const float FADE_WIDTH_PIXELS = 15.0;  // Width of fade gradient in pixels
const float ATLAS_FONT_SIZE = `).concat(xe(Vh),`;  // Base font size used in SDF atlas
const float VERTICAL_CENTER_RATIO = `).concat(xe(qh),`;  // Baseline to visual center ratio

// ============================================================================
// Path Attribute Variables (set in main, used by path functions)
// ============================================================================
// Path attributes are fetched from the edge attribute texture and stored in
// variables with v_ prefix (e.g., v_curvature) for path functions to access.
`).concat(m.vertexVaryingDeclarations.replace(/out /g,""),`

// Node size variables (set in main, used by some path functions like loops).
// These mirror the v_sourceNodeSize / v_targetNodeSize varyings in generator.ts,
// but are plain floats here since the label shader is vertex-only.
float v_sourceNodeSize;
float v_targetNodeSize;

// Shared preamble: shape SDFs, path functions + selectors, clamp, helpers.
`).concat(ts({paths:n,minVisibilityThreshold:s,fullVisibilityThreshold:u}),`

// ============================================================================
// Main
// ============================================================================

void main() {
  // -------------------------------------------------------------------------
  // Fetch edge data from edge texture (2 texels per edge)
  // -------------------------------------------------------------------------
  // Texel 0: sourceNodeIndex, targetNodeIndex, thickness, reserved
  // Texel 1: headLengthRatio, tailLengthRatio, pathId, extremityIds
  int edgeIdx = int(a_edgeIndex);
  int texel0Idx = edgeIdx * 2;
  int texel1Idx = edgeIdx * 2 + 1;
  ivec2 edgeTexCoord0 = ivec2(texel0Idx % u_edgeDataTextureWidth, texel0Idx / u_edgeDataTextureWidth);
  ivec2 edgeTexCoord1 = ivec2(texel1Idx % u_edgeDataTextureWidth, texel1Idx / u_edgeDataTextureWidth);
  vec4 edgeData0 = texelFetch(u_edgeDataTexture, edgeTexCoord0, 0);
  vec4 edgeData1 = texelFetch(u_edgeDataTexture, edgeTexCoord1, 0);

  // Unpack edge data
  int srcIdx = int(edgeData0.x);
  int tgtIdx = int(edgeData0.y);
  float thickness = edgeData0.z;
  // edgeData0.w is reserved
  float headLengthRatio = edgeData1.x;
  float tailLengthRatio = edgeData1.y;
  int pathId = int(edgeData1.z);  // Path type for multi-path support
  float baseFontSize = a_baseFontSize;

  // -------------------------------------------------------------------------
  // Fetch path attributes from edge attribute texture
  // -------------------------------------------------------------------------
  // Note: The fetch code uses 'edgeIdx' variable, so we set it to the attribute texture index
  {
    int edgeIdx = int(a_edgeAttrIndex);  // Use attribute texture index for path attributes
`).concat(m.fetchCode,`
`).concat(m.varyingAssignments,`
  }

  // -------------------------------------------------------------------------
  // Fetch node data from node texture (geometry texel + rotation-flags texel)
  // -------------------------------------------------------------------------
  vec4 srcNodeData = readNodeData(u_nodeDataTexture, u_nodeDataTextureWidth, srcIdx);
  vec4 tgtNodeData = readNodeData(u_nodeDataTexture, u_nodeDataTextureWidth, tgtIdx);

  vec2 source = srcNodeData.xy;
  vec2 target = tgtNodeData.xy;
  float sourceSize = srcNodeData.z;
  float targetSize = tgtNodeData.z;
  v_sourceNodeSize = sourceSize;
  v_targetNodeSize = targetSize;
  float charTextOffset = a_charMetrics.x;
  float charAdvance = a_charMetrics.y;
  float totalTextWidth = a_charMetrics.z;
  float positionMode = a_charMetrics.w;
  vec2 charSize = a_charDims.xy;
  vec2 charOffset = a_charDims.zw;
  float margin = a_labelParams.x;

  // -------------------------------------------------------------------------
  // Compute pixel-to-graph conversion (for fixed font size mode)
  // -------------------------------------------------------------------------
  // This converts screen pixels to graph units such that N pixels on screen
  // becomes N pixels regardless of zoom level.
  // matrixScaleX is how much the matrix scales graph units to clip space
  float matrixScaleX = length(vec2(u_matrix[0][0], u_matrix[1][0]));
  float pixelToGraph = 2.0 / (matrixScaleX * u_resolution.x);

  // -------------------------------------------------------------------------
  // Step 1: Convert thickness to WebGL units
  // -------------------------------------------------------------------------
  float webGLThickness = thickness * u_correctionRatio / u_sizeRatio;

  // -------------------------------------------------------------------------
  // Step 2: Compute body bounds (truncated at node boundaries + extremities)
  // -------------------------------------------------------------------------
  vec4 edgeClamp = readFrameTexel(u_edgeFrameTexture, u_edgeFrameTextureWidth, edgeIdx);
  vec3 bodyBounds = computeEdgeLabelBodyBounds(
    edgeClamp.x, edgeClamp.y, edgeClamp.w,
    webGLThickness, headLengthRatio, tailLengthRatio
  );
  float bodyStartDist = bodyBounds.x;
  float bodyEndDist = bodyBounds.y;
  float bodyLength = bodyBounds.z;

  // -------------------------------------------------------------------------
  // Step 3: Compute font scale and text dimensions
  // -------------------------------------------------------------------------
  // Font size modes:
  // - "fixed": Constant pixel size regardless of zoom, using pixelToGraph conversion
  // - "scaled": Scales with zoom using zoomToSizeRatioFunction
  `).concat(c?`// Scaled mode: font scales with zoom
  float fontScale = baseFontSize / ATLAS_FONT_SIZE * u_zoomSizeRatio;
  // Convert glyph-unit metrics to WebGL units (scales with zoom)
  float textWidthWebGL = totalTextWidth * fontScale * u_correctionRatio / u_sizeRatio;
  float charOffsetWebGL = charTextOffset * fontScale * u_correctionRatio / u_sizeRatio;
  float charAdvanceWebGL = charAdvance * fontScale * u_correctionRatio / u_sizeRatio;`:`// Fixed mode: font stays constant in screen pixels
  float fontScale = baseFontSize / ATLAS_FONT_SIZE;
  // Convert glyph-unit metrics to graph units using pixelToGraph (zoom-independent)
  float textWidthWebGL = totalTextWidth * fontScale * pixelToGraph;
  float charOffsetWebGL = charTextOffset * fontScale * pixelToGraph;
  float charAdvanceWebGL = charAdvance * fontScale * pixelToGraph;`,`

  // Font scale varying for fragment shader gamma scaling.
  // Ratio of rendered font size to atlas font size \u2014 used to tighten the
  // anti-aliasing band for large labels so they stay sharp.
  v_fontScale = fontScale;

  // -------------------------------------------------------------------------
  // Step 4: Alpha modifier from how much of the label fits in the body
  // -------------------------------------------------------------------------
  float alphaModifier = computeEdgeLabelAlpha(bodyLength, textWidthWebGL);

  // -------------------------------------------------------------------------
  // Step 5: Compute character center offset (truncation check moved to after curvature adjustment)
  // -------------------------------------------------------------------------
  // Body center in arc distance
  float bodyCenterDist = (bodyStartDist + bodyEndDist) * 0.5;

  float centerT = queryPathTAtDistance(pathId, bodyCenterDist, source, target);
  float screenDir = computeEdgeLabelScreenDir(pathId, centerT, source, target, u_matrix);

  // Reversed labels lay their characters out from target to source
  float readingSign = `).concat(h?"screenDir":"1.0",`;

  // Character center position relative to label center (on centerline, before curvature adjustment)
  float charCenterOffset = readingSign * (charOffsetWebGL + charAdvanceWebGL * 0.5 - textWidthWebGL * 0.5);

  // -------------------------------------------------------------------------
  // Step 6: Compute perpendicular offset based on position mode
  // -------------------------------------------------------------------------
  // Position modes: 0=over, 1=above, 2=below, 3=auto
  // Needed early for curvature-adaptive character spacing in Step 7
  float halfThickness = webGLThickness * 0.5;
  `).concat(c?`// Scaled mode: margin and text height scale with zoom (same factor as font)
  float marginWebGL = margin * u_zoomSizeRatio * u_correctionRatio / u_sizeRatio;
  float halfTextHeight = baseFontSize * 0.35 * u_zoomSizeRatio * u_correctionRatio / u_sizeRatio;`:`// Fixed mode: margin and text height stay constant in screen pixels
  float marginWebGL = margin * pixelToGraph;
  float halfTextHeight = baseFontSize * 0.35 * pixelToGraph;`,`
  float perpOffset = computeEdgeLabelPerpOffset(
    positionMode, halfThickness, marginWebGL, halfTextHeight, readingSign, screenDir
  );

  // -------------------------------------------------------------------------
  // Step 7: Position character on path using offset path traversal
  // -------------------------------------------------------------------------
  // For "over" mode (perpOffset = 0), use simple centerline placement
  // For above/below modes, walk along the offset path to find correct position
  float charT;

  if (perpOffset == 0.0) {
    // Simple case: place on centerline
    float charArcDist = bodyCenterDist + charCenterOffset;
    charT = queryPathTAtDistance(pathId, charArcDist, source, target);
  } else {
    // Offset path traversal: walk along the offset curve to find character position
    // This ensures even character spacing regardless of curvature

    `).concat(f?`// -----------------------------------------------------------------------
    // Corner skip setup for step/taxi edges with above/below labels
    // -----------------------------------------------------------------------
    // At concave corners (inner side of the bend), characters would bunch up
    // because the offset path has near-zero arc length. We detect corner
    // crossings during the offset path traversal and add skip distance.

    // Get corner t values and concavity
    vec2 cornerTs = queryGetCornerTs(pathId, source, target);
    vec2 concavity = queryGetCornerConcavity(pathId, source, target, perpOffset);

    // Skip distance in graph units, proportional to on-screen font size
    // For fixed mode: use pixelToGraph so gap stays constant regardless of zoom
    // For scaled mode: use the same conversion as text width
    `.concat(c?"float skipDistGraph = STEP_INNER_CORNER_SKIP_FACTOR * baseFontSize * u_zoomSizeRatio * u_correctionRatio / u_sizeRatio;":"float skipDistGraph = STEP_INNER_CORNER_SKIP_FACTOR * baseFontSize * pixelToGraph;",`

    // Corner t values for detecting crossings during traversal
    float corner1T = cornerTs.x;
    float corner2T = cornerTs.y;
    bool corner1IsConcave = concavity.x > 0.5;
    bool corner2IsConcave = concavity.y > 0.5;`):"",`

    // Target distance along offset path from center
    float targetOffsetDist = abs(charCenterOffset);

    // Handle center character (charCenterOffset \u2248 0) - no search needed
    if (targetOffsetDist < 0.0001) {
      charT = centerT;
    } else {
      vec2 centerPos = queryPathPosition(pathId, centerT, source, target);
      vec2 centerNormal = queryPathNormal(pathId, centerT, source, target);
      vec2 offsetCenter = centerPos + centerNormal * perpOffset;

      float searchDir = charCenterOffset > 0.0 ? 1.0 : -1.0;

      // Search bounds (t values for body start and end)
      float tBodyStart = queryPathTAtDistance(pathId, bodyStartDist, source, target);
      float tBodyEnd = queryPathTAtDistance(pathId, bodyEndDist, source, target);

      // Walk along offset path to find character position
      float accumDist = 0.0;
      vec2 prevOffsetPos = offsetCenter;
      float prevT = centerT;
      float foundT = centerT;

      // Search range depends on direction
      float tSearchEnd = searchDir > 0.0 ? tBodyEnd : tBodyStart;

      `).concat(f?`// Track which concave corners we've crossed to add skip distance
      bool crossedCorner1 = false;
      bool crossedCorner2 = false;
      float effectiveTargetDist = targetOffsetDist;`:"",`

      const int STEPS = 32;
      for (int i = 1; i <= STEPS; i++) {
        // Step along centerline t, from center toward target
        float stepT = centerT + searchDir * float(i) * abs(tSearchEnd - centerT) / float(STEPS);

        `).concat(f?`// Check for concave corner crossings and add skip distance
        // Corner 1 crossing check
        if (corner1IsConcave && !crossedCorner1) {
          bool crossingCorner1 = (searchDir > 0.0)
            ? (prevT < corner1T && stepT >= corner1T)
            : (prevT > corner1T && stepT <= corner1T);
          if (crossingCorner1) {
            crossedCorner1 = true;
            effectiveTargetDist += skipDistGraph;
          }
        }

        // Corner 2 crossing check
        if (corner2IsConcave && !crossedCorner2) {
          bool crossingCorner2 = (searchDir > 0.0)
            ? (prevT < corner2T && stepT >= corner2T)
            : (prevT > corner2T && stepT <= corner2T);
          if (crossingCorner2) {
            crossedCorner2 = true;
            effectiveTargetDist += skipDistGraph;
          }
        }`:"",`

        // Compute offset position at this t
        vec2 stepPos = queryPathPosition(pathId, stepT, source, target);
        vec2 stepNormal = queryPathNormal(pathId, stepT, source, target);
        vec2 offsetPos = stepPos + stepNormal * perpOffset;

        // Distance along offset path
        float segDist = length(offsetPos - prevOffsetPos);

        `).concat(f?`if (accumDist + segDist >= effectiveTargetDist) {
          // Interpolate within segment to find exact t
          float remaining = effectiveTargetDist - accumDist;
          float segT = remaining / max(segDist, 0.0001);
          foundT = mix(prevT, stepT, segT);
          break;
        }`:`if (accumDist + segDist >= targetOffsetDist) {
          // Interpolate within segment to find exact t
          float remaining = targetOffsetDist - accumDist;
          float segT = remaining / max(segDist, 0.0001);
          foundT = mix(prevT, stepT, segT);
          break;
        }`,`

        accumDist += segDist;
        prevOffsetPos = offsetPos;
        prevT = stepT;
        // Update foundT to last valid position in case loop exhausts without finding target
        foundT = stepT;
      }

      charT = foundT;
    }
  }

  // Get position and tangent at final character position
  vec2 pathPos = queryPathPosition(pathId, charT, source, target);
  vec2 tangent = queryPathTangent(pathId, charT, source, target);

  // Compute perpendicular direction (90 degrees from tangent)
  vec2 perpDir = vec2(-tangent.y, tangent.x);

  // Apply perpendicular offset to path position
  vec2 offsetPathPos = pathPos + perpDir * perpOffset;

  // -------------------------------------------------------------------------
  // Step 8: Build character quad
  // -------------------------------------------------------------------------
  // Character size in screen pixels
  vec2 charSizePixels = charSize * fontScale;

  // Character offset from origin to the atlas region's top-left corner.
  // bearingX/bearingY already include the SDF buffer.
  vec2 charOffsetPixels = charOffset * fontScale;

  // The character's local X offset from pathPos (which is at character center)
  float charLocalX = -charAdvance * 0.5 * fontScale;

  // Build quad position:
  // - Start at character origin (charLocalX on X axis, 0 on Y axis = baseline)
  // - Add bearing offset to get to atlas region corner
  // - Add quad corner * size to get vertex position
  vec2 quadPos;
  quadPos.x = charLocalX + charOffsetPixels.x + a_quadCorner.x * charSizePixels.x;
  // charOffset.y = -bearingY (negated), so -charOffsetPixels.y = bearingY * fontScale
  // (distance from baseline to atlas region top, positive = upward)
  // Quad corner (0,0) = bottom-left, (1,1) = top-right
  quadPos.y = -charOffsetPixels.y - charSizePixels.y * (1.0 - a_quadCorner.y);

  // Center vertically on the path by offsetting by half the visual text height
  // VERTICAL_CENTER_RATIO is the distance from baseline to visual center as a ratio of atlas font size
  float verticalCenterOffset = VERTICAL_CENTER_RATIO * ATLAS_FONT_SIZE * fontScale;
  quadPos.y -= verticalCenterOffset;

  // -------------------------------------------------------------------------
  // Step 9: Rotate quad to align with tangent
  // -------------------------------------------------------------------------
  // Rotation matrix from the reading direction
  // readingDir = (cos(angle), sin(angle)), so we can build rotation directly
  vec2 readingDir = tangent * readingSign;
  mat2 rotation = mat2(readingDir.x, readingDir.y, -readingDir.y, readingDir.x);

  // Convert pixel offset to WebGL units for rotation
  `).concat(c?"vec2 quadPosWebGL = quadPos * u_correctionRatio / u_sizeRatio; // Scaled mode":"vec2 quadPosWebGL = quadPos * pixelToGraph; // Fixed mode: use pixelToGraph for zoom-independent size",`

  // Rotate around character center on path
  vec2 rotatedOffset = rotation * quadPosWebGL;

  // Final position in graph space (using offset path position for above/below modes)
  vec2 worldPos = offsetPathPos + rotatedOffset;

  // -------------------------------------------------------------------------
  // Step 10: Transform to clip space
  // -------------------------------------------------------------------------
  vec3 clipPos = u_matrix * vec3(worldPos, 1.0);
  gl_Position = vec4(clipPos.xy, 0.0, 1.0);

  // -------------------------------------------------------------------------
  // Step 11: Texture coordinates
  // -------------------------------------------------------------------------
  // Flip Y for texture coordinates (texture Y goes down, quad Y goes up)
  vec2 texCorner = vec2(a_quadCorner.x, 1.0 - a_quadCorner.y);
  v_texCoord = (a_texCoords.xy + texCorner * a_texCoords.zw) / u_atlasSize;

  // -------------------------------------------------------------------------
  // Step 12: Pass color, border color, and alpha modifier
  // -------------------------------------------------------------------------
  v_color = a_color;
  v_color.a *= bias;
`).concat(t?`  v_borderColor = a_borderColor;
  v_borderColor.a *= bias;
  v_positionMode = positionMode;`:"",`
  v_alphaModifier = alphaModifier;

  // -------------------------------------------------------------------------
  // Step 13: Compute edge fade for soft truncation
  // -------------------------------------------------------------------------
  // Convert fade width from pixels to WebGL units
  `).concat(c?"float fadeWidthWebGL = FADE_WIDTH_PIXELS * u_correctionRatio / u_sizeRatio;":"float fadeWidthWebGL = FADE_WIDTH_PIXELS * pixelToGraph;",`

  // Compute the arc position of THIS VERTEX (not just character center)
  // The quad extends from charCenter - advance/2 to charCenter + advance/2
  // a_quadCorner.x is 0 for left edge, 1 for right edge
  float vertexLocalOffset = readingSign * (a_quadCorner.x - 0.5) * charAdvanceWebGL;
  float vertexArcOffset = charCenterOffset + vertexLocalOffset;

  // Compute distance from body edges (positive = inside body, negative = outside)
  float halfBody = bodyLength * 0.5;
  float distFromStart = vertexArcOffset + halfBody;  // Distance from body start edge
  float distFromEnd = halfBody - vertexArcOffset;    // Distance from body end edge
  float distFromEdge = min(distFromStart, distFromEnd);

  // Compute fade: 0 = fully visible (deep inside body), 1 = fully faded (at body edge)
  // Fade goes from 0 (at 2*fadeWidth inside) to 1 (at body edge)
  // This ensures text is fully transparent before reaching extremities
  v_edgeFade = 1.0 - smoothstep(0.0, fadeWidthWebGL * 2.0, distFromEdge);
}
`);return v}function Xh(){var a=arguments.length>0&&arguments[0]!==void 0?arguments[0]:{},n=a.hasBorder,e=n===void 0?!1:n,t=`#version 300 es
precision highp float;

in vec2 v_texCoord;
in vec4 v_color;
`.concat(e?"in vec4 v_borderColor;":"",`
in float v_edgeFade;  // 0 = fully visible, 1 = fully faded
in float v_alphaModifier;  // 0-1 based on label visibility ratio
in float v_fontScale;  // Ratio of rendered font size to atlas font size
`).concat(e?"in float v_positionMode;  // Position mode (0=over, 1=above, 2=below, 3=auto)":"",`

uniform sampler2D u_atlas;
uniform float u_gamma;
uniform float u_sdfBuffer;
uniform float u_pixelRatio;
`).concat(e?"uniform float u_borderWidth;  // Border width in SDF units (normalized)":"",`

// Fragment output (single target - picking handled via separate pass)
out vec4 fragColor;

void main() {
  #ifdef PICKING_MODE
    // Edge labels are not pickable - discard all fragments in picking mode
    fragColor = vec4(0.0);
    discard;
  #else
  // SDF stores normalized distance: 0.5 = on edge, >0.5 = inside glyph
  float sdfValue = texture(u_atlas, v_texCoord).a;

  // Edge threshold accounting for SDF buffer padding
  float edge = 1.0 - u_sdfBuffer;

  // Scale gamma inversely with font scale so small labels get a wider AA band
  // (smoother) and large labels get a tighter band (sharper).
  float aaWidth = u_gamma / (u_pixelRatio * v_fontScale);

  // Apply edge fade for soft truncation at body boundaries
  // Also apply visibility-based alpha modifier for short edge labels
  float edgeAlpha = (1.0 - v_edgeFade) * v_alphaModifier;

`).concat(e?`  // Fill alpha: fully opaque inside the glyph
  float fillAlpha = smoothstep(edge - aaWidth, edge + aaWidth, sdfValue);

  // Only apply border for "over" position mode (v_positionMode == 0.0)
  // Labels positioned above/below/auto don't overlap the edge line and don't need borders
  if (v_positionMode < 0.5) {
    // Border rendering: compute alpha for both fill and border regions
    // Border extends from (edge - borderWidth) to edge
    float borderEdge = edge - u_borderWidth;

    // Border alpha: opaque in the border region (between borderEdge and edge)
    float borderAlpha = smoothstep(borderEdge - aaWidth, borderEdge + aaWidth, sdfValue);

    // Composite: fill on top of border
    // Border is visible where borderAlpha > 0 but fillAlpha < 1
    vec3 borderColorPremult = v_borderColor.rgb * v_borderColor.a * borderAlpha * edgeAlpha;
    vec3 fillColorPremult = v_color.rgb * v_color.a * fillAlpha * edgeAlpha;

    // Blend fill over border (fill replaces border where fill is opaque)
    float finalBorderAlpha = borderAlpha * (1.0 - fillAlpha);
    vec3 finalColor = fillColorPremult + v_borderColor.rgb * v_borderColor.a * finalBorderAlpha * edgeAlpha;
    float finalAlpha = (v_color.a * fillAlpha + v_borderColor.a * finalBorderAlpha) * edgeAlpha;

    fragColor = vec4(finalColor, finalAlpha);
  } else {
    // No border for above/below/auto positions - simple text rendering
    float finalAlpha = v_color.a * fillAlpha * edgeAlpha;
    fragColor = vec4(v_color.rgb * finalAlpha, finalAlpha);
  }`:`  // Smooth transition from transparent to opaque at glyph edge
  float alpha = smoothstep(edge - aaWidth, edge + aaWidth, sdfValue);

  // Premultiplied alpha output
  float finalAlpha = v_color.a * alpha * edgeAlpha;
  fragColor = vec4(v_color.rgb * finalAlpha, finalAlpha);`,`
  #endif
}
`);return t}function Yh(a){var n=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!1,e=arguments.length>2&&arguments[2]!==void 0?arguments[2]:"fixed",t=["u_matrix","u_sizeRatio","u_correctionRatio","u_pixelRatio","u_cameraAngle","u_sdfBufferPixels","u_resolution","u_atlasSize","u_atlas","u_gamma","u_sdfBuffer","u_nodeDataTexture","u_nodeDataTextureWidth","u_edgeDataTexture","u_edgeDataTextureWidth","u_edgeFrameTexture","u_edgeFrameTextureWidth","u_edgeAttributeTexture","u_edgeAttributeTextureWidth","u_edgeAttributeTexelsPerEdge"];e==="scaled"&&t.push("u_zoomSizeRatio"),n&&t.push("u_borderWidth");var r=O(a),i;try{for(r.s();!(i=r.n()).done;){var o=i.value,s=O(o.uniforms),l;try{for(s.s();!(l=s.n()).done;){var u=l.value;t.includes(u.name)||t.push(u.name)}}catch(d){s.e(d)}finally{s.f()}}}catch(d){r.e(d)}finally{r.f()}return t}function Kh(a){var n=a.hasBorder,e=n===void 0?!1:n,t=a.fontSizeMode,r=t===void 0?"fixed":t;return{vertexShader:jh(a),fragmentShader:Xh({hasBorder:e}),uniforms:Yh(a.paths,e,r)}}var Zh=new Map;function Qh(a){switch(a){case"over":return 0;case"above":return 1;case"below":return 2;case"auto":return 3;default:return 0}}function Jh(a,n,e,t){var r=t.color,i=t.margin,o=t.textBorder,s=as(t),l=s.paths,u=s.fontSizeMode,d=s.minVisibilityThreshold,h=s.fullVisibilityThreshold,c=s.keepUpright,f=!!o,g=Kh({paths:l,hasBorder:f,fontSizeMode:u,minVisibilityThreshold:d,fullVisibilityThreshold:h,keepUpright:c}),y=(function(m){function v(p,b,T){var _;te(this,v),_=me(this,v,[p,b,T]),D(_,"atlasTexture",null),D(_,"atlasNeedsUpdate",!1),D(_,"refreshTimeout",null),D(_,"labelGlyphCache",new Map),D(_,"edgeAttributeTexture",null);var E=At();if(_.attributeLayout=$e([].concat(Q(l),[E])),_.attrDescriptors=Aa([].concat(Q(l),[E]),_.attributeLayout),_.edgeAttributeTexture=new wa(p,_.attributeLayout),_.packedAttributeData=new Float32Array(_.attributeLayout.floatsPerItem),_.atlasManager=new Rt,_.gamma=.025,_.sdfBuffer=Je.cutoff,_.atlasTexture=p.createTexture(),!_.atlasTexture)throw new Error("EdgeLabelProgram: failed to create atlas texture");p.bindTexture(p.TEXTURE_2D,_.atlasTexture),p.texParameteri(p.TEXTURE_2D,p.TEXTURE_WRAP_S,p.CLAMP_TO_EDGE),p.texParameteri(p.TEXTURE_2D,p.TEXTURE_WRAP_T,p.CLAMP_TO_EDGE),p.texParameteri(p.TEXTURE_2D,p.TEXTURE_MIN_FILTER,p.LINEAR),p.texParameteri(p.TEXTURE_2D,p.TEXTURE_MAG_FILTER,p.LINEAR),p.bindTexture(p.TEXTURE_2D,null),_.atlasManager.on(Rt.ATLAS_UPDATED_EVENT,function(){_.atlasNeedsUpdate=!0,_.refreshTimeout!==null&&clearTimeout(_.refreshTimeout),_.refreshTimeout=setTimeout(function(){_.refreshTimeout=null,_.renderer.refresh()},0)});var A={family:"sans-serif",weight:"normal",style:"normal"};return _.defaultFontKey=_.atlasManager.registerFont(A),_}return ye(v,m),ne(v,[{key:"getDefinition",value:function(){var b=WebGL2RenderingContext,T=b.FLOAT,_=b.UNSIGNED_BYTE,E=b.TRIANGLE_STRIP,A=new Set,w=[],S=O(l),C;try{for(S.s();!(C=S.n()).done;){var G=C.value,L=O(G.attributes),N;try{for(L.s();!(N=L.n()).done;){var k=N.value,I=k.name.startsWith("a_")?k.name:"a_".concat(k.name);A.has(I)||(A.add(I),w.push({name:I,size:k.size,type:k.type}))}}catch(W){L.e(W)}finally{L.f()}}}catch(W){S.e(W)}finally{S.f()}return{VERTICES:4,VERTEX_SHADER_SOURCE:g.vertexShader,FRAGMENT_SHADER_SOURCE:g.fragmentShader,METHOD:E,UNIFORMS:g.uniforms,ATTRIBUTES:[{name:"a_edgeIndex",size:1,type:T},{name:"a_edgeAttrIndex",size:1,type:T},{name:"a_baseFontSize",size:1,type:T},{name:"a_charMetrics",size:4,type:T},{name:"a_charDims",size:4,type:T},{name:"a_texCoords",size:4,type:T},{name:"a_labelParams",size:2,type:T},{name:"a_color",size:4,type:_,normalized:!0}].concat(Q(f?[{name:"a_borderColor",size:4,type:_,normalized:!0}]:[]),Q(w.filter(function(W){return!["a_curvature","curvature"].includes(W.name)}))),CONSTANT_ATTRIBUTES:[{name:"a_quadCorner",size:2,type:T}],CONSTANT_DATA:[[0,0],[1,0],[0,1],[1,1]]}}},{key:"prepareLabelGlyphs",value:function(b,T){if(T.hidden||!T.text){this.labelGlyphCache.delete(b);return}var _=T.text,E=T.fontKey||this.defaultFontKey;this.atlasManager.ensureGlyphs(_,E);var A=[],w=[],S=0,C=O(_),G;try{for(C.s();!(G=C.n()).done;){var L=G.value,N=L.codePointAt(0);if(N===void 0){A.push(void 0),w.push(S);continue}var k=this.atlasManager.getGlyph(N,E);A.push(k),w.push(S),k&&(S+=k.advance)}}catch(I){C.e(I)}finally{C.f()}this.labelGlyphCache.set(b,{glyphs:A,xOffsets:w,totalWidth:S})}},{key:"processCharacter",value:function(b,T,_,E){var A,w,S,C=this.floats,G=this.STRIDE,L=b*G,N=this.labelGlyphCache.get(T.parentKey);if(!N||!N.glyphs[E]){for(var k=0;k<G;k++)C[L+k]=0;return}var I=N.glyphs[E],W=N.xOffsets[E],F=v.labelColor,x=F&&re(F)==="object"&&"color"in F&&F.color?F.color:T.color,P=Be(x),U=L;C[U++]=T.edgeIndex,C[U++]=(A=(w=this.edgeAttributeTexture)===null||w===void 0?void 0:w.getIndex(T.parentKey))!==null&&A!==void 0?A:0,C[U++]=T.size,C[U++]=W,C[U++]=I.advance,C[U++]=N.totalWidth,C[U++]=Qh(T.position),C[U++]=I.atlasWidth,C[U++]=I.atlasHeight,C[U++]=I.bearingX,C[U++]=-I.bearingY,C[U++]=I.atlasX,C[U++]=I.atlasY,C[U++]=I.atlasWidth,C[U++]=I.atlasHeight;var z=(S=v.labelMargin)!==null&&S!==void 0?S:T.margin;if(C[U++]=z,C[U++]=0,C[U++]=P,f&&o){var R;typeof o.color=="string"?R=o.color:R=o.color.color||"#ffffff",C[U++]=Be(R)}var j=new Set,q=O(l),Z;try{for(q.s();!(Z=q.n()).done;){var Se=Z.value,de=O(Se.attributes),K;try{for(de.s();!(K=de.n()).done;){var Ke=K.value,De=Ke.name.startsWith("a_")?Ke.name.slice(2):Ke.name;if(De!=="curvature"&&!j.has(De)){j.add(De);for(var _t=0;_t<Ke.size;_t++)C[U++]=0}}}catch(Ve){de.e(Ve)}finally{de.f()}}}catch(Ve){q.e(Ve)}finally{q.f()}}},{key:"processEdgeLabel",value:function(b,T,_){if(this.prepareLabelGlyphs(b,_),this.edgeAttributeTexture&&!_.hidden&&_.text){this.edgeAttributeTexture.allocate(b);var E=this.packedAttributeData;Da(this.attrDescriptors,_.edgeAttributes,E,"",Zh,0),this.edgeAttributeTexture.updateAllAttributes(b,E)}return Ee(v,"processLabel",this,3)([b,T,_])}},{key:"updateAtlasTexture",value:function(){if(this.atlasNeedsUpdate){var b=this.normalProgram.gl,T=this.atlasManager.getTextures();if(T.length!==0){var _=T[0];b.bindTexture(b.TEXTURE_2D,this.atlasTexture),b.texImage2D(b.TEXTURE_2D,0,b.RGBA,_.width,_.height,0,b.RGBA,b.UNSIGNED_BYTE,_.data),b.bindTexture(b.TEXTURE_2D,null),this.atlasNeedsUpdate=!1}}}},{key:"setUniforms",value:function(b,T){var _=T.gl,E=T.uniformLocations,A=this.atlasManager.getTextures(),w=A.length>0?[A[0].width,A[0].height]:[1,1];if(_.uniformMatrix3fv(E.u_matrix,!1,b.matrix),_.uniform1f(E.u_sizeRatio,b.sizeRatio),_.uniform1f(E.u_correctionRatio,b.correctionRatio),_.uniform1f(E.u_pixelRatio,b.pixelRatio),_.uniform1f(E.u_cameraAngle,b.cameraAngle),_.uniform1f(E.u_sdfBufferPixels,Je.buffer),_.uniform2f(E.u_resolution,b.width,b.height),_.uniform2f(E.u_atlasSize,w[0],w[1]),_.uniform1f(E.u_gamma,this.gamma),_.uniform1f(E.u_sdfBuffer,this.sdfBuffer),_.activeTexture(_.TEXTURE0),_.bindTexture(_.TEXTURE_2D,this.atlasTexture),_.uniform1i(E.u_atlas,0),E.u_nodeDataTexture!==void 0&&_.uniform1i(E.u_nodeDataTexture,b.nodeDataTextureUnit),E.u_nodeDataTextureWidth!==void 0&&_.uniform1i(E.u_nodeDataTextureWidth,b.nodeDataTextureWidth),E.u_edgeDataTexture!==void 0&&_.uniform1i(E.u_edgeDataTexture,b.edgeDataTextureUnit),E.u_edgeDataTextureWidth!==void 0&&_.uniform1i(E.u_edgeDataTextureWidth,b.edgeDataTextureWidth),E.u_edgeFrameTexture!==void 0&&_.uniform1i(E.u_edgeFrameTexture,b.edgeFrameTextureUnit),E.u_edgeFrameTextureWidth!==void 0&&_.uniform1i(E.u_edgeFrameTextureWidth,b.edgeFrameTextureWidth),f&&o&&E.u_borderWidth!==void 0){var S=o.width/Je.buffer*this.sdfBuffer;_.uniform1f(E.u_borderWidth,S)}if(this.edgeAttributeTexture&&E.u_edgeAttributeTexture!==void 0&&(this.edgeAttributeTexture.bind(mt),_.uniform1i(E.u_edgeAttributeTexture,mt),_.uniform1i(E.u_edgeAttributeTextureWidth,this.edgeAttributeTexture.getTextureWidth()),_.uniform1i(E.u_edgeAttributeTexelsPerEdge,this.edgeAttributeTexture.getTexelsPerItem())),u==="scaled"&&E.u_zoomSizeRatio!==void 0){var C=this.renderer.getSetting("zoomToSizeRatioFunction"),G=1/C(b.zoomRatio);_.uniform1f(E.u_zoomSizeRatio,G)}}},{key:"renderProgram",value:function(b,T){this.updateAtlasTexture(),this.atlasManager.hasPendingGlyphs()&&(this.atlasManager.flush(),this.updateAtlasTexture()),this.edgeAttributeTexture&&this.edgeAttributeTexture.upload(),Ee(v,"renderProgram",this,3)([b,T])}},{key:"registerFont",value:function(b){var T=arguments.length>1&&arguments[1]!==void 0?arguments[1]:"normal",_=arguments.length>2&&arguments[2]!==void 0?arguments[2]:"normal";return this.atlasManager.registerFont({family:b,weight:T,style:_})}},{key:"getAtlasManager",value:function(){return this.atlasManager}},{key:"ensureGlyphsReady",value:function(b,T){var _=T||this.defaultFontKey,E=O(b),A;try{for(E.s();!(A=E.n()).done;){var w=A.value;this.atlasManager.ensureGlyphs(w,_)}}catch(S){E.e(S)}finally{E.f()}this.atlasManager.flush()}},{key:"measureLabelAtlasWidth",value:function(b,T){var _=T||this.defaultFontKey;this.atlasManager.ensureGlyphs(b,_),this.atlasManager.hasPendingGlyphs()&&this.atlasManager.flush();var E=0,A=O(b),w;try{for(A.s();!(w=A.n()).done;){var S=w.value,C=S.codePointAt(0);if(C!==void 0){var G=this.atlasManager.getGlyph(C,_);G&&(E+=G.advance)}}}catch(L){A.e(L)}finally{A.f()}return E}},{key:"measureLabel",value:function(b,T,_){var E=this.measureLabelAtlasWidth(b,_),A=T/Je.fontSize;return{width:E*A,height:T,textHeight:T}}},{key:"kill",value:function(){var b=this.normalProgram.gl;this.refreshTimeout!==null&&(clearTimeout(this.refreshTimeout),this.refreshTimeout=null),this.atlasTexture&&(b.deleteTexture(this.atlasTexture),this.atlasTexture=null),this.edgeAttributeTexture&&(this.edgeAttributeTexture.kill(),this.edgeAttributeTexture=null),this.atlasManager.destroy(),this.labelGlyphCache.clear(),Ee(v,"kill",this,3)([])}}])})(Xo);return D(y,"labelColor",r),D(y,"labelMargin",i),new y(a,n,e)}function ec(){var a=`
// No extremity - always returns positive (outside)
float extremity_none(vec2 uv, float lengthRatio, float widthRatio) {
  return 1.0;
}
`;return{name:"none",glsl:a,length:0,widthFactor:1,margin:0,uniforms:[],attributes:[]}}function rs(a,n,e,t,r,i,o){var s,l,u=Jo(t),d=u.paths,h=u.layers,c=u.defaultHead,f=u.defaultTail,g=[ec()].concat(Q(u.extremities)),y={},m={};d.forEach(function(L,N){return y[L.name]=N}),g.forEach(function(L,N){return m[L.name]=N});var v=(s=m[c])!==null&&s!==void 0?s:0,p=(l=m[f])!==null&&l!==void 0?l:0,b=null,T=$e([].concat(Q(d),Q(h))),_=(function(L){function N(k,I,W){var F;te(this,N),b||(b=Go({paths:d,extremities:g,layers:h,antialias:r})),F=me(this,N,[k,I,W]),D(F,"layerLifecycles",new Map),D(F,"needsShaderRegeneration",!1),D(F,"edgeAttributeTexture",null),D(F,"layout",T),D(F,"attrDescriptors",[]),D(F,"lifecycleIndexOffset",d.length),F._pickingBuffer=I,F.edgeAttributeTexture=new wa(k,F.layout),F.packedAttributeData=new Float32Array(F.layout.floatsPerItem),h.forEach(function(P,U){if(P.lifecycle){var z={gl:k,renderer:{refresh:function(){return W.refresh()}},getUniformLocation:function(j){return k.getUniformLocation(F.normalProgram.program,j)},requestShaderRegeneration:function(){F.needsShaderRegeneration=!0},requestRefresh:function(){W.refresh()}};F.layerLifecycles.set(U,P.lifecycle(z))}}),F.layerLifecycles.forEach(function(P){var U;return(U=P.init)===null||U===void 0?void 0:U.call(P)});var x=new Map;return F.layerLifecycles.forEach(function(P,U){P.getAttributeData&&x.set(d.length+U,P)}),F.attrDescriptors=Aa([].concat(Q(d),Q(h)),F.layout,x),F}return ye(N,L),ne(N,[{key:"getAttributeTexture",value:function(){return this.edgeAttributeTexture}},{key:"resolveEdgeIds",value:function(I,W,F){var x=I,P=0,U=v,z=p,R=W?x.selfLoopPath:F&&x.parallelPath?x.parallelPath:x.path;R&&y[R]!==void 0&&(P=y[R]),x.head&&x.head!=="none"&&m[x.head]!==void 0&&(U=m[x.head]),x.tail&&x.tail!=="none"&&m[x.tail]!==void 0&&(z=m[x.tail]);var j=g[U],q=g[z];return{pathId:P,headId:U,tailId:z,headLengthRatio:ot(j.length)?0:j.length,tailLengthRatio:ot(q.length)?0:q.length}}},{key:"getDefinition",value:function(){var I=WebGL2RenderingContext,W=I.TRIANGLE_STRIP,F=W,x=b;return{VERTICES:x.verticesPerEdge,VERTEX_SHADER_SOURCE:x.vertexShader,FRAGMENT_SHADER_SOURCE:x.fragmentShader,METHOD:F,UNIFORMS:x.uniforms,ATTRIBUTES:x.attributes,CONSTANT_ATTRIBUTES:x.constantAttributes,CONSTANT_DATA:x.constantData}}},{key:"maybeRegenerateShaders",value:function(){var I=this;if(this.needsShaderRegeneration){this.needsShaderRegeneration=!1;var W=h.map(function(j,q){var Z=I.layerLifecycles.get(q);return Z!=null&&Z.regenerate?Z.regenerate():j});b=Go({paths:d,extremities:g,layers:W,antialias:this.renderer.getSetting("antialiasEdges")});var F=this.normalProgram.gl,x=this.normalProgram,P=x.program,U=x.buffer,z=x.vertexShader,R=x.fragmentShader;F.deleteProgram(P),F.deleteBuffer(U),F.deleteShader(z),F.deleteShader(R),this.normalProgram=this.getProgramInfo("normal",F,b.vertexShader,b.fragmentShader,this._pickingBuffer)}}},{key:"process",value:function(I,W,F,x,P,U){var z=W*this.STRIDE;if(P.visibility==="hidden"||F.visibility==="hidden"||x.visibility==="hidden"){for(var R=z+this.STRIDE;z<R;z++)this.floats[z]=0;this.floats[W*this.STRIDE]=Vo;return}this.processVisibleItem(Kt(I),z,F,x,P,U)}},{key:"processVisibleItem",value:function(I,W,F,x,P,U){var z,R=this.floats,j=this.ints;R[W++]=U,R[W++]=Be(P.color),j[W++]=I,R[W++]=(z=P.opacity)!==null&&z!==void 0?z:1;var q=this.packedAttributeData;Da(this.attrDescriptors,P,q,P.color,this.layerLifecycles,this.lifecycleIndexOffset),this.edgeAttributeTexture.updateAllAttributesAtRow(U,q)}},{key:"setUniforms",value:function(I,W){var F=this,x=W.gl,P=W.uniformLocations;P.u_matrix&&x.uniformMatrix3fv(P.u_matrix,!1,I.matrix),P.u_sizeRatio&&x.uniform1f(P.u_sizeRatio,I.sizeRatio),P.u_correctionRatio&&x.uniform1f(P.u_correctionRatio,I.correctionRatio),P.u_zoomRatio&&x.uniform1f(P.u_zoomRatio,I.zoomRatio),P.u_pixelRatio&&x.uniform1f(P.u_pixelRatio,I.pixelRatio),P.u_cameraAngle&&x.uniform1f(P.u_cameraAngle,I.cameraAngle),P.u_feather&&x.uniform1f(P.u_feather,I.antiAliasingFeather),P.u_minEdgeThickness&&x.uniform1f(P.u_minEdgeThickness,I.minEdgeThickness),P.u_pickingPadding&&x.uniform1f(P.u_pickingPadding,I.edgePickingPadding),P.u_nodeDataTexture&&x.uniform1i(P.u_nodeDataTexture,I.nodeDataTextureUnit),P.u_nodeDataTextureWidth&&x.uniform1i(P.u_nodeDataTextureWidth,I.nodeDataTextureWidth),P.u_edgeDataTexture&&x.uniform1i(P.u_edgeDataTexture,I.edgeDataTextureUnit),P.u_edgeDataTextureWidth&&x.uniform1i(P.u_edgeDataTextureWidth,I.edgeDataTextureWidth),P.u_edgeFrameTexture&&x.uniform1i(P.u_edgeFrameTexture,I.edgeFrameTextureUnit),P.u_edgeFrameTextureWidth&&x.uniform1i(P.u_edgeFrameTextureWidth,I.edgeFrameTextureWidth),this.edgeAttributeTexture&&this.layout.floatsPerItem>0&&(this.edgeAttributeTexture.bind(mt),P.u_edgeAttributeTexture&&x.uniform1i(P.u_edgeAttributeTexture,mt),P.u_edgeAttributeTextureWidth&&x.uniform1i(P.u_edgeAttributeTextureWidth,this.edgeAttributeTexture.getTextureWidth()),P.u_edgeAttributeTexelsPerEdge&&x.uniform1i(P.u_edgeAttributeTexelsPerEdge,this.edgeAttributeTexture.getTexelsPerItem()));var U=new Set;d.forEach(function(z){z.uniforms.forEach(function(R){U.has(R.name)||(U.add(R.name),F.setTypedUniform(R,W))})}),g.forEach(function(z){z.uniforms.forEach(function(R){U.has(R.name)||(U.add(R.name),F.setTypedUniform(R,W))})}),h.forEach(function(z){z.uniforms.forEach(function(R){U.has(R.name)||(U.add(R.name),F.setTypedUniform(R,W))})})}},{key:"render",value:function(I,W,F){this.maybeRegenerateShaders(),Ee(N,"render",this,3)([I,W,F])}},{key:"renderProgram",value:function(I,W){this.layerLifecycles.forEach(function(F){var x;return(x=F.beforeRender)===null||x===void 0?void 0:x.call(F)}),Ee(N,"renderProgram",this,3)([I,W])}},{key:"uploadAttributeTexture",value:function(){this.edgeAttributeTexture&&this.layout.floatsPerItem>0&&this.edgeAttributeTexture.upload()}},{key:"kill",value:function(){this.layerLifecycles.forEach(function(I){var W;return(W=I.kill)===null||W===void 0?void 0:W.call(I)}),this.edgeAttributeTexture&&(this.edgeAttributeTexture.kill(),this.edgeAttributeTexture=null),Ee(N,"kill",this,3)([])}}])})(Lt),E=g[v],A=g[p],w=H({paths:d,headLengthRatio:ot(E.length)?0:E.length,tailLengthRatio:ot(A.length)?0:A.length},t.label),S=as(w),C=function(){return{labelProgram:Jh(a,null,e,w),labelBackgroundProgram:$h(a,n,e,{shaderConfig:S})}},G=new Gh(a,{paths:d,extremities:g,layers:h,nodeShapes:i,nodeLayers:o});return{edgeProgram:new _(a,null,e),createLabelPrograms:C,framePass:G}}function tc(a){return re(a)==="object"&&"uniforms"in a&&Array.isArray(a.uniforms)}function nc(a){return re(a)==="object"&&"uniforms"in a&&"attributes"in a&&"glsl"in a}function ac(a){return re(a)==="object"&&"uniforms"in a&&"attributes"in a&&"segments"in a}function rc(a){return re(a)==="object"&&"uniforms"in a&&"attributes"in a&&"length"in a}function ic(a){return re(a)==="object"&&"uniforms"in a&&"attributes"in a&&"glsl"in a}function oc(a){return re(a)==="object"&&"glsl"in a&&"name"in a&&!("uniforms"in a)}function sc(a){return re(a)==="object"&&"glsl"in a&&"name"in a&&!("uniforms"in a)}function lc(a){return re(a)==="object"&&"glsl"in a&&"name"in a&&!("uniforms"in a)}function uc(a){if(tc(a))return a;if(oc(a))return{name:a.name,glsl:a.glsl,inradiusFactor:a.inradiusFactor,uniforms:[]};throw new Error("Invalid node shape specification: ".concat(JSON.stringify(a)))}function dc(a){if(nc(a))return a;if(oo(a))return{name:a.name,glsl:a.glsl,uniforms:[],attributes:[]};throw new Error("Invalid node layer specification: ".concat(JSON.stringify(a)))}function hc(a){if(ac(a))return a;if(sc(a))return{name:a.name,glsl:a.glsl,segments:a.segments,uniforms:[],attributes:[]};throw new Error("Invalid edge path specification: ".concat(JSON.stringify(a)))}function cc(a){if(ic(a))return a;if(so(a))return{name:a.name,glsl:a.glsl,uniforms:[],attributes:[]};throw new Error("Invalid edge layer specification: ".concat(JSON.stringify(a)))}function fc(a){if(rc(a))return a;if(lc(a))return{name:a.name,glsl:a.glsl,length:a.length,widthFactor:a.widthFactor,margin:0,uniforms:[],attributes:[]};throw new Error("Invalid edge extremity specification: ".concat(JSON.stringify(a)))}function is(a){var n,e,t=(n=a?.shapes)!==null&&n!==void 0?n:xn.shapes,r=(e=a?.layers)!==null&&e!==void 0?e:xn.layers,i=t.map(uc),o=r.map(dc);if(i.length===0)throw new Error("At least one node shape must be specified.");if(o.length===0)throw new Error("At least one node layer must be specified.");return{shapes:i,layers:o}}function gc(a){var n,e,t,r=(n=a?.paths)!==null&&n!==void 0?n:Zt.paths,i=(e=a?.extremities)!==null&&e!==void 0?e:Zt.extremities,o=(t=a?.layers)!==null&&t!==void 0?t:Zt.layers,s=r.map(hc),l=i.map(fc).filter(function(d){return d!==null}),u=o.map(cc);if(s.length===0)throw new Error("At least one edge path must be specified.");if(u.length===0)throw new Error("At least one edge layer must be specified.");return{paths:s,extremities:l,layers:u}}function os(a,n){var e={},t=O(a),r;try{for(t.s();!(r=t.n()).done;){var i=r.value;i.variables&&Object.assign(e,i.variables)}}catch(o){t.e(o)}finally{t.f()}return Object.assign(e,n||{}),e}function ss(a,n,e,t,r){var i=is(t),o=i.shapes,s=i.layers,l=os(o,t?.variables),u=Ko(a,n,e,{shapes:o,layers:s,label:t?.label,backdrop:t?.backdrop,labelAttachments:t?.labelAttachments},r);return H(H({},u),{},{variables:l})}function ls(a,n,e,t,r,i){var o=gc(t),s=o.paths,l=o.extremities,u=o.layers,d=is(i),h=d.shapes,c=d.layers,f=os(s,t?.variables),g=rs(a,n,e,{paths:s,extremities:l,layers:u,defaultHead:t?.defaultHead,defaultTail:t?.defaultTail,label:t?.label},r,h,c);return H(H({},g),{},{variables:f,paths:s})}var vc=2;function us(a,n,e){var t=arguments.length>3&&arguments[3]!==void 0?arguments[3]:vc,r=n.canvas,i=r.width,o=r.height,s=e.x,l=e.y,u=e.rowHeight,d=e.maxRowWidth,h={},c=[],f=O(a),g;try{for(f.s();!(g=f.n()).done;){var y=g.value,m=y.width+t,v=y.height+t;if(m>i||v>o||s+m>i&&l+u+v>o){c.push(y);continue}s+m>i&&(d=Math.max(d,s),s=0,l+=u,u=v),y.draw(n,s,l),h[y.key]={x:s,y:l,width:y.width,height:y.height},s+=m,u=Math.max(u,v)}}catch(p){f.e(p)}finally{f.f()}return d=Math.max(d,s),{atlas:h,cursor:{x:s,y:l,rowHeight:u,maxRowWidth:d},remaining:c}}function Ie(a,n,e,t){var r=Object.defineProperty;try{r({},"",{})}catch{r=0}Ie=function(i,o,s,l){function u(d,h){Ie(i,d,function(c){return this._invoke(d,h,c)})}o?r?r(i,o,{value:s,enumerable:!l,configurable:!l,writable:!l}):i[o]=s:(u("next",0),u("throw",1),u("return",2))},Ie(a,n,e,t)}function Ge(){var a,n,e=typeof Symbol=="function"?Symbol:{},t=e.iterator||"@@iterator",r=e.toStringTag||"@@toStringTag";function i(f,g,y,m){var v=g&&g.prototype instanceof s?g:s,p=Object.create(v.prototype);return Ie(p,"_invoke",(function(b,T,_){var E,A,w,S=0,C=_||[],G=!1,L={p:0,n:0,v:a,a:N,f:N.bind(a,4),d:function(k,I){return E=k,A=0,w=a,L.n=I,o}};function N(k,I){for(A=k,w=I,n=0;!G&&S&&!W&&n<C.length;n++){var W,F=C[n],x=L.p,P=F[2];k>3?(W=P===I)&&(w=F[(A=F[4])?5:(A=3,3)],F[4]=F[5]=a):F[0]<=x&&((W=k<2&&x<F[1])?(A=0,L.v=I,L.n=F[1]):x<P&&(W=k<3||F[0]>I||I>P)&&(F[4]=k,F[5]=I,L.n=P,A=0))}if(W||k>1)return o;throw G=!0,I}return function(k,I,W){if(S>1)throw TypeError("Generator is already running");for(G&&I===1&&N(I,W),A=I,w=W;(n=A<2?a:w)||!G;){E||(A?A<3?(A>1&&(L.n=-1),N(A,w)):L.n=w:L.v=w);try{if(S=2,E){if(A||(k="next"),n=E[k]){if(!(n=n.call(E,w)))throw TypeError("iterator result is not an object");if(!n.done)return n;w=n.value,A<2&&(A=0)}else A===1&&(n=E.return)&&n.call(E),A<2&&(w=TypeError("The iterator does not provide a '"+k+"' method"),A=1);E=a}else if((n=(G=L.n<0)?w:b.call(T,L))!==o)break}catch(F){E=a,A=1,w=F}finally{S=1}}return{value:n,done:G}}})(f,y,m),!0),p}var o={};function s(){}function l(){}function u(){}n=Object.getPrototypeOf;var d=[][t]?n(n([][t]())):(Ie(n={},t,function(){return this}),n),h=u.prototype=s.prototype=Object.create(d);function c(f){return Object.setPrototypeOf?Object.setPrototypeOf(f,u):(f.__proto__=u,Ie(f,r,"GeneratorFunction")),f.prototype=Object.create(h),f}return l.prototype=u,Ie(h,"constructor",u),Ie(u,"constructor",l),l.displayName="GeneratorFunction",Ie(u,r,"GeneratorFunction"),Ie(h),Ie(h,r,"Generator"),Ie(h,t,function(){return this}),Ie(h,"toString",function(){return"[object Generator]"}),(Ge=function(){return{w:i,m:c}})()}function ds(a,n,e,t,r,i,o){try{var s=a[i](o),l=s.value}catch(u){return void e(u)}s.done?n(l):Promise.resolve(l).then(t,r)}function ln(a){return function(){var n=this,e=arguments;return new Promise(function(t,r){var i=a.apply(n,e);function o(l){ds(i,t,r,o,s,"next",l)}function s(l){ds(i,t,r,o,s,"throw",l)}o(void 0)})}}var Ca=new Map,hs=!1;function pc(a){return new Promise(function(n,e){var t=new FileReader;t.onload=function(){return n(t.result)},t.onerror=e,t.readAsDataURL(a)})}function mc(a){if(!Ca.has(a)){var n=fetch(a).then(function(e){return e.blob()}).then(pc).catch(function(){return Ca.delete(a),null});Ca.set(a,n)}return Ca.get(a)}function yc(a){return Tr.apply(this,arguments)}function Tr(){return Tr=ln(Ge().m(function a(n){var e,t,r;return Ge().w(function(i){for(;;)switch(i.n){case 0:return e=document.createElement("div"),e.innerHTML=n,t=Array.from(e.querySelectorAll("img[src]")),r=t.filter(function(o){return!o.getAttribute("src").startsWith("data:")}),i.n=1,Promise.all(r.map((function(){var o=ln(Ge().m(function s(l){var u;return Ge().w(function(d){for(;;)switch(d.n){case 0:return d.n=1,mc(l.getAttribute("src"));case 1:u=d.v,u&&l.setAttribute("src",u);case 2:return d.a(2)}},s)}));return function(s){return o.apply(this,arguments)}})()));case 1:return i.a(2,e.innerHTML)}},a)})),Tr.apply(this,arguments)}function cs(a){return Er.apply(this,arguments)}function Er(){return Er=ln(Ge().m(function a(n){var e,t,r,i,o,s,l,u,d,h,c,f,g,y=arguments;return Ge().w(function(m){for(;;)switch(m.n){case 0:if(e=y.length>1&&y[1]!==void 0?y[1]:1,t=n instanceof SVGElement?new XMLSerializer().serializeToString(n):n,r=new DOMParser,i=r.parseFromString(t,"image/svg+xml"),o=i.querySelector("svg"),o){m.n=1;break}return m.a(2,null);case 1:if(s=parseFloat(o.getAttribute("width")||""),l=parseFloat(o.getAttribute("height")||""),(!(s>0)||!(l>0))&&(u=o.getAttribute("viewBox"),u&&(d=u.trim().split(/[\s,]+/),s=parseFloat(d[2]),l=parseFloat(d[3]))),!(!(s>0)||!(l>0))){m.n=2;break}return console.warn("Sigma: SVG label attachment has no parseable dimensions \u2014 skipped."),m.a(2,null);case 2:return h=Math.ceil(s*e),c=Math.ceil(l*e),f=new Blob([t],{type:"image/svg+xml"}),g=URL.createObjectURL(f),m.a(2,new Promise(function(v){var p=new Image;p.onload=function(){var b=document.createElement("canvas");b.width=h,b.height=c,b.getContext("2d").drawImage(p,0,0,h,c),URL.revokeObjectURL(g);try{b.getContext("2d").getImageData(0,0,1,1)}catch(T){if(T instanceof DOMException&&T.name==="SecurityError"){hs||(hs=!0,console.warn('Sigma: A label attachment was skipped because the rendered canvas is tainted. SVG with <foreignObject> (used by the "html" attachment type) is blocked in Chromium and Safari. Use type: "canvas" with Canvas 2D rendering instead.')),v(null);return}throw T}v(b)},p.onerror=function(){URL.revokeObjectURL(g),v(null)},p.src=g}))}},a)})),Er.apply(this,arguments)}function bc(a,n){var e=document.createElement("div");e.style.cssText="position:fixed;left:-99999px;top:0;visibility:hidden;width:max-content;height:max-content",e.innerHTML=(n?"<style>".concat(n,"</style>"):"")+a,document.body.appendChild(e);var t=e.getBoundingClientRect(),r=t.width,i=t.height;return document.body.removeChild(e),{width:Math.ceil(r),height:Math.ceil(i)}}function _c(a,n,e,t){return Sr.apply(this,arguments)}function Sr(){return Sr=ln(Ge().m(function a(n,e,t,r){var i,o,s,l,u,d,h,c,f=arguments;return Ge().w(function(g){for(;;)switch(g.n){case 0:return i=f.length>4&&f[4]!==void 0?f[4]:1,o=n instanceof HTMLElement?n.outerHTML:n,g.n=1,yc(o);case 1:return s=g.v,(t==null||r==null)&&(l=bc(s,e),t=t??l.width,r=r??l.height),u=Math.ceil(t*i),d=Math.ceil(r*i),h=e?"<style>".concat(e,"</style>"):"",c='<svg xmlns="http://www.w3.org/2000/svg" '+'width="'.concat(u,'" height="').concat(d,'" viewBox="0 0 ').concat(t," ").concat(r,'">')+'<foreignObject width="'.concat(t,'" height="').concat(r,'">')+'<body xmlns="http://www.w3.org/1999/xhtml" style="margin:0;padding:0">'.concat(h).concat(s,"</body>")+"</foreignObject></svg>",g.a(2,cs(c,1))}},a)})),Sr.apply(this,arguments)}function xc(a){return wr.apply(this,arguments)}function wr(){return wr=ln(Ge().m(function a(n){var e,t=arguments,r;return Ge().w(function(i){for(;;)switch(i.n){case 0:e=t.length>1&&t[1]!==void 0?t[1]:1,r=n.type,i.n=r==="canvas"?1:r==="svg"?2:r==="html"?3:4;break;case 1:return i.a(2,n.canvas);case 2:return i.a(2,cs(n.svg,e));case 3:return i.a(2,_c(n.html,n.css,n.width,n.height,e));case 4:return i.a(2)}},a)})),wr.apply(this,arguments)}var sn=2048,fs=(function(){function a(n,e,t){te(this,a),D(this,"cache",new Map),D(this,"pending",new Set),D(this,"atlas",{}),D(this,"glTexture",null),D(this,"dirty",!0),this.gl=n,this.renderers=e,this.scheduleRender=t,this.packCanvas=document.createElement("canvas"),this.packCanvas.width=sn,this.packCanvas.height=sn,this.packCtx=this.packCanvas.getContext("2d")}return ne(a,[{key:"renderAttachment",value:function(e,t,r){var i=this,o="".concat(e,":").concat(t);if(!(this.cache.has(o)||this.pending.has(o))){var s=this.renderers[t];if(s){var l=s(r);if(l){this.pending.add(o);var u=r.pixelRatio;Promise.resolve(l).then((function(){var d=ln(Ge().m(function h(c){var f;return Ge().w(function(g){for(;;)switch(g.n){case 0:if(i.pending.has(o)){g.n=1;break}return g.a(2);case 1:if(i.pending.delete(o),c){g.n=2;break}return g.a(2);case 2:return g.n=3,xc(c,u);case 3:if(f=g.v,!(!f||f.width===0||f.height===0)){g.n=4;break}return g.a(2);case 4:i.cache.set(o,{image:f,width:f.width,height:f.height}),i.dirty=!0,i.scheduleRender();case 5:return g.a(2)}},h)}));return function(h){return d.apply(this,arguments)}})())}}}}},{key:"regenerateAtlas",value:function(){if(this.dirty){this.dirty=!1;var e=[];if(this.cache.forEach(function(u,d){e.push({key:d,width:u.width,height:u.height,draw:function(c,f,g){c.drawImage(u.image,f,g)}})}),e.length===0){this.atlas={},this.deleteGLTexture();return}var t={x:0,y:0,rowHeight:0,maxRowWidth:0};this.packCtx.clearRect(0,0,sn,sn);var r=us(e,this.packCtx,t),i=r.atlas,o=r.remaining;this.atlas=i,o.length>0&&console.warn("Sigma: ".concat(o.length," label attachment(s) could not fit in the ").concat(sn,"x").concat(sn," atlas and will not be rendered.")),this.deleteGLTexture();var s=this.gl,l=s.createTexture();s.activeTexture(s.TEXTURE0+Cn),s.bindTexture(s.TEXTURE_2D,l),s.pixelStorei(s.UNPACK_PREMULTIPLY_ALPHA_WEBGL,!0),s.texImage2D(s.TEXTURE_2D,0,s.RGBA,s.RGBA,s.UNSIGNED_BYTE,this.packCanvas),s.pixelStorei(s.UNPACK_PREMULTIPLY_ALPHA_WEBGL,!1),s.texParameteri(s.TEXTURE_2D,s.TEXTURE_MIN_FILTER,s.LINEAR),s.texParameteri(s.TEXTURE_2D,s.TEXTURE_MAG_FILTER,s.LINEAR),s.texParameteri(s.TEXTURE_2D,s.TEXTURE_WRAP_S,s.CLAMP_TO_EDGE),s.texParameteri(s.TEXTURE_2D,s.TEXTURE_WRAP_T,s.CLAMP_TO_EDGE),this.glTexture=l}}},{key:"bindTexture",value:function(e){if(this.glTexture){var t=this.gl;t.activeTexture(t.TEXTURE0+e),t.bindTexture(t.TEXTURE_2D,this.glTexture)}}},{key:"getEntry",value:function(e,t){var r="".concat(e,":").concat(t);return this.atlas[r]||null}},{key:"invalidateNode",value:function(e){var t="".concat(e,":"),r=O(this.cache.keys()),i;try{for(r.s();!(i=r.n()).done;){var o=i.value;o.startsWith(t)&&(this.cache.delete(o),this.dirty=!0)}}catch(d){r.e(d)}finally{r.f()}var s=O(this.pending),l;try{for(s.s();!(l=s.n()).done;){var u=l.value;u.startsWith(t)&&this.pending.delete(u)}}catch(d){s.e(d)}finally{s.f()}}},{key:"restore",value:function(){this.glTexture=null,this.dirty=!0}},{key:"clear",value:function(){this.cache.clear(),this.pending.clear(),this.atlas={},this.dirty=!0,this.deleteGLTexture()}},{key:"kill",value:function(){this.clear(),this.packCanvas=null,this.packCtx=null,this.gl=null}},{key:"deleteGLTexture",value:function(){this.glTexture&&(this.gl.deleteTexture(this.glTexture),this.glTexture=null)}}])})(),Ar=(function(){function a(n){te(this,a),D(this,"buckets",new Map),D(this,"keyDepth",new Map);var e=O(n),t;try{for(e.s();!(t=e.n()).done;){var r=t.value;this.buckets.set(r,new Set)}}catch(i){e.e(i)}finally{e.f()}}return ne(a,[{key:"has",value:function(e){return this.keyDepth.has(e)}},{key:"getBucket",value:function(e){return this.buckets.get(e)}},{key:"set",value:function(e,t){var r,i=this.keyDepth.get(e);if(i!==t){var o=this.buckets.get(t);if(!o)throw new Error('Sigma: "'.concat(t,'" is not a declared depth layer'));i!==void 0&&((r=this.buckets.get(i))===null||r===void 0||r.delete(e)),o.add(e),this.keyDepth.set(e,t)}}},{key:"remove",value:function(e){var t=this.keyDepth.get(e);t!==void 0&&(this.buckets.get(t).delete(e),this.keyDepth.delete(e))}},{key:"clearAll",value:function(){var e=O(this.buckets.values()),t;try{for(e.s();!(t=e.n()).done;){var r=t.value;r.clear()}}catch(i){e.e(i)}finally{e.f()}this.keyDepth.clear()}},{key:"getSorted",value:function(e,t){var r=this.buckets.get(e);return!r||r.size===0?[]:Q(r).sort(function(i,o){return t(i)-t(o)})}}])})(),gs=(function(a){function n(e,t){return te(this,n),me(this,n,[e,2,t])}return ye(n,a),ne(n,[{key:"updateNode",value:function(t,r,i,o,s,l,u,d){var h=this.indexMap.get(t);if(h===void 0)throw new Error('Node "'.concat(t,'" not allocated in NodeDataTexture'));var c=gt(d),f=ie(c,4),g=f[0],y=f[1],m=f[2],v=f[3],p=h*2*4;this.data[p]=r,this.data[p+1]=i,this.data[p+2]=o,this.data[p+3]=s,this.data[p+4]=l,this.data[p+5]=u,this.data[p+6]=g*65536+y*256+m,this.data[p+7]=v/255,this.markDirty(h)}}])})(Sa),Tc=1024,Ec=1.5,Sc=4096,Dr=(function(){function a(n,e){var t;if(te(this,a),D(this,"texture",null),D(this,"framebuffer",null),!n.getExtension("EXT_color_buffer_float"))throw new Error("sigma: EXT_color_buffer_float is required for label/edge placement but is unavailable in this WebGL2 context.");this.gl=n,this.channels=e.channels,this.capacity=this.roundUpToPowerOfTwo((t=e.initialCapacity)!==null&&t!==void 0?t:Tc);var r=this.computeDimensions(this.capacity);this.textureWidth=r.width,this.textureHeight=r.height,this.create()}return ne(a,[{key:"roundUpToPowerOfTwo",value:function(e){return Math.pow(2,Math.ceil(Math.log2(Math.max(1,e))))}},{key:"computeDimensions",value:function(e){var t=Math.min(e,Sc),r=Math.ceil(e/t);return{width:t,height:r}}},{key:"create",value:function(){var e=this.gl,t=this.channels===1?e.R32F:e.RGBA32F,r=this.channels===1?e.RED:e.RGBA;if(this.texture=e.createTexture(),e.activeTexture(e.TEXTURE0),e.bindTexture(e.TEXTURE_2D,this.texture),e.texImage2D(e.TEXTURE_2D,0,t,this.textureWidth,this.textureHeight,0,r,e.FLOAT,null),e.texParameteri(e.TEXTURE_2D,e.TEXTURE_MIN_FILTER,e.NEAREST),e.texParameteri(e.TEXTURE_2D,e.TEXTURE_MAG_FILTER,e.NEAREST),e.texParameteri(e.TEXTURE_2D,e.TEXTURE_WRAP_S,e.CLAMP_TO_EDGE),e.texParameteri(e.TEXTURE_2D,e.TEXTURE_WRAP_T,e.CLAMP_TO_EDGE),this.framebuffer=e.createFramebuffer(),e.bindFramebuffer(e.FRAMEBUFFER,this.framebuffer),e.framebufferTexture2D(e.FRAMEBUFFER,e.COLOR_ATTACHMENT0,e.TEXTURE_2D,this.texture,0),e.checkFramebufferStatus(e.FRAMEBUFFER)!==e.FRAMEBUFFER_COMPLETE)throw new Error("sigma: float framebuffer for frame-pass placement is incomplete.");e.bindFramebuffer(e.FRAMEBUFFER,null),e.bindTexture(e.TEXTURE_2D,null)}},{key:"ensureCapacity",value:function(e){if(!(e<=this.capacity)){var t=this.gl;this.capacity=this.roundUpToPowerOfTwo(Math.ceil(e*Ec));var r=this.computeDimensions(this.capacity);this.textureWidth=r.width,this.textureHeight=r.height,this.texture&&t.deleteTexture(this.texture),this.framebuffer&&t.deleteFramebuffer(this.framebuffer),this.create()}}},{key:"bindAsRenderTarget",value:function(){var e=this.gl;e.bindFramebuffer(e.FRAMEBUFFER,this.framebuffer),e.viewport(0,0,this.textureWidth,this.textureHeight)}},{key:"bind",value:function(e){var t=this.gl;t.activeTexture(t.TEXTURE0+e),t.bindTexture(t.TEXTURE_2D,this.texture)}},{key:"getTexture",value:function(){return this.texture}},{key:"getTextureWidth",value:function(){return this.textureWidth}},{key:"getTextureHeight",value:function(){return this.textureHeight}},{key:"restore",value:function(){this.gl.getExtension("EXT_color_buffer_float"),this.create()}},{key:"kill",value:function(){var e=this.gl;this.texture&&(e.deleteTexture(this.texture),this.texture=null),this.framebuffer&&(e.deleteFramebuffer(this.framebuffer),this.framebuffer=null)}}])})(),vs=(function(a){function n(e,t){return te(this,n),me(this,n,[e,2,t])}return ye(n,a),ne(n,[{key:"updateEdge",value:function(t,r,i,o,s,l){var u=arguments.length>6&&arguments[6]!==void 0?arguments[6]:0,d=arguments.length>7&&arguments[7]!==void 0?arguments[7]:0,h=arguments.length>8&&arguments[8]!==void 0?arguments[8]:0,c=this.indexMap.get(t);if(c===void 0)throw new Error('Edge "'.concat(t,'" not allocated in EdgeDataTexture'));var f=c*this.TEXELS_PER_ITEM*4;this.data[f+0]=r,this.data[f+1]=i,this.data[f+2]=o,this.data[f+3]=0,this.data[f+4]=s,this.data[f+5]=l,this.data[f+6]=u,this.data[f+7]=(d&15)<<4|h&15,this.markDirty(c)}}])})(Sa);var Ag=tt(cn()),Dg=tt(qt());function wc(a,n){if(a==null)return{};var e={};for(var t in a)if({}.hasOwnProperty.call(a,t)){if(n.indexOf(t)!==-1)continue;e[t]=a[t]}return e}function ps(a,n){if(a==null)return{};var e,t,r=wc(a,n);if(Object.getOwnPropertySymbols){var i=Object.getOwnPropertySymbols(a);for(t=0;t<i.length;t++)e=i[t],n.indexOf(e)===-1&&{}.propertyIsEnumerable.call(a,e)&&(r[e]=a[e])}return r}var Ac=["factor"],Dc=["factor"],ms=1.5,Rr={x:.5,y:.5,angle:0,ratio:1},ys=(function(a){function n(){var e;te(this,n);for(var t=arguments.length,r=new Array(t),i=0;i<t;i++)r[i]=arguments[i];return e=me(this,n,[].concat(r)),D(e,"minRatio",null),D(e,"maxRatio",null),D(e,"enabled",!0),D(e,"enabledZooming",!0),D(e,"enabledPanning",!0),D(e,"enabledRotation",!0),D(e,"constrainState",null),D(e,"state",H({},Rr)),D(e,"previousState",H({},Rr)),D(e,"nextFrame",null),D(e,"currentAnimationFrom",null),D(e,"currentAnimationTo",null),D(e,"animationCallback",null),e}return ye(n,a),ne(n,[{key:"x",get:function(){return this.state.x}},{key:"y",get:function(){return this.state.y}},{key:"angle",get:function(){return this.state.angle}},{key:"ratio",get:function(){return this.state.ratio}},{key:"getState",value:function(){return H({},this.state)}},{key:"getPreviousState",value:function(){return H({},this.previousState)}},{key:"getBoundedRatio",value:function(t){var r=t;return typeof this.minRatio=="number"&&(r=Math.max(r,this.minRatio)),typeof this.maxRatio=="number"&&(r=Math.min(r,this.maxRatio)),r}},{key:"validateState",value:function(t){var r=this.getState();return this.enabledPanning&&typeof t.x=="number"&&(r.x=t.x),this.enabledPanning&&typeof t.y=="number"&&(r.y=t.y),this.enabledZooming&&typeof t.ratio=="number"&&(r.ratio=this.getBoundedRatio(t.ratio)),this.enabledRotation&&typeof t.angle=="number"&&(r.angle=t.angle),this.constrainState?this.constrainState(r):r}},{key:"isAnimating",value:function(){return this.nextFrame!==null}},{key:"setState",value:function(t){if(!this.enabled)return this;var r=this.validateState(t);return Eo(this.state,r)?this:(this.previousState=this.state,this.state=r,this.emit("updated",this.getState()),this)}},{key:"updateState",value:function(t){return this.setState(t(this.getState())),this}},{key:"animate",value:function(t,r){var i=this;return this.enabled?new Promise(function(o){return i.runAnimation(t,H(H({},wo),r),o)}):Promise.resolve()}},{key:"cancelAnimation",value:function(){return this.nextFrame!==null&&(cancelAnimationFrame(this.nextFrame),this.nextFrame=null),this.resolveAnimation(),this.emitAnimationEnd(!1),this}},{key:"zoomIn",value:function(){var t=arguments.length>0&&arguments[0]!==void 0?arguments[0]:{},r=t.factor,i=r===void 0?ms:r,o=ps(t,Ac);return this.animate({ratio:this.ratio/i},o)}},{key:"zoomOut",value:function(){var t=arguments.length>0&&arguments[0]!==void 0?arguments[0]:{},r=t.factor,i=r===void 0?ms:r,o=ps(t,Dc);return this.animate({ratio:this.ratio*i},o)}},{key:"reset",value:function(t){return this.animate(Rr,t)}},{key:"runAnimation",value:function(t,r,i){var o=this,s=sa(r.easing),l=Date.now(),u=this.getState(),d=this.validateState(t),h=function(){if(!o.enabled){o.cancelAnimation();return}var f=r.duration>0?(Date.now()-l)/r.duration:1;if(f>=1){o.nextFrame=null,o.setState(d),o.resolveAnimation(),o.emitAnimationEnd(!0);return}var g=s(f);o.setState({x:u.x+(d.x-u.x)*g,y:u.y+(d.y-u.y)*g,angle:u.angle+(d.angle-u.angle)*g,ratio:u.ratio+(d.ratio-u.ratio)*g}),o.nextFrame=requestAnimationFrame(h)};this.cancelAnimation(),this.currentAnimationFrom=u,this.currentAnimationTo=d,this.animationCallback=i,this.emit("animationStart",{from:u,to:d}),h()}},{key:"resolveAnimation",value:function(){var t=this.animationCallback;this.animationCallback=null,t&&t()}},{key:"emitAnimationEnd",value:function(t){var r=this.currentAnimationFrom,i=this.currentAnimationTo;!r||!i||(this.currentAnimationFrom=null,this.currentAnimationTo=null,this.emit("animationEnd",{from:r,to:i,completed:t}))}}],[{key:"from",value:function(t){var r=new n;return r.setState(t)}}])})(ha);function ze(a,n){var e=n.getBoundingClientRect();return{x:a.clientX-e.left,y:a.clientY-e.top}}function et(a,n){var e=H(H({},ze(a,n)),{},{sigmaDefaultPrevented:!1,preventSigmaDefault:function(){e.sigmaDefaultPrevented=!0},original:a});return e}function kt(a){var n="x"in a?a:H(H({},a.touches[0]||a.previousTouches[0]),{},{original:a.original,sigmaDefaultPrevented:a.sigmaDefaultPrevented,preventSigmaDefault:function(){a.sigmaDefaultPrevented=!0,n.sigmaDefaultPrevented=!0}});return n}function Rc(a,n){var e=et(a,n);return e.delta=Fs(a),e}var Cc=2;function ka(a){for(var n=[],e=0,t=Math.min(a.length,Cc);e<t;e++)n.push(a[e]);return n}function kn(a,n,e){var t={touches:ka(a.touches).map(function(r){return ze(r,e)}),previousTouches:n.map(function(r){return ze(r,e)}),sigmaDefaultPrevented:!1,preventSigmaDefault:function(){t.sigmaDefaultPrevented=!0},original:a};return t}function Fs(a){if(typeof a.deltaY<"u")return a.deltaY*-3/360;if(typeof a.detail<"u")return a.detail/-9;throw new Error("Captor: could not extract delta from event.")}var Is=(function(a){function n(e,t){var r;return te(this,n),r=me(this,n),r.container=e,r.renderer=t,r}return ye(n,a),ne(n)})(ha),Lc=["doubleClickTimeout","doubleClickZoomingDuration","doubleClickZoomingRatio","dragTimeout","draggedEventsTolerance","enableCameraMouseRotation","gestureTarget","inertiaDuration","inertiaRatio","zoomDuration","zoomingRatio"],kc=Lc.reduce(function(a,n){return H(H({},a),{},D({},n,ga[n]))},{});function Pn(a){return a instanceof PointerEvent&&a.pointerType==="touch"}var Pc=(function(a){function n(e,t){var r;return te(this,n),r=me(this,n,[e,t]),D(r,"enabled",!0),D(r,"draggedEvents",0),D(r,"downStartTime",null),D(r,"lastMouseX",null),D(r,"lastMouseY",null),D(r,"isMouseDown",!1),D(r,"isMoving",!1),D(r,"isPanningStage",!1),D(r,"movingTimeout",null),D(r,"startCameraState",null),D(r,"clicks",0),D(r,"doubleClickTimeout",null),D(r,"isRightMouseDown",!1),D(r,"startRotationAngle",null),D(r,"startCameraAngle",null),D(r,"currentWheelDirection",0),D(r,"lastWheelAnimationId",0),D(r,"settings",kc),r.handleRightClick=r.handleRightClick.bind(r),r.handleDown=r.handleDown.bind(r),r.handleUp=r.handleUp.bind(r),r.handleMove=r.handleMove.bind(r),r.handleWheel=r.handleWheel.bind(r),r.handleLeave=r.handleLeave.bind(r),r.handleEnter=r.handleEnter.bind(r),e.addEventListener("contextmenu",r.handleRightClick,{capture:!1}),e.addEventListener("pointerdown",r.handleDown,{capture:!1}),e.addEventListener("wheel",r.handleWheel,{capture:!1,passive:!1}),e.addEventListener("pointerleave",r.handleLeave,{capture:!1}),e.addEventListener("pointerenter",r.handleEnter,{capture:!1}),document.addEventListener("pointermove",r.handleMove,{capture:!1}),document.addEventListener("pointerup",r.handleUp,{capture:!1}),r}return ye(n,a),ne(n,[{key:"kill",value:function(){var t=this.container;t.removeEventListener("contextmenu",this.handleRightClick),t.removeEventListener("pointerdown",this.handleDown),t.removeEventListener("wheel",this.handleWheel),t.removeEventListener("pointerleave",this.handleLeave),t.removeEventListener("pointerenter",this.handleEnter),document.removeEventListener("pointermove",this.handleMove),document.removeEventListener("pointerup",this.handleUp)}},{key:"handleClick",value:function(t){var r=this;if(this.enabled){if(this.clicks++,this.clicks===2)return this.clicks=0,typeof this.doubleClickTimeout=="number"&&(clearTimeout(this.doubleClickTimeout),this.doubleClickTimeout=null),this.handleDoubleClick(t);setTimeout(function(){r.clicks=0,r.doubleClickTimeout=null},this.settings.doubleClickTimeout),this.draggedEvents<this.settings.draggedEventsTolerance&&this.emit("click",et(t,this.container))}}},{key:"handleRightClick",value:function(t){this.enabled&&(this.settings.enableCameraMouseRotation&&t.preventDefault(),this.emit("rightClick",et(t,this.container)))}},{key:"handleDoubleClick",value:function(t){if(this.enabled){t.preventDefault(),t.stopPropagation();var r=et(t,this.container);if(this.emit("doubleClick",r),!r.sigmaDefaultPrevented){var i=this.renderer.getCamera(),o=i.getBoundedRatio(i.getState().ratio/this.settings.doubleClickZoomingRatio);i.animate(this.renderer.getViewportZoomedState(ze(t,this.container),o),{easing:"quadraticInOut",duration:this.settings.doubleClickZoomingDuration})}}}},{key:"handleDown",value:function(t){if(!(!this.enabled||Pn(t))){if(t.button===0){this.startCameraState=this.renderer.getCamera().getState();var r=ze(t,this.container),i=r.x,o=r.y;this.lastMouseX=i,this.lastMouseY=o,this.draggedEvents=0,this.downStartTime=Date.now(),this.isMouseDown=!0}if(t.button===2&&this.settings.enableCameraMouseRotation){var s=ze(t,this.container),l=s.x,u=s.y,d=this.container.offsetWidth/2,h=this.container.offsetHeight/2;this.startRotationAngle=Math.atan2(u-h,l-d),this.startCameraAngle=this.renderer.getCamera().getState().angle,this.isRightMouseDown=!0}this.emit("mousedown",et(t,this.container))}}},{key:"handleUp",value:function(t){var r=this;if(!(!this.enabled||Pn(t)||!this.isMouseDown&&!this.isRightMouseDown)){if(this.isRightMouseDown){this.isRightMouseDown=!1,this.startRotationAngle=null,this.startCameraAngle=null,this.emit("mouseup",et(t,this.container));return}var i=this.renderer.getCamera();this.isMouseDown=!1,this.isPanningStage&&(this.isPanningStage=!1,this.renderer._setPanning(!1)),typeof this.movingTimeout=="number"&&(clearTimeout(this.movingTimeout),this.movingTimeout=null);var o=ze(t,this.container),s=o.x,l=o.y,u=i.getState(),d=i.getPreviousState();this.isMoving?i.animate({x:u.x+this.settings.inertiaRatio*(u.x-d.x),y:u.y+this.settings.inertiaRatio*(u.y-d.y)},{duration:this.settings.inertiaDuration,easing:"quadraticOut"}):(this.lastMouseX!==s||this.lastMouseY!==l)&&i.setState({x:u.x,y:u.y}),this.isMoving=!1,setTimeout(function(){var h=r.draggedEvents>0;r.draggedEvents=0;var c=r.renderer.getSetting("hideEdgesOnMove")||r.renderer.getSetting("hideLabelsOnMove");h&&c&&r.renderer.refresh()},0),this.emit("mouseup",et(t,this.container)),(t.target===this.container||t.composedPath()[0]===this.container)&&this.handleClick(t)}}},{key:"handleMove",value:function(t){var r=this;if(!(!this.enabled||Pn(t))){var i=et(t,this.container);if(this.emit("mousemovebody",i),(t.target===this.container||t.composedPath()[0]===this.container)&&this.emit("mousemove",i),this.isMouseDown&&this.draggedEvents++,!i.sigmaDefaultPrevented){if(this.isMouseDown){this.isMoving=!0,typeof this.movingTimeout=="number"&&clearTimeout(this.movingTimeout),this.movingTimeout=window.setTimeout(function(){r.movingTimeout=null,r.isMoving=!1},this.settings.dragTimeout);var o=this.renderer.getCamera(),s=ze(t,this.container),l=s.x,u=s.y,d=this.renderer.viewportToFramedGraph({x:this.lastMouseX,y:this.lastMouseY}),h=this.renderer.viewportToFramedGraph({x:l,y:u}),c=d.x-h.x,f=d.y-h.y,g=o.getState(),y=g.x+c,m=g.y+f;this.isPanningStage||(this.isPanningStage=!0,this.renderer._setPanning(!0)),o.setState({x:y,y:m}),this.lastMouseX=l,this.lastMouseY=u,t.preventDefault(),t.stopPropagation()}if(this.isRightMouseDown){var v=ze(t,this.container),p=v.x,b=v.y,T=this.container.offsetWidth/2,_=this.container.offsetHeight/2,E=Math.atan2(b-_,p-T),A=E-this.startRotationAngle,w=this.renderer.getCamera();w.setState({angle:this.startCameraAngle+A}),t.preventDefault(),t.stopPropagation()}}}}},{key:"handleLeave",value:function(t){Pn(t)||this.emit("mouseleave",et(t,this.container))}},{key:"handleEnter",value:function(t){Pn(t)||this.emit("mouseenter",et(t,this.container))}},{key:"handleWheel",value:function(t){var r=this,i=this.renderer.getCamera();if(!(!this.enabled||!i.enabledZooming)){var o=Rc(t,this.container);if(this.emit("wheel",o),!o.sigmaDefaultPrevented){var s=this.settings.gestureTarget;if(s!=="page"){if(s==="shared"&&!t.ctrlKey&&!t.metaKey){this.renderer._showGestureHint("wheel");return}var l=Fs(t);if(l){t.preventDefault(),t.stopPropagation();var u=i.getState().ratio,d=l>0?1/this.settings.zoomingRatio:this.settings.zoomingRatio,h=i.getBoundedRatio(u*d),c=l>0?1:-1,f=Date.now();if(u!==h&&!(this.currentWheelDirection===c&&this.lastWheelTriggerTime&&f-this.lastWheelTriggerTime<this.settings.zoomDuration/5)){var g=++this.lastWheelAnimationId;i.animate(this.renderer.getViewportZoomedState(ze(t,this.container),h),{easing:"quadraticOut",duration:this.settings.zoomDuration}).then(function(){r.lastWheelAnimationId===g&&(r.currentWheelDirection=0)}),this.currentWheelDirection=c,this.lastWheelTriggerTime=f}}}}}}},{key:"setSettings",value:function(t){this.settings=t}}])})(Is),Fc=["dragTimeout","gestureTarget","inertiaDuration","inertiaRatio","doubleClickTimeout","doubleClickZoomingRatio","doubleClickZoomingDuration","tapMoveTolerance"],Ic=Fc.reduce(function(a,n){return H(H({},a),{},D({},n,ga[n]))},{}),Gc=(function(a){function n(e,t){var r;return te(this,n),r=me(this,n,[e,t]),D(r,"enabled",!0),D(r,"isMoving",!1),D(r,"hasMoved",!1),D(r,"isPanningStage",!1),D(r,"isZoomingStage",!1),D(r,"touchMode",0),D(r,"startTouchesPositions",[]),D(r,"lastTouches",[]),D(r,"lastTap",null),D(r,"settings",Ic),r.handleStart=r.handleStart.bind(r),r.handleLeave=r.handleLeave.bind(r),r.handleMove=r.handleMove.bind(r),e.addEventListener("touchstart",r.handleStart,{capture:!1}),e.addEventListener("touchcancel",r.handleLeave,{capture:!1}),document.addEventListener("touchend",r.handleLeave,{capture:!1,passive:!1}),document.addEventListener("touchmove",r.handleMove,{capture:!1,passive:!1}),r}return ye(n,a),ne(n,[{key:"kill",value:function(){var t=this.container;t.removeEventListener("touchstart",this.handleStart),t.removeEventListener("touchcancel",this.handleLeave),document.removeEventListener("touchend",this.handleLeave),document.removeEventListener("touchmove",this.handleMove)}},{key:"getDimensions",value:function(){return{width:this.container.offsetWidth,height:this.container.offsetHeight}}},{key:"doesCapture",value:function(t){var r=this.settings.gestureTarget;return r==="graph"?!0:r==="page"?!1:t>=2}},{key:"syncStageFlags",value:function(){var t=this.touchMode===1&&this.hasMoved,r=this.touchMode===2;t!==this.isPanningStage&&(this.isPanningStage=t,this.renderer._setPanning(t)),r!==this.isZoomingStage&&(this.isZoomingStage=r,this.renderer._setZooming(r))}},{key:"handleStart",value:function(t){var r=this;if(this.enabled){var i=ka(t.touches);if(this.touchMode=i.length,this.startCameraState=this.renderer.getCamera().getState(),this.startTouchesPositions=i.map(function(f){return ze(f,r.container)}),this.touchMode===2){var o=ie(this.startTouchesPositions,2),s=o[0],l=s.x,u=s.y,d=o[1],h=d.x,c=d.y;this.startTouchesAngle=Math.atan2(c-u,h-l),this.startTouchesDistance=Math.sqrt(Math.pow(h-l,2)+Math.pow(c-u,2))}this.syncStageFlags(),this.emit("touchdown",kn(t,this.lastTouches,this.container)),this.lastTouches=i,this.lastTouchesPositions=this.startTouchesPositions,t.cancelable&&(this.doesCapture(t.touches.length)||this.renderer._hasNodeDrag())&&t.preventDefault()}}},{key:"handleLeave",value:function(t){if(!(!this.enabled||!this.startTouchesPositions.length)){switch(t.cancelable&&this.doesCapture(this.touchMode)&&t.preventDefault(),this.movingTimeout&&(this.isMoving=!1,clearTimeout(this.movingTimeout)),this.touchMode){case 2:if(t.touches.length===1){this.handleStart(t);break}case 1:if(this.isMoving){var r=this.renderer.getCamera(),i=r.getState(),o=r.getPreviousState();r.animate({x:i.x+this.settings.inertiaRatio*(i.x-o.x),y:i.y+this.settings.inertiaRatio*(i.y-o.y)},{duration:this.settings.inertiaDuration,easing:"quadraticOut"})}this.hasMoved=!1,this.isMoving=!1,this.touchMode=0;break}if(this.syncStageFlags(),this.emit("touchup",kn(t,this.lastTouches,this.container)),!t.touches.length){var s=ze(this.lastTouches[0],this.container),l=this.startTouchesPositions[0],u=Math.pow(s.x-l.x,2)+Math.pow(s.y-l.y,2);if(!t.touches.length&&u<Math.pow(this.settings.tapMoveTolerance,2))if(this.lastTap&&Date.now()-this.lastTap.time<this.settings.doubleClickTimeout){var d=kn(t,this.lastTouches,this.container);if(this.emit("doubletap",d),this.lastTap=null,!d.sigmaDefaultPrevented&&this.settings.gestureTarget!=="page"){var h=this.renderer.getCamera(),c=h.getBoundedRatio(h.getState().ratio/this.settings.doubleClickZoomingRatio);h.animate(this.renderer.getViewportZoomedState(s,c),{easing:"quadraticInOut",duration:this.settings.doubleClickZoomingDuration})}}else{var f=kn(t,this.lastTouches,this.container);this.emit("tap",f),this.lastTap={time:Date.now(),position:f.touches[0]||f.previousTouches[0]}}}this.lastTouches=ka(t.touches),this.startTouchesPositions=[]}}},{key:"handleMove",value:function(t){var r=this;if(!(!this.enabled||!this.startTouchesPositions.length)){var i=this.doesCapture(t.touches.length);i&&t.preventDefault();var o=ka(t.touches),s=o.map(function(R){return ze(R,r.container)}),l=this.lastTouches;this.lastTouches=o,this.lastTouchesPositions=s;var u=kn(t,l,this.container);if(this.emit("touchmove",u),!u.sigmaDefaultPrevented&&(this.hasMoved||(this.hasMoved=s.some(function(R,j){var q=r.startTouchesPositions[j];return q&&(R.x!==q.x||R.y!==q.y)})),!!this.hasMoved)){if(!i){this.settings.gestureTarget==="shared"&&this.renderer._showGestureHint("touch");return}this.isMoving=!0,this.syncStageFlags(),this.movingTimeout&&clearTimeout(this.movingTimeout),this.movingTimeout=window.setTimeout(function(){r.isMoving=!1},this.settings.dragTimeout);var d=this.renderer.getCamera(),h=this.startCameraState,c=this.renderer.getSetting("stagePadding");switch(this.touchMode){case 1:{var f=this.renderer.viewportToFramedGraph((this.startTouchesPositions||[])[0]),g=f.x,y=f.y,m=this.renderer.viewportToFramedGraph(s[0]),v=m.x,p=m.y;d.setState({x:h.x+g-v,y:h.y+y-p});break}case 2:{var b={x:.5,y:.5,angle:0,ratio:1},T=s[0],_=T.x,E=T.y,A=s[1],w=A.x,S=A.y,C=Math.atan2(S-E,w-_)-this.startTouchesAngle,G=Math.hypot(S-E,w-_)/this.startTouchesDistance,L=d.getBoundedRatio(h.ratio/G);b.ratio=L,b.angle=h.angle+C;var N=this.getDimensions(),k=this.renderer.viewportToFramedGraph((this.startTouchesPositions||[])[0],{cameraState:h}),I=Math.min(N.width,N.height)-2*c,W=I/N.width,F=I/N.height,x=L/I,P=_-I/2/W,U=E-I/2/F,z=ja({x:P,y:U},b.angle);P=z.x,U=z.y,b.x=k.x-P*x,b.y=k.y+U*x,d.setState(b);break}}}}}},{key:"setSettings",value:function(t){this.settings=t}}])})(Is),zc=(function(){function a(n,e,t,r){te(this,a),D(this,"pendingNode",null),D(this,"session",null),this.graph=n,this.viewportToGraph=e,this.setNodesState=t,this.emit=r}return ne(a,[{key:"start",value:function(e,t,r,i,o){var s=r(e),l=!1;if(this.emit("nodeDragStart",{node:e,allDraggedNodes:s,event:t,preventSigmaDefault:function(){l=!0}}),l)return!1;var u=new Map,d=O(s),h;try{for(d.s();!(h=d.n()).done;){var c=h.value;u.set(c,{x:this.graph.getNodeAttribute(c,i),y:this.graph.getNodeAttribute(c,o)})}}catch(f){d.e(f)}finally{d.f()}return this.session={node:e,allNodes:s,startPosition:this.viewportToGraph(t),startNodePositions:u,xAttr:i,yAttr:o},this.setNodesState(s,{isDragged:!0}),!0}},{key:"applyMove",value:function(e,t){var r=this.session,i=r.allNodes,o=r.startNodePositions,s=r.startPosition,l=r.xAttr,u=r.yAttr,d=this.viewportToGraph(e),h={x:d.x-s.x,y:d.y-s.y},c=O(i),f;try{for(c.s();!(f=c.n()).done;){var g=f.value,y=o.get(g);if(!(!y||!this.graph.hasNode(g))){var m={x:y.x+h.x,y:y.y+h.y};t?this.graph.mergeNodeAttributes(g,t(m,g)):(this.graph.setNodeAttribute(g,l,m.x),this.graph.setNodeAttribute(g,u,m.y))}}}catch(v){c.e(v)}finally{c.f()}}},{key:"end",value:function(){if(this.pendingNode=null,!this.session)return null;var e=this.session,t=e.node,r=e.allNodes;return this.setNodesState(r,{isDragged:!1}),this.session=null,{node:t,allNodes:r}}},{key:"removeNode",value:function(e){e===this.pendingNode&&(this.pendingNode=null),this.session&&(this.session.node===e?(this.setNodesState(this.session.allNodes,{isDragged:!1}),this.session=null):this.session.allNodes.includes(e)&&(this.session.allNodes=this.session.allNodes.filter(function(t){return t!==e}),this.session.startNodePositions.delete(e)))}},{key:"clear",value:function(){this.pendingNode=null,this.session=null}}])})();function bs(a,n){return a<n?"".concat(a,"\0").concat(n):"".concat(n,"\0").concat(a)}var Nc=(function(){function a(n,e){te(this,a),D(this,"groups",new Map),D(this,"edgeToGroupKey",new Map),this.graph=n,this.onGroupChanged=e}return ne(a,[{key:"getGroupKey",value:function(e){return bs(this.graph.source(e),this.graph.target(e))}},{key:"sortGroup",value:function(e,t){var r=this,i=t.split("\0")[0];e.sort(function(o,s){var l=r.graph.source(o)===i||!r.graph.isDirected(o)?0:1,u=r.graph.source(s)===i||!r.graph.isDirected(s)?0:1;return l-u})}},{key:"register",value:function(e){var t=this.getGroupKey(e),r=this.groups.get(t);r||(r=[],this.groups.set(t,r)),r.includes(e)||r.push(e),this.edgeToGroupKey.set(e,t),r.length>1&&this.sortGroup(r,t),this.onGroupChanged(r,r.length)}},{key:"unregister",value:function(e){var t=this.edgeToGroupKey.get(e);if(t){this.edgeToGroupKey.delete(e);var r=this.groups.get(t);if(r){var i=r.indexOf(e);i!==-1&&r.splice(i,1),r.length===0?this.groups.delete(t):this.onGroupChanged(r,r.length)}}}},{key:"getGroup",value:function(e){var t,r=this.edgeToGroupKey.get(e);return r?(t=this.groups.get(r))!==null&&t!==void 0?t:[]:[]}},{key:"getSiblings",value:function(e){return this.getGroup(e).filter(function(t){return t!==e})}},{key:"rebuild",value:function(){var e=this;this.groups.clear(),this.edgeToGroupKey.clear(),this.graph.forEachEdge(function(l,u,d,h){var c=bs(d,h),f=e.groups.get(c);f||(f=[],e.groups.set(c,f)),f.push(l),e.edgeToGroupKey.set(l,c)});var t=O(this.groups),r;try{for(t.s();!(r=t.n()).done;){var i=ie(r.value,2),o=i[0],s=i[1];s.length>1&&this.sortGroup(s,o),this.onGroupChanged(s,s.length)}}catch(l){t.e(l)}finally{t.f()}}},{key:"clear",value:function(){this.groups.clear(),this.edgeToGroupKey.clear()}}])})();function _s(a,n){var e;if(a===!1||a==="extend"||a==="separate")return a;var t=a[n];return t!==void 0?t:(e=a.default)!==null&&e!==void 0?e:!1}function xs(a){return a===!1?!1:a==="extend"||a==="separate"?!0:Object.values(a).some(function(n){return n==="extend"||n==="separate"})}function Ts(a){return a==="separate"?!0:a===!1||a==="extend"?!1:a.default==="separate"?!0:Object.values(a).includes("separate")}var Ce={node:{parent:null,eventSuffix:"Node",payloadKey:"node",isEnabled:function(){return!0},writesPickingThisFrame:function(){return!0},setHover:function(n,e,t){return n.setNodeState(e,{isHovered:t})},getCursor:function(n,e){var t;return(t=n.nodeDataCache[e])===null||t===void 0?void 0:t.cursor},isHitValid:function(n,e){var t;return((t=n.nodeDataCache[e])===null||t===void 0?void 0:t.visibility)!=="hidden"}},edge:{parent:null,eventSuffix:"Edge",payloadKey:"edge",isEnabled:function(n){return!!n.settings.enableEdgeEvents},writesPickingThisFrame:function(n){return!!n.settings.enableEdgeEvents},setHover:function(n,e,t){return n.setEdgeState(e,{isHovered:t})},getCursor:function(n,e){var t;return(t=n.edgeDataCache[e])===null||t===void 0?void 0:t.cursor}},nodeLabel:{parent:"node",eventSuffix:"NodeLabel",payloadKey:"node",isEnabled:function(n){return Ts(n.settings.nodeLabelEvents)},writesPickingThisFrame:function(n){return xs(n.settings.nodeLabelEvents)},setHover:function(n,e,t){return n.setNodeState(e,{isLabelHovered:t})},getCursor:function(n,e){var t;return(t=n.nodeDataCache[e])===null||t===void 0?void 0:t.labelCursor},resolveForVerb:function(n,e,t){var r=_s(t.settings.nodeLabelEvents,e);return r===!1?null:r==="extend"?{kind:"node",key:n.key}:n}},edgeLabel:{parent:"edge",eventSuffix:"EdgeLabel",payloadKey:"edge",isEnabled:function(n){return Ts(n.settings.edgeLabelEvents)},writesPickingThisFrame:function(n){return xs(n.settings.edgeLabelEvents)},setHover:function(n,e,t){return n.setEdgeState(e,{isLabelHovered:t})},getCursor:function(n,e){var t;return(t=n.edgeDataCache[e])===null||t===void 0?void 0:t.labelCursor},resolveForVerb:function(n,e,t){var r=_s(t.settings.edgeLabelEvents,e);return r===!1?null:r==="extend"?{kind:"edge",key:n.key}:n}}},It=["node","edge","nodeLabel","edgeLabel"];function Mc(){return{lookup:[null],idsByKind:{node:new Map,edge:new Map,nodeLabel:new Map,edgeLabel:new Map},nextId:1}}function Ft(a,n,e){var t;return(t=a.idsByKind[n].get(e))!==null&&t!==void 0?t:0}function Cr(a,n){var e=O(It),t;try{for(e.s();!(t=e.n()).done;){var r=t.value;if(r===n||Ce[r].parent===n){var i=O(a.idsByKind[r].values()),o;try{for(i.s();!(o=i.n()).done;){var s=o.value;a.lookup[s]=null}}catch(c){i.e(c)}finally{i.f()}a.idsByKind[r]=new Map}}}catch(c){e.e(c)}finally{e.f()}var l=1,u=O(It),d;try{for(u.s();!(d=u.n()).done;){var h=d.value;if(h===n)break;l+=a.idsByKind[h].size}}catch(c){u.e(c)}finally{u.f()}a.nextId=l}function Es(a,n,e){var t=a.nextId++;return a.idsByKind[n].set(e,t),a.lookup[t]={kind:n,key:e},t}function Wc(a,n){var e=O(It),t;try{for(e.s();!(t=e.n()).done;){var r=t.value;if(Ce[r].parent!==null){var i=O(a.idsByKind[r].values()),o;try{for(i.s();!(o=i.n()).done;){var s=o.value;a.lookup[s]=null}}catch(_){i.e(_)}finally{i.f()}a.idsByKind[r]=new Map}}}catch(_){e.e(_)}finally{e.f()}a.nextId=1;var l=O(It),u;try{for(l.s();!(u=l.n()).done;){var d=u.value;if(Ce[d].parent===null){var h=O(a.idsByKind[d].values()),c;try{for(h.s();!(c=h.n()).done;){var f=c.value;f>=a.nextId&&(a.nextId=f+1)}}catch(_){h.e(_)}finally{h.f()}}}}catch(_){l.e(_)}finally{l.f()}var g=O(It),y;try{for(g.s();!(y=g.n()).done;){var m=y.value,v=Ce[m];if(!(v.parent===null||!v.isEnabled(n))){var p=O(a.idsByKind[v.parent].keys()),b;try{for(p.s();!(b=p.n()).done;){var T=b.value;a.idsByKind[m].set(T,a.nextId),a.lookup[a.nextId]={kind:m,key:T},a.nextId++}}catch(_){p.e(_)}finally{p.f()}}}}catch(_){g.e(_)}finally{g.f()}}function Uc(a,n){var e=O(It),t;try{for(e.s();!(t=e.n()).done;){var r=t.value,i=a[r],o=n[r];if(i!==o){if(i.size!==o.size)return!1;var s=O(i),l;try{for(s.s();!(l=s.n()).done;){var u=ie(l.value,2),d=u[0],h=u[1];if(o.get(d)!==h)return!1}}catch(c){s.e(c)}finally{s.f()}}}}catch(c){e.e(c)}finally{e.f()}return!0}function Ss(a,n,e){Ce[n.kind].setHover(a,n.key,e)}function Oc(a,n){return Ce[n.kind].getCursor(a,n.key)}function Fn(a,n){return"".concat(n).concat(Ce[a].eventSuffix)}function In(a,n){return H(H({},n),{},D({},Ce[a.kind].payloadKey,a.key))}function Bc(a,n,e){var t=Ce[n.kind].resolveForVerb;return t?t(n,e,a):n}function Hc(a,n){var e=Ce[n.kind].isHitValid;return e?e(a,n.key):!0}function Lr(a){return It.filter(function(n){return n===a||Ce[n].parent===a})}function Gs(a,n,e){return n&&(n=Bc(a,n,e)),n&&!Hc(a,n)&&(n=null),n}function kr(a,n,e){var t=e==="wheel"?a.stateManager.hovered:a.getHitAtPosition(n);return Gs(a,t,e)}function $c(a,n){return!a||!n?a===n:a.kind===n.kind&&a.key===n.key}function zs(a,n,e){var t={event:e,preventSigmaDefault:function(){return e.preventSigmaDefault()}},r=a.dragManager.session,i=r?{kind:"node",key:r.node}:Gs(a,n,"enter"),o=a.stateManager,s=o.hovered;$c(s,i)||(s&&(Ss(a,s,!1),a.emit(Fn(s.kind,"leave"),In(s,t))),o.setHovered(i),i&&(Ss(a,i,!0),a.emit(Fn(i.kind,"enter"),In(i,t))),a.updateContainerCursor())}function Vc(a,n,e,t){t.handleResize=function(){return a.scheduleRefresh()},window.addEventListener("resize",t.handleResize),t.handleMove=function(i){a.hoverResolver.pointerMoved(kt(i))},t.handleMoveBody=function(i){var o=kt(i),s=a.dragManager;if(s.pendingNode&&!s.session){var l=a.nodeStyleAnalysis,u=l.xAttribute,d=l.yAttribute,h=a.settings;s.start(s.pendingNode,o,h.getDraggedNodes,u||"x",d||"y"),s.pendingNode=null}s.session&&(s.applyMove(o,a.settings.dragPositionToAttributes),a.emit("nodeDrag",{node:s.session.node,allDraggedNodes:s.session.allNodes,event:o}),o.preventSigmaDefault()),a.emit("moveBody",{event:o,preventSigmaDefault:function(){return o.preventSigmaDefault()}})},t.handleLeave=function(i){var o=kt(i),s={event:o,preventSigmaDefault:function(){return o.preventSigmaDefault()}};a.hoverResolver.pointerLeft(),zs(a,null,o),a.emit("leaveStage",s)},t.handleEnter=function(i){var o=kt(i);a.emit("enterStage",{event:o,preventSigmaDefault:function(){return o.preventSigmaDefault()}})};var r=function(o){return function(s){var l=kt(s),u={event:l,preventSigmaDefault:function(){return l.preventSigmaDefault()}},d=kr(a,l,o);if(d){a.emit(Fn(d.kind,o),In(d,u));return}a.emit("".concat(o,"Stage"),u)}};t.handleClick=r("click"),t.handleRightClick=r("rightClick"),t.handleDoubleClick=r("doubleClick"),t.handleWheel=r("wheel"),t.handleDown=function(i){var o=kt(i),s={event:o,preventSigmaDefault:function(){return o.preventSigmaDefault()}},l=kr(a,o,"down");if(l){l.kind==="node"&&a.settings.enableNodeDrag&&(a.dragManager.pendingNode=l.key),a.emit(Fn(l.kind,"down"),In(l,s));return}a.emit("downStage",s)},t.handleUp=function(i){var o=kt(i),s={event:o,preventSigmaDefault:function(){return o.preventSigmaDefault()}},l=a.dragManager.end();l&&a.emit("nodeDragEnd",H({node:l.node,allDraggedNodes:l.allNodes},s));var u=kr(a,o,"up");if(u){a.emit(Fn(u.kind,"up"),In(u,s));return}a.emit("upStage",s)},n.on("mousemove",t.handleMove),n.on("mousemovebody",t.handleMoveBody),n.on("click",t.handleClick),n.on("rightClick",t.handleRightClick),n.on("doubleClick",t.handleDoubleClick),n.on("wheel",t.handleWheel),n.on("mousedown",t.handleDown),n.on("mouseup",t.handleUp),n.on("mouseleave",t.handleLeave),n.on("mouseenter",t.handleEnter),e.on("touchdown",t.handleDown),e.on("touchdown",t.handleMove),e.on("touchup",t.handleUp),e.on("touchmove",t.handleMove),e.on("tap",t.handleClick),e.on("doubletap",t.handleDoubleClick),e.on("touchmove",t.handleMoveBody)}function qc(a,n){var e=a.graph,t=new Set(["x","y","zIndex","type"]);n.eachNodeAttributesUpdatedGraphUpdate=function(r){var i,o=(i=r.hints)===null||i===void 0?void 0:i.attributes,s=!o||o.some(function(l){return t.has(l)});a.refresh({partialGraph:{nodes:e.nodes()},skipIndexation:!s,schedule:!0})},n.eachEdgeAttributesUpdatedGraphUpdate=function(r){var i,o=(i=r.hints)===null||i===void 0?void 0:i.attributes,s=o&&["zIndex","type"].some(function(l){return o?.includes(l)});a.refresh({partialGraph:{edges:e.edges()},skipIndexation:!s,schedule:!0})},n.addNodeGraphUpdate=function(r){a.addNode(r.key),a.refresh({partialGraph:{nodes:[r.key]},skipIndexation:!1,schedule:!0})},n.updateNodeGraphUpdate=function(r){a.refresh({partialGraph:{nodes:[r.key]},skipIndexation:!1,schedule:!0})},n.dropNodeGraphUpdate=function(r){a.removeNode(r.key),a.refresh({schedule:!0})},n.addEdgeGraphUpdate=function(r){var i=r.key;a.edgeGroups.register(i),a.addEdge(i);var o=a.edgeGroups.getSiblings(i),s=O(o),l;try{for(s.s();!(l=s.n()).done;){var u=l.value;a.addEdge(u)}}catch(d){s.e(d)}finally{s.f()}a.refresh({partialGraph:{edges:[i].concat(Q(o))},schedule:!0})},n.updateEdgeGraphUpdate=function(r){a.refresh({partialGraph:{edges:[r.key]},skipIndexation:!1,schedule:!0})},n.dropEdgeGraphUpdate=function(r){var i=r.key,o=a.edgeGroups.getSiblings(i);a.edgeGroups.unregister(i),a.removeEdge(i);var s=O(o),l;try{for(s.s();!(l=s.n()).done;){var u=l.value;a.addEdge(u)}}catch(d){s.e(d)}finally{s.f()}a.refresh({schedule:!0})},n.clearEdgesGraphUpdate=function(){a.clearEdgeState(),a.clearEdgeIndices(),a.refresh({schedule:!0})},n.clearGraphUpdate=function(){a.clearEdgeState(),a.clearNodeState(),a.clearEdgeIndices(),a.clearNodeIndices(),a.refresh({schedule:!0})},e.on("nodeAdded",n.addNodeGraphUpdate),e.on("nodeDropped",n.dropNodeGraphUpdate),e.on("nodeAttributesUpdated",n.updateNodeGraphUpdate),e.on("eachNodeAttributesUpdated",n.eachNodeAttributesUpdatedGraphUpdate),e.on("edgeAdded",n.addEdgeGraphUpdate),e.on("edgeDropped",n.dropEdgeGraphUpdate),e.on("edgeAttributesUpdated",n.updateEdgeGraphUpdate),e.on("eachEdgeAttributesUpdated",n.eachEdgeAttributesUpdatedGraphUpdate),e.on("edgesCleared",n.clearEdgesGraphUpdate),e.on("cleared",n.clearGraphUpdate)}function jc(a,n){a.removeListener("nodeAdded",n.addNodeGraphUpdate),a.removeListener("nodeDropped",n.dropNodeGraphUpdate),a.removeListener("nodeAttributesUpdated",n.updateNodeGraphUpdate),a.removeListener("eachNodeAttributesUpdated",n.eachNodeAttributesUpdatedGraphUpdate),a.removeListener("edgeAdded",n.addEdgeGraphUpdate),a.removeListener("edgeDropped",n.dropEdgeGraphUpdate),a.removeListener("edgeAttributesUpdated",n.updateEdgeGraphUpdate),a.removeListener("eachEdgeAttributesUpdated",n.eachEdgeAttributesUpdatedGraphUpdate),a.removeListener("edgesCleared",n.clearEdgesGraphUpdate),a.removeListener("cleared",n.clearGraphUpdate)}var Xc={x:.5,y:.5,angle:0,ratio:1},Yc=8,Kc=.001;function Zc(a){var n=a.coords,e=a.nodeData,t=a.dimensions,r=a.stagePadding,i=a.zoomToSizeRatioFunction,o=a.itemSizesReference,s=a.fitLabels,l=a.nodeLabelBox,u=Object.keys(n);if(!u.length)return a.extent;for(var d=i(1)||1,h=o==="positions",c=t.width,f=t.height,g=a.extent,y=0;y<Yc;y++){for(var m=fa(g),v={width:g.x[1]-g.x[0]||1,height:g.y[1]-g.y[0]||1},p=ft(Xc,t,v,r),b=ws(p,m({x:0,y:0}),c,f),T=ws(p,m({x:1,y:0}),c,f),_=Math.hypot(T.x-b.x,T.y-b.y)||1,E=1/0,A=-1/0,w=1/0,S=-1/0,C=0,G=u.length;C<G;C++){var L=u[C],N=e[L],k=N.size/d*(h?_:1),I=-k,W=k,F=-k,x=k;if(s){var P=l(N,k);P&&(P.minX<I&&(I=P.minX),P.maxX>W&&(W=P.maxX),P.minY<F&&(F=P.minY),P.maxY>x&&(x=P.maxY))}var U=n[L],z=U.x,R=U.y;E=Math.min(E,z+I/_),A=Math.max(A,z+W/_),w=Math.min(w,R-x/_),S=Math.max(S,R-F/_)}var j={x:[E,A],y:[w,S]},q=Math.max(j.x[1]-j.x[0],j.y[1]-j.y[0])||1,Z=Math.max(Math.abs(j.x[0]-g.x[0]),Math.abs(j.x[1]-g.x[1]),Math.abs(j.y[0]-g.y[0]),Math.abs(j.y[1]-g.y[1]));if(g=j,Z/q<Kc)break}return g}function ws(a,n,e,t){var r=Yt(a,n);return{x:(1+r.x)*e/2,y:(1-r.y)*t/2}}var Qc=typeof navigator<"u"&&/Mac|iP(hone|ad|od)/.test(navigator.platform),Jc=1500,ef=`.sigma-gesture-hint {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 1em;
  background: #00000066;
  color: #ffffff;
  font-size: 1em;
  pointer-events: none;
  transition: opacity 0.1s;
}`;function As(a){var n,e,t=en("style");t.textContent=a,document.head.appendChild(t);var r=((n=(e=t.sheet)===null||e===void 0?void 0:e.cssRules.length)!==null&&n!==void 0?n:0)>0;return t.remove(),r}var Pt=null;function tf(){return Pt===null&&(Pt=ef,As("@scope {}")&&(Pt=`@scope {
`.concat(Pt,`
}`)),As("@layer sigma-gesture-hint {}")&&(Pt=`@layer sigma-gesture-hint {
`.concat(Pt,`
}`))),Pt}var nf=(function(){function a(n){te(this,a),D(this,"hideTimeout",null),this.styleElement=en("style"),this.styleElement.textContent=tf(),n.appendChild(this.styleElement),this.element=en("div",{opacity:"0"},{class:"sigma-gesture-hint"}),n.appendChild(this.element)}return ne(a,[{key:"show",value:function(e,t){var r=this,i=e==="touch"?t.sharedGestureTouchMessage:Qc?t.sharedGestureAppleWheelMessage:t.sharedGestureWheelMessage;i&&(this.element.textContent=i,this.element.style.opacity="1",typeof this.hideTimeout=="number"&&clearTimeout(this.hideTimeout),this.hideTimeout=window.setTimeout(function(){r.hideTimeout=null,r.element.style.opacity="0"},Jc))}},{key:"kill",value:function(){typeof this.hideTimeout=="number"&&clearTimeout(this.hideTimeout),this.styleElement.remove(),this.element.remove()}}])})(),af=(function(){function a(n){te(this,a),D(this,"readBuffer",null),D(this,"fence",null),D(this,"result",new Uint8Array(4)),D(this,"generation",0),D(this,"readGeneration",0),D(this,"lastEvent",null),D(this,"active",!1),D(this,"dirty",!1),D(this,"rafId",null),D(this,"killed",!1),this.options=n}return ne(a,[{key:"pointerMoved",value:function(e){this.lastEvent=e,this.active=!0,!this.options.isRenderPending()&&this.request()}},{key:"pointerLeft",value:function(){this.active=!1,this.dirty=!1}},{key:"frameRendered",value:function(){this.request()}},{key:"invalidate",value:function(){this.generation++}},{key:"request",value:function(){if(!(this.killed||!this.active||!this.lastEvent)){if(this.fence){this.dirty=!0;return}this.startRead()}}},{key:"startRead",value:function(){var e=this.options,t=e.gl,r=e.getFrameBuffer,i=e.getPixelRatio,o=e.getDownSizingRatio;this.readGeneration=this.generation;var s=this.lastEvent,l=Xa(t,s.x,s.y,i(),o()),u=ie(l,2),d=u[0],h=u[1];this.readBuffer||(this.readBuffer=t.createBuffer()),t.bindFramebuffer(t.FRAMEBUFFER,r()),t.bindBuffer(t.PIXEL_PACK_BUFFER,this.readBuffer),t.bufferData(t.PIXEL_PACK_BUFFER,4,t.STREAM_READ),t.readPixels(d,h,1,1,t.RGBA,t.UNSIGNED_BYTE,0),t.bindBuffer(t.PIXEL_PACK_BUFFER,null),t.bindFramebuffer(t.FRAMEBUFFER,null),this.fence=t.fenceSync(t.SYNC_GPU_COMMANDS_COMPLETE,0),t.flush(),this.schedulePoll(s)}},{key:"schedulePoll",value:function(e){var t=this;this.rafId=requestAnimationFrame(function(){t.rafId=null,t.poll(e)})}},{key:"poll",value:function(e){var t=this.options,r=t.gl,i=t.onIndex;if(!(this.killed||!this.fence)){var o=r.clientWaitSync(this.fence,0,0);if(o===r.TIMEOUT_EXPIRED){this.schedulePoll(e);return}if(r.deleteSync(this.fence),this.fence=null,o!==r.WAIT_FAILED&&this.readGeneration===this.generation){r.bindBuffer(r.PIXEL_PACK_BUFFER,this.readBuffer),r.getBufferSubData(r.PIXEL_PACK_BUFFER,0,this.result),r.bindBuffer(r.PIXEL_PACK_BUFFER,null);var s=ie(this.result,4),l=s[0],u=s[1],d=s[2],h=s[3];this.active&&i(Ya(l,u,d,h),e)}this.dirty&&(this.dirty=!1,this.active&&this.lastEvent&&!this.options.isRenderPending()&&this.startRead())}}},{key:"reset",value:function(){this.rafId!==null&&cancelAnimationFrame(this.rafId),this.rafId=null,this.fence=null,this.readBuffer=null,this.dirty=!1}},{key:"kill",value:function(){this.killed=!0,this.rafId!==null&&cancelAnimationFrame(this.rafId),this.rafId=null;var e=this.options.gl;this.fence&&e.deleteSync(this.fence),this.fence=null,this.readBuffer&&e.deleteBuffer(this.readBuffer),this.readBuffer=null}}])})(),Ds=(function(){function a(n,e){te(this,a),this.key=n,this.size=e}return ne(a,null,[{key:"compare",value:function(e,t){return e.size>t.size?-1:e.size<t.size||e.key>t.key?1:-1}}])})(),La=(function(){function a(){te(this,a),D(this,"width",0),D(this,"height",0),D(this,"cellSize",0),D(this,"columns",0),D(this,"rows",0),D(this,"cells",{})}return ne(a,[{key:"resizeAndClear",value:function(e,t){this.width=e.width,this.height=e.height,this.cellSize=t,this.columns=Math.ceil(e.width/t),this.rows=Math.ceil(e.height/t),this.cells={}}},{key:"getIndex",value:function(e){var t=Math.floor(e.x/this.cellSize),r=Math.floor(e.y/this.cellSize);return r*this.columns+t}},{key:"add",value:function(e,t,r){var i=new Ds(e,t),o=this.getIndex(r),s=this.cells[o];s||(s=[],this.cells[o]=s),s.push(i)}},{key:"organize",value:function(){for(var e in this.cells){var t=this.cells[e];t.sort(Ds.compare)}}},{key:"getLabelsToDisplay",value:function(e,t,r){var i=this.cellSize*this.cellSize,o=i/e/e,s=o*t/i,l=Math.ceil(s),u=[];if(r)for(var d=Math.max(0,Math.floor(r.x1/this.cellSize)),h=Math.min(this.columns-1,Math.floor(r.x2/this.cellSize)),c=Math.max(0,Math.floor(r.y1/this.cellSize)),f=Math.min(this.rows-1,Math.floor(r.y2/this.cellSize)),g=c;g<=f;g++)for(var y=d;y<=h;y++){var m=g*this.columns+y,v=this.cells[m];if(v)for(var p=0;p<Math.min(l,v.length);p++)u.push(v[p].key)}else for(var b in this.cells)for(var T=this.cells[b],_=0;_<Math.min(l,T.length);_++)u.push(T[_].key);return u}}])})();function rf(a){var n=a.graph,e=a.hoveredNode,t=a.highlightedNodes,r=a.displayedNodeLabels,i=new Set,o=new Set(t);e&&o.add(e);var s=O(o),l;try{for(s.s();!(l=s.n()).done;){var u=l.value;n.hasNode(u)&&n.forEachEdge(u,function(f){i.add(f)})}}catch(f){s.e(f)}finally{s.f()}var d=O(r),h;try{var c=function(){var g=h.value;if(o.has(g))return 1;n.forEachEdge(g,function(y,m,v,p){var b=v===g?p:v;r.has(b)&&i.add(y)})};for(d.s();!(h=d.n()).done;)c()}catch(f){d.e(f)}finally{d.f()}return Array.from(i)}var un=150,dn=50,of={both:0,node:1,label:2},sf={over:0,above:1,below:2,auto:3},Rs=12,lf=3,uf=(function(){function a(n){te(this,a),D(this,"labelGrid",new La),D(this,"edgeAnchorGrid",new La),D(this,"displayedNodeLabels",new Set),D(this,"displayedEdgeLabels",new Set),D(this,"edgeLabelCandidates",[]),D(this,"renderedNodeLabels",new Set),D(this,"labelSizeCache",new Map),D(this,"framePassPoints",new Float32Array(0)),D(this,"labelsDirty",!0),this.internals=n}return ne(a,[{key:"resetFrame",value:function(){this.displayedNodeLabels=new Set,this.renderedNodeLabels=new Set,this.labelSizeCache.clear()}},{key:"clearEdgeLabels",value:function(){this.displayedEdgeLabels=new Set}},{key:"resetLabelGrid",value:function(){this.labelGrid=new La,this.edgeAnchorGrid=new La}},{key:"processWebGLLabels",value:function(e){for(var t,r=this.internals,i=r.labelProgram,o=r.primitives,s=r.nodeDataCache,l=(o==null||(t=o.nodes)===null||t===void 0||(t=t.label)===null||t===void 0||(t=t.font)===null||t===void 0?void 0:t.family)||"sans-serif",u=new Map,d=0,h=e.length;d<h;d++){var c=e[d],f=s[c];if(!(f.visibility==="hidden"||!f.label)){var g=f.labelFont||l,y=u.get(g);y?y.push(f.label):u.set(g,[f.label])}}var m=O(u),v;try{for(m.s();!(v=m.n()).done;){var p=ie(v.value,2),b=p[0],T=p[1],_=pa(b),E=_.family,A=_.weight,w=_.style,S=i.registerFont(E,A,w);i.ensureGlyphsReady(T,S)}}catch(C){m.e(C)}finally{m.f()}}},{key:"measureNodeLabel",value:function(e){var t,r;if(!e.label)return{width:0,height:0,textHeight:0};var i=this.internals,o=i.labelProgram,s=i.primitives,l=(t=e.labelSize)!==null&&t!==void 0?t:14,u=e.labelFont||(s==null||(r=s.nodes)===null||r===void 0||(r=r.label)===null||r===void 0||(r=r.font)===null||r===void 0?void 0:r.family)||"sans-serif",d="".concat(e.label,"|").concat(l,"|").concat(u);if(this.labelSizeCache.has(d))return this.labelSizeCache.get(d);var h=pa(u),c=h.family,f=h.weight,g=h.style,y=o.registerFont(c,f,g),m=o.measureLabel(e.label,l,y);return this.labelSizeCache.set(d,m),m}},{key:"nodeLabelBox",value:function(e,t){var r,i,o,s,l;if(e.visibility==="hidden"||e.labelVisibility==="hidden")return null;var u=this.measureNodeLabel(e),d=u.width,h=u.height,c=u.textHeight;if(!d)return null;var f=(r=(i=this.internals.primitives)===null||i===void 0||(i=i.nodes)===null||i===void 0||(i=i.label)===null||i===void 0?void 0:i.margin)!==null&&r!==void 0?r:an,g=t+f,y=e.labelBackgroundColor?(o=e.labelBackgroundPadding)!==null&&o!==void 0?o:mr:0,m=d/2,v=h/2,p=m+y,b=v+y,T=c/2,_=0,E=0;switch((s=e.labelPosition)!==null&&s!==void 0?s:"right"){case"left":_=-(g+m);break;case"above":E=-(g+T);break;case"below":E=g+T;break;case"over":break;default:_=g+m}var A=(l=e.labelAngle)!==null&&l!==void 0?l:0,w=ja({x:_,y:E},A),S=w.x,C=w.y,G=Math.abs(Math.cos(A)),L=Math.abs(Math.sin(A)),N=G*p+L*b,k=L*p+G*b;return{minX:S-N,maxX:S+N,minY:C-k,maxY:C+k}}},{key:"computeDisplayedNodeLabels",value:function(){var e=this.internals.getCameraState(),t=this.internals.getDimensions(),r=t.width,i=t.height,o=this.internals.viewportToFramedGraph({x:-un,y:-dn}),s=this.internals.viewportToFramedGraph({x:r+un,y:-dn}),l=this.internals.viewportToFramedGraph({x:-un,y:i+dn}),u=this.internals.viewportToFramedGraph({x:r+un,y:i+dn}),d=Math.min(o.x,s.x,l.x,u.x),h=Math.max(o.x,s.x,l.x,u.x),c=Math.min(o.y,s.y,l.y,u.y),f=Math.max(o.y,s.y,l.y,u.y),g=ft({x:.5,y:.5,ratio:1,angle:0},{width:r,height:i},this.internals.getGraphDimensions(),this.internals.getStagePadding()),y=function(P){var U=Yt(g,P);return{x:(1+U.x)*r/2,y:(1-U.y)*i/2}},m=y({x:d,y:c}),v=y({x:h,y:c}),p=y({x:d,y:f}),b=y({x:h,y:f}),T={x1:Math.min(m.x,v.x,p.x,b.x),y1:Math.min(m.y,v.y,p.y,b.y),x2:Math.max(m.x,v.x,p.x,b.x),y2:Math.max(m.y,v.y,p.y,b.y)},_=this.internals,E=_.settings,A=_.nodeDataCache,w=_.nodesWithForcedLabels,S=this.labelGrid.getLabelsToDisplay(e.ratio,E.labelDensity,T);sr(S,w);for(var C=0,G=S.length;C<G;C++){var L=S[C],N=A[L];if(!this.displayedNodeLabels.has(L)&&!(N.visibility==="hidden"||N.labelVisibility==="hidden")&&N.label&&!(N.x<d||N.x>h||N.y<c||N.y>f)){var k=this.internals.framedGraphToViewport(N),I=k.x,W=k.y,F=this.internals.scaleSize(N.size);!vt(N)&&F<E.labelRenderedSizeThreshold||I<-un-F||I>r+un+F||W<-dn-F||W>i+dn+F||this.displayedNodeLabels.add(L)}}}},{key:"buildFramePassPoints",value:function(){var e=this.internals,t=e.nodeDataCache,r=e.nodeDataTexture;if(!r)return{data:this.framePassPoints,count:0};var i=this.displayedNodeLabels.size*3;this.framePassPoints.length<i&&(this.framePassPoints=new Float32Array(i));var o=this.framePassPoints,s=0,l=O(this.displayedNodeLabels),u;try{for(l.s();!(u=l.n()).done;){var d,h,c=u.value,f=t[c];if(f){var g=r.getIndex(c);g<0||(o[s*3]=g,o[s*3+1]=(d=nn[f.labelPosition||st.labelPosition])!==null&&d!==void 0?d:0,o[s*3+2]=(h=f.labelAngle)!==null&&h!==void 0?h:0,s++)}}}catch(y){l.e(y)}finally{l.f()}return{data:o,count:s}}},{key:"renderWebGLLabels",value:function(e,t){var r=this.internals,i=r.nodeDataCache,o=r.labelProgram,s=r.primitives,l=r.nodeDataTexture,u=[],d=O(this.displayedNodeLabels),h;try{for(d.s();!(h=d.n()).done;){var c=h.value;if(!this.renderedNodeLabels.has(c)){var f=i[c];t&&f.labelDepth!==t||(this.renderedNodeLabels.add(c),u.push(c))}}}catch(de){d.e(de)}finally{d.f()}if(u.length!==0){if(this.labelsDirty){for(var g,y,m,v=0,p=0,b=u.length;p<b;p++){var T=i[u[p]];v+=T.label.length}o.reallocate(v);for(var _=14,E=(g=s==null||(y=s.nodes)===null||y===void 0||(y=y.label)===null||y===void 0?void 0:y.margin)!==null&&g!==void 0?g:an,A=st.labelPosition,w=(s==null||(m=s.nodes)===null||m===void 0||(m=m.label)===null||m===void 0||(m=m.font)===null||m===void 0?void 0:m.family)||"sans-serif",S=new Map,C=0,G=0,L=u.length;G<L;G++){var N,k,I,W,F=u[G],x=i[F],P=x.labelFont||w,U=S.get(P);if(U===void 0){var z=pa(P),R=z.family,j=z.weight,q=z.style;U=o.registerFont(R,j,q),S.set(P,U)}var Z={text:x.label,x:x.x,y:x.y,size:(N=x.labelSize)!==null&&N!==void 0?N:_,color:x.labelColor,nodeSize:x.size,margin:E,position:(k=x.labelPosition)!==null&&k!==void 0?k:A,hidden:!1,forceLabel:vt(x),type:"default",zIndex:(I=x.zIndex)!==null&&I!==void 0?I:0,parentType:"node",parentKey:F,fontKey:U,labelAngle:(W=x.labelAngle)!==null&&W!==void 0?W:0,nodeIndex:l.getIndex(F)},Se=o.processLabel(F,C,Z);C+=Se}o.invalidateBuffers()}o.render(e)}}},{key:"renderBackdrops",value:function(e,t){var r=this.internals,i=r.backdropProgram,o=r.nodeDataCache,s=r.nodesWithBackdrop,l=r.attachmentManager,u=r.pixelRatio,d=r.nodeDataTexture,h=[],c=O(s),f;try{for(c.s();!(f=c.n()).done;){var g,y=f.value,m=o[y];if(!(!m||m.visibility==="hidden")&&!(t&&m.depth!==t)){var v=(g=d?.getIndex(y))!==null&&g!==void 0?g:-1;v<0||h.push({key:y,nodeIndex:v})}}}catch(Y){c.e(Y)}finally{c.f()}if(h.length!==0){i.reallocate(h.length);for(var p=0;p<h.length;p++){var b,T,_,E,A,w,S,C,G=h[p],L=G.key,N=G.nodeIndex,k=o[L],I=this.displayedNodeLabels.has(L),W=I?this.measureNodeLabel(k):{width:0,height:0,textHeight:0},F=W.textHeight,x=W.width,P=W.height,U=0,z=0;if(I&&k.labelAttachment&&l){var R=l.getEntry(L,k.labelAttachment);if(R){var j=k.labelAttachmentPlacement||"below";if(j==="below"||j==="above"){var q=R.height/u;P+=q+yt,x=Math.max(x,R.width/u),z=j==="below"?(q+yt)/2:-(q+yt)/2}else{var Z=R.width/u;x+=Z+yt,P=Math.max(P,R.height/u),U=j==="right"?(Z+yt)/2:-(Z+yt)/2}}}var Se=k.backdropColor?gt(k.backdropColor):[255,255,255,255],de=k.backdropShadowColor?gt(k.backdropShadowColor):[0,0,0,128],K=Se.map(function(Y){return Y/255}),Ke=de.map(function(Y){return Y/255}),De=(b=k.backdropShadowBlur)!==null&&b!==void 0?b:12,_t=(T=k.backdropPadding)!==null&&T!==void 0?T:6,Ve=k.backdropBorderColor?gt(k.backdropBorderColor):[0,0,0,0],Fa=Ve.map(function(Y){return Y/255}),Gt=(_=k.backdropBorderWidth)!==null&&_!==void 0?_:0,ge=(E=k.backdropCornerRadius)!==null&&E!==void 0?E:0,oe=(A=k.backdropLabelPadding)!==null&&A!==void 0?A:-1,se=oe<0?_t:oe,qe=(w=of[(S=k.backdropArea)!==null&&S!==void 0?S:"both"])!==null&&w!==void 0?w:0,ee={key:L,nodeIndex:N,label:k.label,labelWidth:x,labelHeight:P,textHeight:F,type:"default",position:k.labelPosition||st.labelPosition,labelAngle:(C=k.labelAngle)!==null&&C!==void 0?C:0,backdropColor:K,backdropShadowColor:Ke,backdropShadowBlur:De,backdropPadding:_t,backdropBorderColor:Fa,backdropBorderWidth:Gt,backdropCornerRadius:ge,backdropLabelPadding:se,backdropArea:qe,labelBoxOffset:[U,z]};i.processBackdrop(p,ee)}i.invalidateBuffers(),i.render(e)}}},{key:"renderLabelBackgrounds",value:function(e,t){var r=this.internals,i=r.labelBackgroundProgram,o=r.nodeDataCache,s=r.nodeDataTexture,l=Ce.nodeLabel.writesPickingThisFrame(this.internals),u=[],d=O(this.displayedNodeLabels),h;try{for(d.s();!(h=d.n()).done;){var c=h.value,f=o[c];!f||f.visibility==="hidden"||t&&f.labelDepth!==t||!l&&!f.labelBackgroundColor||u.push(c)}}catch(N){d.e(N)}finally{d.f()}if(u.length!==0){i.reallocate(u.length);for(var g=0;g<u.length;g++){var y,m,v,p,b=u[g],T=o[b],_=(y=s?.getIndex(b))!==null&&y!==void 0?y:-1;if(!(_<0)){var E=this.measureNodeLabel(T),A=E.width,w=E.height,S=E.textHeight,C=Ft(this.internals.pickingState,"nodeLabel",b)||Ft(this.internals.pickingState,"node",b),G=T.labelBackgroundColor?Be(T.labelBackgroundColor):Be("transparent"),L={nodeIndex:_,id:Kt(C),color:G,labelWidth:A,labelHeight:w,textHeight:S,positionMode:(m=nn[T.labelPosition||st.labelPosition])!==null&&m!==void 0?m:0,labelAngle:(v=T.labelAngle)!==null&&v!==void 0?v:0,padding:(p=T.labelBackgroundPadding)!==null&&p!==void 0?p:mr};i.processLabelBackground(g,L)}}i.invalidateBuffers(),i.render(e)}}},{key:"cacheAttachments",value:function(e){var t=this.internals,r=t.attachmentManager,i=t.pixelRatio,o=t.nodeDataCache,s=t.nodesWithBackdrop,l=t.graph;if(r){var u=O(s),d;try{for(u.s();!(d=u.n()).done;){var h=d.value;if(this.displayedNodeLabels.has(h)){var c=o[h];if(!(!c||c.visibility==="hidden")&&!(e&&c.depth!==e)&&c.labelAttachment){var f=l.getNodeAttributes(h),g=this.measureNodeLabel(c),y=g.width,m=g.height,v={node:h,attributes:f,pixelRatio:i,labelWidth:y,labelHeight:m};r.renderAttachment(h,c.labelAttachment,v)}}}}catch(p){u.e(p)}finally{u.f()}r.regenerateAtlas()}}},{key:"renderAttachments",value:function(e,t){var r=this.internals,i=r.attachmentManager,o=r.attachmentProgram,s=r.nodeDataCache,l=r.nodesWithBackdrop,u=r.pixelRatio,d=r.nodeDataTexture;if(!(!i||!o)){var h=0;o.reallocateAttachments(l.size);var c=O(l),f;try{for(c.s();!(f=c.n()).done;){var g,y,m,v,p=f.value;if(this.displayedNodeLabels.has(p)){var b=s[p];if(!(!b||b.visibility==="hidden")&&!(t&&b.labelDepth!==t)&&b.labelAttachment){var T=i.getEntry(p,b.labelAttachment);if(T){var _=(g=d?.getIndex(p))!==null&&g!==void 0?g:-1;if(!(_<0)){var E=this.measureNodeLabel(b),A=E.width,w=E.height,S=E.textHeight,C=(y=qo[b.labelAttachmentPlacement||"below"])!==null&&y!==void 0?y:0;o.processAttachment(h,{nodeIndex:_,atlasX:T.x,atlasY:T.y,atlasW:T.width,atlasH:T.height,attachWidth:T.width/u,attachHeight:T.height/u,positionMode:(m=nn[b.labelPosition||st.labelPosition])!==null&&m!==void 0?m:0,attachmentPlacement:C,labelWidth:A,labelHeight:w,textHeight:S,labelAngle:(v=b.labelAngle)!==null&&v!==void 0?v:0}),h++}}}}}}catch(G){c.e(G)}finally{c.f()}h!==0&&(o.reallocateAttachments(h),i.bindTexture(Cn),o.invalidateBuffers(),o.render(e))}}},{key:"computeDisplayedEdgeLabels",value:function(){var e=this.internals,t=e.graph,r=e.stateManager,i=e.settings,o=e.edgesWithForcedLabels,s=r.getHighlightedNodes(),l=i.edgeLabelAnchors==="allNodes"?new Set(this.edgeAnchorGrid.getLabelsToDisplay(this.internals.getCameraState().ratio,i.labelDensity)):this.displayedNodeLabels,u=r.hovered,d=rf({graph:t,hoveredNode:u?.kind==="node"?u.key:null,displayedNodeLabels:l,highlightedNodes:s});sr(d,o),this.edgeLabelCandidates=d,this.displayedEdgeLabels=new Set}},{key:"filterEdgeLabelsForDepth",value:function(e){for(var t=this.internals,r=t.graph,i=t.nodeDataCache,o=t.edgeDataCache,s=[],l=new Set,u=0,d=this.edgeLabelCandidates.length;u<d;u++){var h=this.edgeLabelCandidates[u];if(!l.has(h)){l.add(h);var c=r.extremities(h),f=i[c[0]],g=i[c[1]],y=o[h];!y||!f||!g||y.visibility==="hidden"||y.labelVisibility==="hidden"||f.visibility==="hidden"||g.visibility==="hidden"||e&&y.labelDepth!==e||y.label&&s.push(h)}}return s}},{key:"renderEdgeLabels",value:function(e,t){var r=this.internals,i=r.graph,o=r.nodeDataCache,s=r.edgeDataCache,l=r.primitives,u=r.edgeLabelProgram,d=r.nodeDataTexture,h=r.edgeDataTexture;if(u){var c=this.filterEdgeLabelsForDepth(t),f=O(c),g;try{for(f.s();!(g=f.n()).done;){var y=g.value;this.displayedEdgeLabels.add(y)}}catch(Z){f.e(Z)}finally{f.f()}if(c.length!==0){if(this.labelsDirty){var m,v,p=0,b=O(c),T;try{for(b.s();!(T=b.n()).done;){var _=T.value;p+=s[_].label.length}}catch(Z){b.e(Z)}finally{b.f()}u.reallocate(p);var E=(m=l==null||(v=l.edges)===null||v===void 0||(v=v.label)===null||v===void 0?void 0:v.margin)!==null&&m!==void 0?m:5,A="over",w=0,S=O(c),C;try{for(S.s();!(C=S.n()).done;){var G,L,N=C.value,k=i.extremities(N),I=k[0],W=k[1],F=o[I],x=o[W],P=s[N],U=d.getIndex(I),z=d.getIndex(W),R=h.getIndex(N),j={text:P.label,x:(F.x+x.x)/2,y:(F.y+x.y)/2,size:Rs,color:P.labelColor,nodeSize:0,nodeIndex:-1,margin:E,position:(G=P.labelPosition)!==null&&G!==void 0?G:A,hidden:!1,forceLabel:vt(P),type:"default",zIndex:(L=P.zIndex)!==null&&L!==void 0?L:0,parentType:"edge",parentKey:N,fontKey:"",labelAngle:0,sourceX:F.x,sourceY:F.y,targetX:x.x,targetY:x.y,sourceSize:F.size,targetSize:x.size,sourceShape:F.shape||"circle",targetShape:x.shape||"circle",edgeSize:P.size,offset:0,edgeAttributes:P,sourceNodeIndex:U,targetNodeIndex:z,edgeIndex:R},q=u.processEdgeLabel(N,w,j);w+=q}}catch(Z){S.e(Z)}finally{S.f()}u.invalidateBuffers()}u.render(e)}}}},{key:"renderEdgeLabelBackgrounds",value:function(e,t){var r,i,o=this.internals,s=o.edgeLabelBackgroundProgram,l=o.edgeLabelProgram,u=o.edgeDataCache,d=o.primitives,h=o.edgeDataTexture;if(!(!h||!l||!s)){var c=Ce.edgeLabel.writesPickingThisFrame(this.internals),f=(r=d==null||(i=d.edges)===null||i===void 0||(i=i.label)===null||i===void 0?void 0:i.margin)!==null&&r!==void 0?r:5,g="over",y=this.filterEdgeLabelsForDepth(t),m=[],v=O(y),p;try{for(v.s();!(p=v.n()).done;){var b=p.value;!c&&!u[b].labelBackgroundColor||m.push(b)}}catch(F){v.e(F)}finally{v.f()}if(m.length!==0){s.reallocate(m.length);for(var T=0;T<m.length;T++){var _,E,A,w=m[T],S=u[w],C=S.label,G=l.measureLabelAtlasWidth(C),L=(_=S.labelPosition)!==null&&_!==void 0?_:g,N=typeof L=="string"&&(E=sf[L])!==null&&E!==void 0?E:0,k=Ft(this.internals.pickingState,"edgeLabel",w)||Ft(this.internals.pickingState,"edge",w),I=S.labelBackgroundColor?Be(S.labelBackgroundColor):Be("transparent"),W={edgeIndex:h.getIndex(w),baseFontSize:Rs,totalTextWidth:G,positionMode:N,margin:f,padding:(A=S.labelBackgroundPadding)!==null&&A!==void 0?A:lf,color:I,id:Kt(k),edgeAttributes:S};s.processEdgeLabelBackground(T,w,W)}s.invalidateBuffers(),s.render(e)}}}}])})(),df=(function(){function a(n,e,t,r){te(this,a),D(this,"nodeStates",new Map),D(this,"edgeStates",new Map),D(this,"hovered",null),D(this,"dirtyNodes",new Set),D(this,"dirtyEdges",new Set),D(this,"graphStateChanged",!1),D(this,"graphStateFlagsDirty",!1),this.scheduleRefresh=n,this.customNodeStateDefaults=e,this.customEdgeStateDefaults=t,this.customGraphStateDefaults=r,this.graphState=er(r)}return ne(a,[{key:"getNodeState",value:function(e){e=""+e;var t=this.nodeStates.get(e);return t||(t=mo(this.customNodeStateDefaults),this.nodeStates.set(e,t)),t}},{key:"getEdgeState",value:function(e){e=""+e;var t=this.edgeStates.get(e);return t||(t=yo(this.customEdgeStateDefaults),this.edgeStates.set(e,t)),t}},{key:"getGraphState",value:function(){return this.flushGraphStateFlags(),this.graphState}},{key:"getHighlightedNodes",value:function(){var e=new Set,t=O(this.nodeStates),r;try{for(t.s();!(r=t.n()).done;){var i=ie(r.value,2),o=i[0],s=i[1];s.isHighlighted&&e.add(o)}}catch(l){t.e(l)}finally{t.f()}return e}},{key:"setNodeState",value:function(e,t){e=""+e;var r=this.getNodeState(e);if(Jt(r,t)){var i=H(H({},r),t);this.nodeStates.set(e,i),this.dirtyNodes.add(e),this.updateHoveredNodeTracking(e,r,i),this.graphStateFlagsDirty=!0,this.scheduleRefresh()}}},{key:"setEdgeState",value:function(e,t){e=""+e;var r=this.getEdgeState(e);if(Jt(r,t)){var i=H(H({},r),t);this.edgeStates.set(e,i),this.dirtyEdges.add(e),this.updateHoveredEdgeTracking(e,r,i),this.graphStateFlagsDirty=!0,this.scheduleRefresh()}}},{key:"setGraphState",value:function(e){if(Jt(this.graphState,e)){var t=H(H({},this.graphState),e);t.isIdle=!t.isPanning&&!t.isZooming&&!t.isDragging,this.graphState=t,this.graphStateChanged=!0,this.scheduleRefresh()}}},{key:"setNodesState",value:function(e,t){var r=!1,i=O(e),o;try{for(i.s();!(o=i.n()).done;){var s=o.value;s=""+s;var l=this.getNodeState(s);if(Jt(l,t)){var u=H(H({},l),t);this.nodeStates.set(s,u),this.dirtyNodes.add(s),this.updateHoveredNodeTracking(s,l,u),r=!0}}}catch(d){i.e(d)}finally{i.f()}r&&(this.graphStateFlagsDirty=!0,this.scheduleRefresh())}},{key:"setEdgesState",value:function(e,t){var r=!1,i=O(e),o;try{for(i.s();!(o=i.n()).done;){var s=o.value;s=""+s;var l=this.getEdgeState(s);if(Jt(l,t)){var u=H(H({},l),t);this.edgeStates.set(s,u),this.dirtyEdges.add(s),this.updateHoveredEdgeTracking(s,l,u),r=!0}}}catch(d){i.e(d)}finally{i.f()}r&&(this.graphStateFlagsDirty=!0,this.scheduleRefresh())}},{key:"removeNode",value:function(e){this.nodeStates.delete(e),this.dirtyNodes.delete(e),this.clearHoveredFor("node",e)}},{key:"removeEdge",value:function(e){this.edgeStates.delete(e),this.dirtyEdges.delete(e),this.clearHoveredFor("edge",e)}},{key:"pruneNodes",value:function(e){var t=O(this.nodeStates.keys()),r;try{for(t.s();!(r=t.n()).done;){var i=r.value;e(i)||this.removeNode(i)}}catch(o){t.e(o)}finally{t.f()}}},{key:"pruneEdges",value:function(e){var t=O(this.edgeStates.keys()),r;try{for(t.s();!(r=t.n()).done;){var i=r.value;e(i)||this.removeEdge(i)}}catch(o){t.e(o)}finally{t.f()}}},{key:"clearNodes",value:function(){this.nodeStates.clear(),this.dirtyNodes.clear(),this.clearHoveredForKinds(Lr("node"))}},{key:"clearEdges",value:function(){this.edgeStates.clear(),this.dirtyEdges.clear(),this.clearHoveredForKinds(Lr("edge"))}},{key:"resetGraphState",value:function(){this.graphState=er(this.customGraphStateDefaults),this.graphStateChanged=!1,this.graphStateFlagsDirty=!1}},{key:"clearDirtyTracking",value:function(){this.dirtyNodes.clear(),this.dirtyEdges.clear(),this.graphStateChanged=!1}},{key:"setHovered",value:function(e){this.hovered=e}},{key:"clearHoveredFor",value:function(e,t){this.hovered&&this.hovered.key===t&&Lr(e).includes(this.hovered.kind)&&(this.hovered=null)}},{key:"clearHoveredForKinds",value:function(e){this.hovered&&e.includes(this.hovered.kind)&&(this.hovered=null)}},{key:"updateGraphStateFromNodes",value:function(){var e,t=!1,r=!1,i=!1,o=O(this.nodeStates),s;try{for(o.s();!(s=o.n()).done;){var l=ie(s.value,2),u=l[1];if(u.isHovered&&(t=!0),u.isHighlighted&&(r=!0),u.isDragged&&(i=!0),t&&r&&i)break}}catch(h){o.e(h)}finally{o.f()}!t&&((e=this.hovered)===null||e===void 0?void 0:e.kind)==="edge"&&(t=!0);var d=!this.graphState.isPanning&&!this.graphState.isZooming&&!i;(this.graphState.hasHovered!==t||this.graphState.hasHighlighted!==r||this.graphState.isDragging!==i||this.graphState.isIdle!==d)&&(this.graphStateChanged=!0),this.graphState=H(H({},this.graphState),{},{hasHovered:t,hasHighlighted:r,isDragging:i,isIdle:d})}},{key:"updateGraphStateFromEdges",value:function(){var e,t=((e=this.hovered)===null||e===void 0?void 0:e.kind)==="node";if(!t){var r=O(this.edgeStates),i;try{for(r.s();!(i=r.n()).done;){var o=ie(i.value,2),s=o[1];if(s.isHovered){t=!0;break}}}catch(l){r.e(l)}finally{r.f()}}this.graphState.hasHovered!==t&&(this.graphStateChanged=!0),this.graphState=H(H({},this.graphState),{},{hasHovered:t})}},{key:"flushGraphStateFlags",value:function(){this.graphStateFlagsDirty&&(this.updateGraphStateFromNodes(),this.updateGraphStateFromEdges(),this.graphStateFlagsDirty=!1)}},{key:"updateHoveredNodeTracking",value:function(e,t,r){var i;if(t.isHovered!==r.isHovered)if(r.isHovered){var o;if(((o=this.hovered)===null||o===void 0?void 0:o.kind)==="node"&&this.hovered.key!==e){var s=this.hovered.key,l=this.getNodeState(s);this.nodeStates.set(s,H(H({},l),{},{isHovered:!1})),this.dirtyNodes.add(s)}this.hovered={kind:"node",key:e}}else((i=this.hovered)===null||i===void 0?void 0:i.kind)==="node"&&this.hovered.key===e&&(this.hovered=null)}},{key:"updateHoveredEdgeTracking",value:function(e,t,r){var i;if(t.isHovered!==r.isHovered)if(r.isHovered){var o;if(((o=this.hovered)===null||o===void 0?void 0:o.kind)==="edge"&&this.hovered.key!==e){var s=this.hovered.key,l=this.getEdgeState(s);this.edgeStates.set(s,H(H({},l),{},{isHovered:!1})),this.dirtyEdges.add(s)}this.hovered={kind:"edge",key:e}}else((i=this.hovered)===null||i===void 0?void 0:i.kind)==="edge"&&this.hovered.key===e&&(this.hovered=null)}}])})(),Cs=1,Ls=2,ks=3,Ps=4,hf=(function(a){function n(e,t){var r,i,o,s,l,u=arguments.length>2&&arguments[2]!==void 0?arguments[2]:{};te(this,n),l=me(this,n),D(l,"nodeReducer",null),D(l,"edgeReducer",null),D(l,"stageCanvas",null),D(l,"mouseLayer",null),D(l,"gestureHint",null),D(l,"extraElements",{}),D(l,"webGLContext",null),D(l,"pickingFrameBuffer",null),D(l,"pickingTexture",null),D(l,"pickingDepthBuffer",null),D(l,"activeListeners",{}),D(l,"nodeVariableEntries",[]),D(l,"edgeVariableEntries",[]),D(l,"edgePathsByName",new Map),D(l,"nodeProgramIndex",{}),D(l,"edgeProgramIndex",{}),D(l,"edgeTextureIndexCache",{}),D(l,"nodeGraphCoords",{}),D(l,"nodeExtent",{x:[0,1],y:[0,1]}),D(l,"matrix",Oe()),D(l,"invMatrix",Oe()),D(l,"correctionRatio",1),D(l,"frameId",0),D(l,"customBBox",null),D(l,"gpuTimerExt",void 0),D(l,"activeGpuTimerQuery",null),D(l,"pendingGpuTimerQueries",[]),D(l,"normalizationFunction",fa({x:[0,1],y:[0,1]})),D(l,"graphToViewportRatio",1),D(l,"pickingState",Mc()),D(l,"prevNodeVisibilities",{}),D(l,"width",0),D(l,"height",0),D(l,"autoRescaleFrozen",!1),D(l,"stylesDeclaration",null),D(l,"resolvedStageStyle",{}),D(l,"renderFrame",null),D(l,"contextLost",!1),D(l,"pendingProcess","full"),D(l,"needToRefreshState",!1),D(l,"checkEdgesEventsFrame",null),D(l,"edgeStyleAnalysis",{dependency:"static",xAttribute:null,yAttribute:null}),D(l,"depthLayers",Q(oa)),D(l,"customLayerPrograms",new Map),D(l,"nodeShapeSlug",null),D(l,"sdfAtlas",null),D(l,"depthRanges",{nodes:{},edges:{}}),D(l,"nodeBaseDepth",{}),D(l,"edgeBaseDepth",{});var d=u.primitives,h=u.styles,c=u.settings,f=c===void 0?{}:c,g=u.nodeReducer,y=u.edgeReducer,m=u.customNodeState,v=u.customEdgeState,p=u.customGraphState;l.stateManager=new df(function(){return l.scheduleStateRefresh()},m,v,p);var b=d??xo;l.stylesDeclaration=h?{nodes:(r=h.nodes)!==null&&r!==void 0?r:ua.nodes,edges:(i=h.edges)!==null&&i!==void 0?i:ua.edges,stage:h.stage}:ua,l.nodeReducer=g??null,l.edgeReducer=y??null;var T=tr(l.stylesDeclaration.nodes);l.nodeReducer&&(T.dependency="graph-state"),l.edgeStyleAnalysis=tr(l.stylesDeclaration.edges),l.edgeReducer&&(l.edgeStyleAnalysis.dependency="graph-state"),l.stylesDeclaration.stage&&(l.resolvedStageStyle=or(l.stylesDeclaration.stage,l.stateManager.graphState));var _=Do(f);if(va(_),_.enableNodeDrag){var E=T.xAttribute,A=T.yAttribute;if((!E||!A)&&!_.dragPositionToAttributes)throw new Error('Sigma: `enableNodeDrag` is true but position attribute names could not be inferred from styles. Either use attribute bindings for x/y in your node styles (e.g. `x: { attribute: "x" }`), or provide a `dragPositionToAttributes` setting.')}if(Ao(e),!(t instanceof HTMLElement))throw new Error("Sigma: container should be an html element.");l.container=t,l.edgeGroups=new Nc(e,function(x,P){for(var U=0;U<x.length;U++){var z=l.stateManager.getEdgeState(x[U]);z.parallelIndex=U,z.parallelCount=P}});var w=new zc(e,l.viewportToGraph.bind(l),l.setNodesState.bind(l),function(x,P){return l.emit(x,P)});if(l.depthLayers=(o=b.depthLayers)!==null&&o!==void 0?o:Q(oa),!(h!=null&&h.nodes)&&!ra.every(function(x){return l.depthLayers.includes(x)}))throw new Error("Sigma: depthLayers must include ".concat(ra.join(", ")," for the built-in node styles."));if(!(h!=null&&h.edges)&&!ia.every(function(x){return l.depthLayers.includes(x)}))throw new Error("Sigma: depthLayers must include ".concat(ia.join(", ")," for the built-in edge styles."));l.itemBuckets={nodes:new Ar(l.depthLayers),edges:new Ar(l.depthLayers)},l.initWebGLContext(),l.mouseLayer=en("div",{position:"absolute",touchAction:"none",userSelect:"none"},{class:"sigma-mouse"}),l.container.appendChild(l.mouseLayer),l.resolvedStageStyle.background&&(l.container.style.backgroundColor=l.resolvedStageStyle.background),l.resolvedStageStyle.cursor&&(l.container.style.cursor=l.resolvedStageStyle.cursor);var S=new gs(l.webGLContext),C=new Dr(l.webGLContext,{channels:1}),G=new vs(l.webGLContext),L=new Dr(l.webGLContext,{channels:4}),N=l.webGLContext,k=new af({gl:N,getFrameBuffer:function(){return l.pickingFrameBuffer},getPixelRatio:function(){return l.internals.pixelRatio},getDownSizingRatio:function(){return l.internals.settings.pickingDownSizingRatio},isRenderPending:function(){return l.renderFrame!==null},onIndex:function(P,U){var z;return zs(l.internals,(z=l.pickingState.lookup[P])!==null&&z!==void 0?z:null,U)}}),I=l.initPrograms(b,_),W=b==null||(s=b.nodes)===null||s===void 0?void 0:s.labelAttachments,F=null;return W&&Object.keys(W).length>0&&(F=new fs(N,W,function(){return l.scheduleRender()})),l.internals=H(H({nodeDataCache:{},edgeDataCache:{},nodesWithForcedLabels:new Set,nodesWithBackdrop:new Set,edgesWithForcedLabels:new Set,settings:_,primitives:b,pixelRatio:Tn(),graph:e,stateManager:l.stateManager,dragManager:w,hoverResolver:k,nodeStyleAnalysis:T,pickingState:l.pickingState},I),{},{attachmentManager:F,nodeDataTexture:S,nodeFrameTexture:C,edgeDataTexture:G,edgeFrameTexture:L,getDimensions:function(){return l.getDimensions()},getGraphDimensions:function(){return l.getGraphDimensions()},getStagePadding:function(){return l.getStagePadding()},getCameraState:function(){return l.camera.getState()},getHitAtPosition:function(P){return l.getHitAtPosition(P)},setNodeState:function(P,U){return l.setNodeState(P,U)},setEdgeState:function(P,U){return l.setEdgeState(P,U)},updateContainerCursor:function(){return l.updateContainerCursor()},scheduleRefresh:function(){return l.scheduleRefresh()},viewportToFramedGraph:function(P){return l.viewportToFramedGraph(P)},viewportToGraph:function(P){return l.viewportToGraph(P)},framedGraphToViewport:function(P){return l.framedGraphToViewport(P)},scaleSize:function(P){return l.scaleSize(P)},emit:function(P,U){return l.emit(P,U)}}),l.labelRenderer=new uf(l.internals),l.resize(),l.initializeWebGLLabels(),l.camera=new ys,l.bindCameraHandlers(),l.mouseCaptor=new Pc(l.mouseLayer,l),l.mouseCaptor.setSettings(l.internals.settings),l.touchCaptor=new Gc(l.mouseLayer,l),l.touchCaptor.setSettings(l.internals.settings),l.bindEventHandlers(),l.bindGraphHandlers(),l.handleSettingsUpdate(),l.refresh(),l}return ye(n,a),ne(n,[{key:"initializeWebGLLabels",value:function(){this.sdfAtlas=new Rt,this.sdfAtlas.registerFont({family:"sans-serif",weight:"normal",style:"normal"})}},{key:"resetWebGLTexture",value:function(){var t=this.webGLContext;if(!this.pickingFrameBuffer)return this;var r=Math.ceil(this.width*this.internals.pixelRatio/this.internals.settings.pickingDownSizingRatio),i=Math.ceil(this.height*this.internals.pixelRatio/this.internals.settings.pickingDownSizingRatio);t.bindFramebuffer(t.FRAMEBUFFER,this.pickingFrameBuffer),this.pickingTexture&&t.deleteTexture(this.pickingTexture);var o=t.createTexture();o&&(t.bindTexture(t.TEXTURE_2D,o),t.texImage2D(t.TEXTURE_2D,0,t.RGBA,r,i,0,t.RGBA,t.UNSIGNED_BYTE,null),t.texParameteri(t.TEXTURE_2D,t.TEXTURE_MIN_FILTER,t.NEAREST),t.texParameteri(t.TEXTURE_2D,t.TEXTURE_MAG_FILTER,t.NEAREST),t.framebufferTexture2D(t.FRAMEBUFFER,t.COLOR_ATTACHMENT0,t.TEXTURE_2D,o,0),this.pickingTexture=o),this.pickingDepthBuffer&&t.deleteRenderbuffer(this.pickingDepthBuffer);var s=t.createRenderbuffer();return s&&(t.bindRenderbuffer(t.RENDERBUFFER,s),t.renderbufferStorage(t.RENDERBUFFER,t.DEPTH_COMPONENT16,r,i),t.framebufferRenderbuffer(t.FRAMEBUFFER,t.DEPTH_ATTACHMENT,t.RENDERBUFFER,s),this.pickingDepthBuffer=s),t.bindFramebuffer(t.FRAMEBUFFER,null),this}},{key:"bindCameraHandlers",value:function(){var t=this;return this.activeListeners.camera=function(){t.refreshMatrices(),t.labelRenderer.labelsDirty=!0,t.scheduleRender()},this.activeListeners.cameraAnimationStart=function(r){var i=r.from,o=r.to;i.ratio!==o.ratio&&t.stateManager.setGraphState({isZooming:!0})},this.activeListeners.cameraAnimationEnd=function(){t.stateManager.setGraphState({isZooming:!1})},this.camera.on("updated",this.activeListeners.camera),this.camera.on("animationStart",this.activeListeners.cameraAnimationStart),this.camera.on("animationEnd",this.activeListeners.cameraAnimationEnd),this}},{key:"unbindCameraHandlers",value:function(){return this.camera.removeListener("updated",this.activeListeners.camera),this.camera.removeListener("animationStart",this.activeListeners.cameraAnimationStart),this.camera.removeListener("animationEnd",this.activeListeners.cameraAnimationEnd),this}},{key:"getHitAtPosition",value:function(t){var r;if(this.contextLost)return null;var i=this.webGLContext;i.bindFramebuffer(i.FRAMEBUFFER,this.pickingFrameBuffer);var o=Ki(i,this.pickingFrameBuffer,t.x,t.y,this.internals.pixelRatio,this.internals.settings.pickingDownSizingRatio),s=Ya.apply(void 0,Q(o));return(r=this.pickingState.lookup[s])!==null&&r!==void 0?r:null}},{key:"bindEventHandlers",value:function(){return Vc(this.internals,this.mouseCaptor,this.touchCaptor,this.activeListeners),this}},{key:"bindGraphHandlers",value:function(){return qc({graph:this.internals.graph,edgeGroups:this.edgeGroups,addNode:this.addNode.bind(this),updateNode:this.updateNode.bind(this),removeNode:this.removeNode.bind(this),addEdge:this.addEdge.bind(this),updateEdge:this.updateEdge.bind(this),removeEdge:this.removeEdge.bind(this),clearEdgeState:this.clearEdgeState.bind(this),clearNodeState:this.clearNodeState.bind(this),clearEdgeIndices:this.clearEdgeIndices.bind(this),clearNodeIndices:this.clearNodeIndices.bind(this),refresh:this.refresh.bind(this)},this.activeListeners),this}},{key:"unbindGraphHandlers",value:function(){jc(this.internals.graph,this.activeListeners)}},{key:"getNodeShapeId",value:function(t){return this.internals.nodeShapeMap&&this.internals.nodeGlobalShapeIds&&t.shape&&t.shape in this.internals.nodeShapeMap?this.internals.nodeGlobalShapeIds[this.internals.nodeShapeMap[t.shape]]:Dn(t.shape||"circle")}},{key:"processNodes",value:function(){var t=this,r=this.internals.graph,i=this.internals.settings,o=this.getDimensions(),s=i.autoRescale,l=i.autoRescaleContent,u=this.nodeExtent;if(s===!1){var d=o.width,h=o.height;u={x:[-d/2,d/2],y:[-h/2,h/2]}}else(s!=="once"||!this.autoRescaleFrozen)&&(u=this.computeNodeExtent(),l!=="positions"&&!this.customBBox&&(u=Zc({extent:u,coords:this.nodeGraphCoords,nodeData:this.internals.nodeDataCache,dimensions:o,stagePadding:this.getStagePadding(),zoomToSizeRatioFunction:i.zoomToSizeRatioFunction,itemSizesReference:i.itemSizesReference,fitLabels:l==="labels",nodeLabelBox:function(z,R){return t.labelRenderer.nodeLabelBox(z,R)}})),s==="once"&&(this.autoRescaleFrozen=!0));this.nodeExtent=u,this.normalizationFunction=fa(this.customBBox||this.nodeExtent);var c=new ys,f=ft(c.getState(),o,this.getGraphDimensions(),this.getStagePadding());this.labelRenderer.labelGrid.resizeAndClear(o,i.labelGridCellSize),this.labelRenderer.edgeAnchorGrid.resizeAndClear(o,i.labelGridCellSize);var g=i.renderEdgeLabels&&i.edgeLabelAnchors==="allNodes",y=!1;Cr(this.pickingState,"node");for(var m=r.nodes(),v=0,p=m.length;v<p;v++){var b=m[v],T=this.internals.nodeDataCache[b],_=this.nodeGraphCoords[b];T.x=_.x,T.y=_.y,this.normalizationFunction.applyTo(T),T.visibility!==this.prevNodeVisibilities[b]&&(y=!0),typeof T.label=="string"&&T.visibility!=="hidden"&&T.labelVisibility!=="hidden"&&this.labelRenderer.labelGrid.add(b,T.size,this.framedGraphToViewport(T,{matrix:f})),g&&T.visibility!=="hidden"&&this.labelRenderer.edgeAnchorGrid.add(b,T.size,this.framedGraphToViewport(T,{matrix:f}))}this.labelRenderer.labelGrid.organize(),this.labelRenderer.edgeAnchorGrid.organize(),this.nodeProgram.reallocate(m.length);var E=0;this.depthRanges.nodes={},this.nodeBaseDepth={};var A=this.internals.nodeDataCache,w=O(this.depthLayers),S;try{for(w.s();!(S=w.n()).done;){var C=S.value,G=this.itemBuckets.nodes.getSorted(C,function(U){return A[U].zIndex});if(G.length!==0){this.depthRanges.nodes[C]=[{offset:E,count:G.length}];var L=O(G),N;try{for(L.s();!(N=L.n()).done;){var k=N.value;this.nodeBaseDepth[k]=C,this.nodeProgram.allocateNode(k),Es(this.pickingState,"node",k),this.addNodeToProgram(k,E++)}}catch(U){L.e(U)}finally{L.f()}}}}catch(U){w.e(U)}finally{w.f()}this.nodeProgram.invalidateBuffers();for(var I=0,W=m.length;I<W;I++)this.prevNodeVisibilities[m[I]]=this.internals.nodeDataCache[m[I]].visibility;this.labelRenderer.processWebGLLabels(m);var F=O(this.customLayerPrograms.values()),x;try{for(F.s();!(x=F.n()).done;){var P=x.value.program;P.cacheData&&P.cacheData()}}catch(U){F.e(U)}finally{F.f()}return y}},{key:"processEdges",value:function(){var t=this.internals.graph,r=t.edges();this.edgeProgram.reallocate(r.length);var i=0;Cr(this.pickingState,"edge"),this.depthRanges.edges={},this.edgeBaseDepth={};var o=this.internals.edgeDataCache,s=O(this.depthLayers),l;try{for(s.s();!(l=s.n()).done;){var u=l.value,d=this.itemBuckets.edges.getSorted(u,function(g){return o[g].zIndex});if(d.length!==0){this.depthRanges.edges[u]=[{offset:i,count:d.length}];var h=O(d),c;try{for(h.s();!(c=h.n()).done;){var f=c.value;this.edgeBaseDepth[f]=u,Es(this.pickingState,"edge",f),this.addEdgeToProgram(f,i++)}}catch(g){h.e(g)}finally{h.f()}}}}catch(g){s.e(g)}finally{s.f()}this.edgeProgram.invalidateBuffers()}},{key:"updateNodeDepthRanges",value:function(t,r,i){var o=this.nodeProgramIndex[t];o!==void 0&&(ur(this.depthRanges.nodes,r,o),dr(this.depthRanges.nodes,i,o))}},{key:"updateEdgeDepthRanges",value:function(t,r,i){var o=this.edgeProgramIndex[t];o!==void 0&&(ur(this.depthRanges.edges,r,o),dr(this.depthRanges.edges,i,o))}},{key:"handleSettingsUpdate",value:function(){var t=this,r=this.internals.settings;return this.camera.minRatio=r.minCameraRatio,this.camera.maxRatio=r.maxCameraRatio,this.camera.enabledZooming=r.enableCameraZooming,this.camera.enabledPanning=r.enableCameraPanning,this.camera.enabledRotation=r.enableCameraRotation,r.cameraPanBoundaries?this.camera.constrainState=function(i){return t.cleanCameraState(i,r.cameraPanBoundaries&&re(r.cameraPanBoundaries)==="object"?r.cameraPanBoundaries:{})}:this.camera.constrainState=null,this.camera.setState(this.camera.getState()),this.mouseLayer.style.touchAction=r.gestureTarget==="graph"?"none":r.gestureTarget==="shared"?"pan-x pan-y":"auto",r.gestureTarget!=="shared"&&this.gestureHint&&(this.gestureHint.kill(),this.gestureHint=null),this.mouseCaptor.setSettings(this.internals.settings),this.touchCaptor.setSettings(this.internals.settings),this}},{key:"cleanCameraState",value:function(t){var r=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{},i=r.tolerance,o=i===void 0?0:i,s=r.boundaries,l=H({},t),u=s||this.nodeExtent,d=ie(u.x,2),h=d[0],c=d[1],f=ie(u.y,2),g=f[0],y=f[1],m=[this.graphToViewport({x:h,y:g},{cameraState:t}),this.graphToViewport({x:c,y:g},{cameraState:t}),this.graphToViewport({x:h,y},{cameraState:t}),this.graphToViewport({x:c,y},{cameraState:t})],v=1/0,p=-1/0,b=1/0,T=-1/0;m.forEach(function(k){var I=k.x,W=k.y;v=Math.min(v,I),p=Math.max(p,I),b=Math.min(b,W),T=Math.max(T,W)});var _=p-v,E=T-b,A=this.getDimensions(),w=A.width,S=A.height,C=0,G=0;if(_>=w?p<w-o?C=p-(w-o):v>o&&(C=v-o):p>w+o?C=p-(w+o):v<-o&&(C=v+o),E>=S?T<S-o?G=T-(S-o):b>o&&(G=b-o):T>S+o?G=T-(S+o):b<-o&&(G=b+o),C||G){var L=this.viewportToFramedGraph({x:0,y:0},{cameraState:t}),N=this.viewportToFramedGraph({x:C,y:G},{cameraState:t});C=N.x-L.x,G=N.y-L.y,l.x+=C,l.y+=G}return l}},{key:"refreshMatrices",value:function(){var t=this.camera.getState(),r=this.getDimensions(),i=this.getGraphDimensions(),o=this.getStagePadding();this.matrix=ft(t,r,i,o),this.invMatrix=ft(t,r,i,o,!0),this.correctionRatio=qi(this.matrix,t,r),this.graphToViewportRatio=this.getGraphToViewportRatio()}},{key:"processData",value:function(){var t;this.emit("beforeProcess"),(t=this.internals.attachmentManager)===null||t===void 0||t.clear();var r=H({},this.pickingState.idsByKind),i=this.processNodes();(this.pendingProcess==="full"||i)&&this.processEdges(),Wc(this.pickingState,this.internals),Uc(r,this.pickingState.idsByKind)||this.internals.hoverResolver.invalidate(),this.pendingProcess="none",this.emit("afterProcess")}},{key:"render",value:function(){var t=this;if(this.contextLost)return this;this.emit("beforeRender");var r=function(){return t.internals.hoverResolver.frameRendered(),t.emit("afterRender"),t};if(this.renderFrame&&(cancelAnimationFrame(this.renderFrame),this.renderFrame=null),this.resize(),(this.pendingProcess!=="none"||this.needToRefreshState)&&(this.labelRenderer.labelsDirty=!0),this.pendingProcess!=="none"&&this.processData(),this.needToRefreshState&&this.refreshState(),this.needToRefreshState=!1,this.stateManager.clearDirtyTracking(),this.pendingProcess!=="none"&&this.processData(),this.clear(),this.resetWebGLTexture(),!this.internals.graph.order)return r();var i=this.mouseCaptor,o=this.camera.isAnimating()||i.isMoving||i.draggedEvents||i.currentWheelDirection;if(this.refreshMatrices(),this.frameId++,this.internals.settings.renderEdgeLabels&&!this.internals.edgeLabelProgram){var s=this.createEdgeLabelPrograms(),l=s.labelProgram,u=s.labelBackgroundProgram;this.internals.edgeLabelProgram=l,this.internals.edgeLabelBackgroundProgram=u}var d=this.internals.settings.DEBUG_logRenderStats?this.getDebugPrograms():null;d&&d.forEach(function(Z){return Z.resetDebugStats()}),this.internals.settings.DEBUG_gpuTimerQueries&&this.beginGpuTimerQuery(),this.internals.nodeFrameTexture.ensureCapacity(this.internals.nodeDataTexture.getCapacity()),this.internals.edgeFrameTexture.ensureCapacity(this.internals.edgeDataTexture.getCapacity());var h=this.getRenderParams(),c=Ce.edge.writesPickingThisFrame(this.internals)?h:H(H({},h),{},{pickingFrameBuffer:null});this.labelRenderer.resetFrame();var f=this.webGLContext,g=Math.ceil(this.width*this.internals.pixelRatio/this.internals.settings.pickingDownSizingRatio),y=Math.ceil(this.height*this.internals.pixelRatio/this.internals.settings.pickingDownSizingRatio);if(f.bindFramebuffer(f.FRAMEBUFFER,this.pickingFrameBuffer),f.viewport(0,0,g,y),f.clear(f.COLOR_BUFFER_BIT|f.DEPTH_BUFFER_BIT),f.bindFramebuffer(f.FRAMEBUFFER,null),f.viewport(0,0,this.width*this.internals.pixelRatio,this.height*this.internals.pixelRatio),f.clear(f.COLOR_BUFFER_BIT|f.DEPTH_BUFFER_BIT),this.internals.nodeDataTexture.upload(),this.internals.edgeDataTexture.upload(),this.nodeProgram.uploadLayerTexture(),this.edgeProgram.uploadAttributeTexture(),this.emit("afterTexturesUpload"),this.internals.nodeDataTexture.bind(ks),this.internals.edgeDataTexture.bind(Ps),this.edgeFramePass.run(h,this.internals.edgeFrameTexture,this.internals.edgeDataTexture.getHighWaterMark(),this.edgeProgram.getAttributeTexture(),this.nodeProgram.getAttributeTexture()),this.internals.edgeFrameTexture.bind(Cs),this.internals.settings.renderLabels){this.labelRenderer.computeDisplayedNodeLabels();var m=this.labelRenderer.buildFramePassPoints(),v=m.data,p=m.count;this.nodeFramePass.run(v,p,this.internals.nodeFrameTexture,h,this.nodeProgram.getAttributeTexture()),this.internals.nodeFrameTexture.bind(Ls)}this.internals.settings.renderEdgeLabels&&this.labelRenderer.computeDisplayedEdgeLabels();var b=O(this.customLayerPrograms.values()),T;try{for(b.s();!(T=b.n()).done;){var _=T.value.program;_.preRender&&_.preRender(h)}}catch(Z){b.e(Z)}finally{b.f()}f.bindFramebuffer(f.FRAMEBUFFER,null),f.viewport(0,0,this.width*this.internals.pixelRatio,this.height*this.internals.pixelRatio),f.blendFunc(f.ONE,f.ONE_MINUS_SRC_ALPHA);var E=!this.internals.settings.hideLabelsOnMove||!o,A=O(this.depthLayers),w;try{for(A.s();!(w=A.n()).done;){var S=w.value,C=O(this.customLayerPrograms.values()),G;try{for(C.s();!(G=C.n()).done;){var L=G.value;L.depth===S&&L.program.render(h)}}catch(Z){C.e(Z)}finally{C.f()}var N=this.depthRanges.edges[S];if(N&&(!this.internals.settings.hideEdgesOnMove||!o)){var k=O(N),I;try{for(k.s();!(I=k.n()).done;){var W=I.value,F=W.offset,x=W.count;x>0&&this.edgeProgram.render(c,F,x)}}catch(Z){k.e(Z)}finally{k.f()}}this.internals.settings.renderEdgeLabels&&E&&(this.labelRenderer.renderEdgeLabelBackgrounds(Ce.edgeLabel.writesPickingThisFrame(this.internals)?h:H(H({},h),{},{pickingFrameBuffer:null}),S),this.labelRenderer.renderEdgeLabels(h,S)),this.labelRenderer.cacheAttachments(S),this.labelRenderer.renderBackdrops(H(H({},h),{},{pickingFrameBuffer:null}),S);var P=this.depthRanges.nodes[S];if(P){var U=O(P),z;try{for(U.s();!(z=U.n()).done;){var R=z.value,j=R.offset,q=R.count;q>0&&this.nodeProgram.render(h,j,q)}}catch(Z){U.e(Z)}finally{U.f()}}E&&(this.labelRenderer.renderAttachments(H(H({},h),{},{pickingFrameBuffer:null}),S),this.labelRenderer.renderLabelBackgrounds(Ce.nodeLabel.writesPickingThisFrame(this.internals)?h:H(H({},h),{},{pickingFrameBuffer:null}),S),this.internals.settings.renderLabels&&this.labelRenderer.renderWebGLLabels(h,S))}}catch(Z){A.e(Z)}finally{A.f()}return this.labelRenderer.labelsDirty=!1,this.internals.settings.DEBUG_displayPickingLayer&&(f.bindFramebuffer(f.READ_FRAMEBUFFER,this.pickingFrameBuffer),f.bindFramebuffer(f.DRAW_FRAMEBUFFER,null),f.blitFramebuffer(0,0,g,y,0,0,this.width*this.internals.pixelRatio,this.height*this.internals.pixelRatio,f.COLOR_BUFFER_BIT,f.NEAREST)),this.internals.settings.DEBUG_gpuTimerQueries&&this.endGpuTimerQuery(),this.pollGpuTimerQueries(),d&&this.logRenderStats(d),r()}},{key:"getDebugPrograms",value:function(){return[this.nodeProgram,this.edgeProgram,this.internals.labelProgram,this.internals.edgeLabelProgram,this.internals.edgeLabelBackgroundProgram,this.internals.backdropProgram,this.internals.labelBackgroundProgram,this.internals.attachmentProgram].filter(function(t){return t!==null})}},{key:"logRenderStats",value:function(t){var r={},i=O(t),o;try{for(i.s();!(o=i.n()).done;){var s=o.value;r[s.constructor.name]=H({},s.debugStats)}}catch(l){i.e(l)}finally{i.f()}console.log("[sigma] DEBUG_logRenderStats: frame #".concat(this.frameId)),console.table(r)}},{key:"getGpuTimerExtension",value:function(){return this.gpuTimerExt===void 0&&(this.gpuTimerExt=this.webGLContext.getExtension("EXT_disjoint_timer_query_webgl2"),this.gpuTimerExt||console.warn("Sigma: DEBUG_gpuTimerQueries is enabled, but this browser/driver doesn't support EXT_disjoint_timer_query_webgl2.")),this.gpuTimerExt}},{key:"beginGpuTimerQuery",value:function(){var t=this.getGpuTimerExtension();if(t){var r=this.webGLContext,i=r.createQuery();i&&(r.beginQuery(t.TIME_ELAPSED_EXT,i),this.activeGpuTimerQuery=i)}}},{key:"endGpuTimerQuery",value:function(){!this.gpuTimerExt||!this.activeGpuTimerQuery||(this.webGLContext.endQuery(this.gpuTimerExt.TIME_ELAPSED_EXT),this.pendingGpuTimerQueries.push({query:this.activeGpuTimerQuery,frameId:this.frameId}),this.activeGpuTimerQuery=null)}},{key:"pollGpuTimerQueries",value:function(){if(this.pendingGpuTimerQueries.length!==0){var t=this.webGLContext,r=this.gpuTimerExt;if(!r){this.pendingGpuTimerQueries.forEach(function(h){var c=h.query;return t.deleteQuery(c)}),this.pendingGpuTimerQueries=[];return}var i=t.getParameter(r.GPU_DISJOINT_EXT),o=[],s=O(this.pendingGpuTimerQueries),l;try{for(s.s();!(l=s.n()).done;){var u=l.value;if(!t.getQueryParameter(u.query,t.QUERY_RESULT_AVAILABLE)){o.push(u);continue}if(!i){var d=t.getQueryParameter(u.query,t.QUERY_RESULT);console.log("[sigma] DEBUG_gpuTimerQueries: frame #".concat(u.frameId," GPU time = ").concat((d/1e6).toFixed(2),"ms"))}t.deleteQuery(u.query)}}catch(h){s.e(h)}finally{s.f()}this.pendingGpuTimerQueries=o}}},{key:"postEvaluateNode",value:function(t,r,i){var o=t;o.x===void 0&&(o.x=r.x),o.y===void 0&&(o.y=r.y),t.highlighted=i.isHighlighted;for(var s=0,l=this.nodeVariableEntries.length;s<l;s++){var u,d,h=ie(this.nodeVariableEntries[s],2),c=h[0],f=h[1];o[c]=(u=(d=o[c])!==null&&d!==void 0?d:r[c])!==null&&u!==void 0?u:f.default}}},{key:"addNode",value:function(t){var r=this.internals.graph.getNodeAttributes(t),i=this.stateManager.getNodeState(t),o=this.internals.nodeDataCache[t]||{};if(rr(this.stylesDeclaration.nodes,r,i,this.stateManager.graphState,this.internals.graph,o),this.postEvaluateNode(o,r,i),this.nodeReducer){var s=this.nodeReducer(t,o,r,i,this.stateManager.graphState,this.internals.graph);o=H(H({},o),s)}if(typeof o.x!="number"||typeof o.y!="number")throw new Error('Sigma: could not find a valid position (x, y) for node "'.concat(t,'". ')+"Provide coordinates via node attributes, styles, or a nodeReducer.");this.internals.nodeShapeMap?(!o.shape||!(o.shape in this.internals.nodeShapeMap))&&(o.shape=Object.keys(this.internals.nodeShapeMap)[0]):this.nodeShapeSlug&&(o.shape=this.nodeShapeSlug),this.internals.nodeDataCache[t]=o,this.nodeGraphCoords[t]={x:o.x,y:o.y},Dt(this.internals.nodesWithForcedLabels,t,vt(o)),Dt(this.internals.nodesWithBackdrop,t,lr(o)),this.itemBuckets.nodes.set(t,o.depth)}},{key:"updateNode",value:function(t){this.addNode(t);var r=this.internals.nodeDataCache[t];this.normalizationFunction.applyTo(r)}},{key:"removeNode",value:function(t){this.itemBuckets.nodes.remove(t),delete this.internals.nodeDataCache[t],delete this.nodeGraphCoords[t],delete this.nodeProgramIndex[t],this.internals.dragManager.removeNode(t),this.stateManager.removeNode(t),this.internals.nodesWithForcedLabels.delete(t),this.internals.nodesWithBackdrop.delete(t)}},{key:"postEvaluateEdge",value:function(t,r){for(var i=t,o=0,s=this.edgeVariableEntries.length;o<s;o++){var l,u,d=ie(this.edgeVariableEntries[o],2),h=d[0],c=d[1];i[h]=(l=(u=i[h])!==null&&u!==void 0?u:r[h])!==null&&l!==void 0?l:c.default}}},{key:"applyEdgeSpread",value:function(t,r,i){var o;if(!(i.parallelCount<=1)){var s=this.internals.graph.source(t),l=this.internals.graph.target(t),u=s===l,d=u?r.selfLoopPath||r.path:r.parallelPath||r.path,h=d?this.edgePathsByName.get(d):void 0;if(h!=null&&h.spread){var c=(o=r.parallelSpread)!==null&&o!==void 0?o:.25,f=h.spread.compute(i.parallelIndex,i.parallelCount,c);!u&&this.internals.graph.isDirected(t)&&s>l&&(f=-f),r[h.spread.variable]=f}}}},{key:"addEdge",value:function(t){var r=this.internals.graph.getEdgeAttributes(t),i=this.stateManager.getEdgeState(t),o={};if(ir(this.stylesDeclaration.edges,r,i,this.stateManager.graphState,this.internals.graph,o),this.postEvaluateEdge(o,r),this.edgeReducer){var s=this.edgeReducer(t,o,r,i,this.stateManager.graphState,this.internals.graph);o=H(H({},o),s)}this.applyEdgeSpread(t,o,i),this.internals.edgeDataCache[t]=o,Dt(this.internals.edgesWithForcedLabels,t,vt(o)),this.itemBuckets.edges.set(t,o.depth)}},{key:"updateEdge",value:function(t){this.addEdge(t)}},{key:"removeEdge",value:function(t){this.itemBuckets.edges.remove(t),delete this.internals.edgeDataCache[t],delete this.edgeProgramIndex[t],delete this.edgeTextureIndexCache[t],this.internals.edgeDataTexture.free(t),this.stateManager.removeEdge(t),this.internals.edgesWithForcedLabels.delete(t)}},{key:"clearNodeIndices",value:function(){this.labelRenderer.resetLabelGrid(),this.autoRescaleFrozen||(this.nodeExtent={x:[0,1],y:[0,1]}),this.internals.nodeDataCache={},this.nodeGraphCoords={},this.edgeProgramIndex={},this.internals.nodesWithForcedLabels.clear(),this.internals.nodesWithBackdrop.clear(),this.prevNodeVisibilities={},this.itemBuckets.nodes.clearAll(),this.depthRanges.nodes={},this.nodeBaseDepth={}}},{key:"clearEdgeIndices",value:function(){this.internals.edgeDataCache={},this.edgeProgramIndex={},this.edgeTextureIndexCache={},this.internals.edgesWithForcedLabels.clear(),Cr(this.pickingState,"edge"),this.itemBuckets.edges.clearAll(),this.depthRanges.edges={},this.edgeBaseDepth={},this.edgeGroups.clear()}},{key:"clearIndices",value:function(){this.clearEdgeIndices(),this.clearNodeIndices()}},{key:"clearNodeState",value:function(){this.labelRenderer.resetFrame(),this.internals.nodesWithBackdrop.clear(),this.internals.dragManager.clear(),this.autoRescaleFrozen=!1,this.stateManager.clearNodes()}},{key:"clearEdgeState",value:function(){this.labelRenderer.clearEdgeLabels(),this.stateManager.clearEdges()}},{key:"clearState",value:function(){this.clearEdgeState(),this.clearNodeState(),this.stateManager.resetGraphState()}},{key:"addNodeToProgram",value:function(t,r){var i,o=this.internals.nodeDataCache[t];this.internals.nodeDataTexture.allocate(t),(i=this.internals.nodeDataTexture).updateNode.apply(i,[t,o.x,o.y,o.size,this.getNodeShapeId(o)].concat(Q(ca(o)),[o.color]));var s=this.internals.nodeDataTexture.getIndex(t);this.nodeProgram.process(Ft(this.pickingState,"node",t),r,o,s,t),this.nodeProgramIndex[t]=r}},{key:"addEdgeToProgram",value:function(t,r){var i,o,s=this.internals.edgeDataCache[t],l=this.internals.graph.source(t),u=this.internals.graph.target(t),d=this.internals.edgeDataTexture.allocate(t);this.edgeTextureIndexCache[t]=d;var h=l===u,c=!h&&((i=(o=this.stateManager.getEdgeState(t))===null||o===void 0?void 0:o.parallelCount)!==null&&i!==void 0?i:1)>1,f=this.edgeProgram.resolveEdgeIds(s,h,c),g=f.pathId,y=f.headId,m=f.tailId,v=f.headLengthRatio,p=f.tailLengthRatio;this.internals.edgeDataTexture.updateEdge(t,this.internals.nodeDataTexture.getIndex(l),this.internals.nodeDataTexture.getIndex(u),s.size,v,p,g,y,m),this.edgeProgram.process(Ft(this.pickingState,"edge",t),r,this.internals.nodeDataCache[l],this.internals.nodeDataCache[u],s,d),this.edgeProgramIndex[t]=r}},{key:"getRenderParams",value:function(){return{frameId:this.frameId,matrix:this.matrix,invMatrix:this.invMatrix,width:this.width,height:this.height,pixelRatio:this.internals.pixelRatio,zoomRatio:this.camera.ratio,cameraAngle:this.camera.angle,sizeRatio:1/this.scaleSize(),correctionRatio:this.correctionRatio,downSizingRatio:this.internals.settings.pickingDownSizingRatio,minEdgeThickness:this.internals.settings.minEdgeThickness,antiAliasingFeather:this.internals.settings.antiAliasingFeather,nodePickingPadding:this.internals.settings.nodePickingPadding,edgePickingPadding:this.internals.settings.edgePickingPadding,labelPickingPadding:this.internals.settings.labelPickingPadding,nodeDataTextureUnit:ks,nodeDataTextureWidth:this.internals.nodeDataTexture.getTextureWidth(),nodeFrameTextureUnit:Ls,nodeFrameTextureWidth:this.internals.nodeFrameTexture.getTextureWidth(),edgeDataTextureUnit:Ps,edgeDataTextureWidth:this.internals.edgeDataTexture.getTextureWidth(),edgeFrameTextureUnit:Cs,edgeFrameTextureWidth:this.internals.edgeFrameTexture.getTextureWidth(),pickingFrameBuffer:this.pickingFrameBuffer,labelPixelSnapping:this.internals.settings.labelPixelSnapping?1:0}}},{key:"getStagePadding",value:function(){var t=this.internals.settings,r=t.stagePadding,i=t.autoRescale;return i&&r||0}},{key:"getLayerElement",value:function(t){if(t==="mouse")return this.mouseLayer;var r=this.extraElements[t];if(!r)throw new Error('Sigma: layer "'.concat(t,'" does not exist'));return r}},{key:"initWebGLContext",value:function(){var t=this,r=this.createWebGLContext("stage");this.stageCanvas=this.extraElements.stage,this.webGLContext=r,this.stageCanvas.addEventListener("webglcontextlost",function(i){t.webGLContext&&(i.preventDefault(),t.contextLost=!0,t.renderFrame&&(cancelAnimationFrame(t.renderFrame),t.renderFrame=null),t.gpuTimerExt=void 0,t.activeGpuTimerQuery=null,t.pendingGpuTimerQueries=[],t.emit("webglContextLost"))}),this.stageCanvas.addEventListener("webglcontextrestored",function(){requestAnimationFrame(function(){t.webGLContext&&!t.webGLContext.isContextLost()&&t.restoreWebGLContext()})}),this.initPickingFramebuffer()}},{key:"initPickingFramebuffer",value:function(){var t=this.webGLContext,r=t.createFramebuffer();if(!r)throw new Error("Sigma: cannot create picking frame buffer");t.bindFramebuffer(t.FRAMEBUFFER,r);var i=t.createTexture();if(!i)throw new Error("Sigma: cannot create picking texture");t.bindTexture(t.TEXTURE_2D,i),t.texImage2D(t.TEXTURE_2D,0,t.RGBA,1,1,0,t.RGBA,t.UNSIGNED_BYTE,null),t.texParameteri(t.TEXTURE_2D,t.TEXTURE_MIN_FILTER,t.NEAREST),t.texParameteri(t.TEXTURE_2D,t.TEXTURE_MAG_FILTER,t.NEAREST),t.texParameteri(t.TEXTURE_2D,t.TEXTURE_WRAP_S,t.CLAMP_TO_EDGE),t.texParameteri(t.TEXTURE_2D,t.TEXTURE_WRAP_T,t.CLAMP_TO_EDGE),t.framebufferTexture2D(t.FRAMEBUFFER,t.COLOR_ATTACHMENT0,t.TEXTURE_2D,i,0);var o=t.createRenderbuffer();if(!o)throw new Error("Sigma: cannot create picking depth buffer");if(t.bindRenderbuffer(t.RENDERBUFFER,o),t.renderbufferStorage(t.RENDERBUFFER,t.DEPTH_COMPONENT16,1,1),t.framebufferRenderbuffer(t.FRAMEBUFFER,t.DEPTH_ATTACHMENT,t.RENDERBUFFER,o),t.checkFramebufferStatus(t.FRAMEBUFFER)!==t.FRAMEBUFFER_COMPLETE)throw new Error("Sigma: picking framebuffer is not complete");t.bindFramebuffer(t.FRAMEBUFFER,null),this.pickingFrameBuffer=r,this.pickingTexture=i,this.pickingDepthBuffer=o}},{key:"initPrograms",value:function(t,r){var i=this,o=this.webGLContext,s=ss(o,this.pickingFrameBuffer,i,t?.nodes,r.antialiasNodes),l=s.nodeProgram,u=s.labelProgram,d=s.backdropProgram,h=s.labelBackgroundProgram,c=s.attachmentProgram,f=s.framePass,g=s.shapeSlug,y=s.shapeNameToIndex,m=s.shapeGlobalIds,v=s.variables;this.nodeProgram=l,this.nodeFramePass=f,this.nodeVariableEntries=Object.entries(v),g&&(this.nodeShapeSlug=g);var p=ls(o,this.pickingFrameBuffer,i,t?.edges,r.antialiasEdges,t?.nodes),b=p.edgeProgram,T=p.createLabelPrograms,_=p.framePass,E=p.variables,A=p.paths;return this.createEdgeLabelPrograms=T,this.edgeProgram=b,this.edgeFramePass=_,this.edgeVariableEntries=Object.entries(E),this.edgePathsByName=new Map(A.map(function(w){return[w.name,w]})),{labelProgram:u,edgeLabelProgram:null,edgeLabelBackgroundProgram:null,backdropProgram:d,labelBackgroundProgram:h,attachmentProgram:c,nodeShapeMap:y??null,nodeGlobalShapeIds:m??null}}},{key:"restoreWebGLContext",value:function(){var t,r,i,o,s,l=this.internals;this.initPickingFramebuffer(),(t=l.nodeDataTexture)===null||t===void 0||t.restore(),(r=l.nodeFrameTexture)===null||r===void 0||r.restore(),(i=l.edgeDataTexture)===null||i===void 0||i.restore(),(o=l.edgeFrameTexture)===null||o===void 0||o.restore(),(s=l.attachmentManager)===null||s===void 0||s.restore(),l.hoverResolver.reset(),Object.assign(l,this.initPrograms(l.primitives,l.settings));var u=O(this.customLayerPrograms.values()),d;try{for(u.s();!(d=u.n()).done;){var h=d.value;h.program.kill(),h.program=h.factory(this.webGLContext)}}catch(c){u.e(c)}finally{u.f()}this.contextLost=!1,this.emit("webglContextRestored"),this.refresh()}},{key:"createLayer",value:function(t,r){var i=arguments.length>2&&arguments[2]!==void 0?arguments[2]:{};if(this.extraElements[t])throw new Error('Sigma: a layer named "'.concat(t,'" already exists'));var o=en(r,{position:"absolute"},{class:"sigma-".concat(t)});return i.style&&Object.assign(o.style,i.style),this.extraElements[t]=o,"beforeLayer"in i&&i.beforeLayer?this.getLayerElement(i.beforeLayer).before(o):"afterLayer"in i&&i.afterLayer?this.getLayerElement(i.afterLayer).after(o):this.container.appendChild(o),o}},{key:"createCanvas",value:function(t){var r=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{};return this.createLayer(t,"canvas",r)}},{key:"createWebGLContext",value:function(t){var r=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{},i=this.createCanvas(t,r);r.hidden&&i.remove();var o=i.getContext("webgl2",H({preserveDrawingBuffer:!1,antialias:!1,depth:!0},r));if(!o)throw new Error("Sigma: WebGL 2 is not supported by your browser. Please use a modern browser (Chrome 56+, Firefox 51+, Safari 15+, Edge 79+).");return o.blendFunc(o.ONE,o.ONE_MINUS_SRC_ALPHA),o}},{key:"killLayer",value:function(t){if(t==="stage"||t==="mouse")throw new Error('Sigma: cannot kill built-in layer "'.concat(t,'"'));var r=this.extraElements[t];if(!r)throw new Error("Sigma: cannot kill layer ".concat(t,", which does not exist"));return r.remove(),delete this.extraElements[t],this}},{key:"getWebGLContext",value:function(){if(!this.webGLContext)throw new Error("Sigma: WebGL context is not available");return this.webGLContext}},{key:"getNodeDataTexture",value:function(){if(!this.internals.nodeDataTexture)throw new Error("Sigma: node data texture is not available");return this.internals.nodeDataTexture}},{key:"getNormalizationFunction",value:function(){return this.normalizationFunction}},{key:"addCustomLayerProgram",value:function(t,r,i){var o;if(!this.depthLayers.includes(r))throw new Error('Sigma: cannot add custom layer program at depth "'.concat(r,'", ')+"it must be declared in primitives.depthLayers. Current layers: ".concat(this.depthLayers.join(", ")));(o=this.customLayerPrograms.get(t))===null||o===void 0||o.program.kill();var s=i(this.webGLContext);return this.customLayerPrograms.set(t,{depth:r,factory:i,program:s}),s.cacheData&&s.cacheData(),this.scheduleRender(),this}},{key:"removeCustomLayerProgram",value:function(t){var r=this.customLayerPrograms.get(t);return r&&(r.program.kill(),this.customLayerPrograms.delete(t),this.scheduleRender()),this}},{key:"getCamera",value:function(){return this.camera}},{key:"setCamera",value:function(t){return this.camera.cancelAnimation(),this.unbindCameraHandlers(),this.camera=t,this.bindCameraHandlers(),this.scheduleRender(),this}},{key:"getContainer",value:function(){return this.container}},{key:"getGraph",value:function(){return this.internals.graph}},{key:"setGraph",value:function(t){return t===this.internals.graph?this:(this.stateManager.pruneNodes(function(r){return t.hasNode(r)}),this.stateManager.pruneEdges(function(r){return t.hasEdge(r)}),this.unbindGraphHandlers(),this.checkEdgesEventsFrame!==null&&(cancelAnimationFrame(this.checkEdgesEventsFrame),this.checkEdgesEventsFrame=null),this.internals.graph=t,this.autoRescaleFrozen=!1,this.bindGraphHandlers(),this.refresh(),this)}},{key:"getMouseCaptor",value:function(){return this.mouseCaptor}},{key:"getTouchCaptor",value:function(){return this.touchCaptor}},{key:"getDimensions",value:function(){return{width:this.width,height:this.height}}},{key:"getGraphDimensions",value:function(){var t=this.customBBox||this.nodeExtent;return{width:t.x[1]-t.x[0]||1,height:t.y[1]-t.y[0]||1}}},{key:"getNodeDisplayData",value:function(t){var r=this.internals.nodeDataCache[t];return r?Object.assign({},r):void 0}},{key:"getEdgeDisplayData",value:function(t){var r=this.internals.edgeDataCache[t];return r?Object.assign({},r):void 0}},{key:"getNodeState",value:function(t){return this.stateManager.getNodeState(t)}},{key:"getEdgeState",value:function(t){return this.stateManager.getEdgeState(t)}},{key:"getGraphState",value:function(){return this.stateManager.getGraphState()}},{key:"setNodeState",value:function(t,r){return this.stateManager.setNodeState(t,r),this}},{key:"setEdgeState",value:function(t,r){return this.stateManager.setEdgeState(t,r),this}},{key:"setGraphState",value:function(t){return this.stateManager.setGraphState(t),this}},{key:"_setPanning",value:function(t){this.stateManager.setGraphState({isPanning:t})}},{key:"_setZooming",value:function(t){this.stateManager.setGraphState({isZooming:t})}},{key:"_hasNodeDrag",value:function(){var t=this.internals.dragManager;return!!(t.pendingNode||t.session)}},{key:"_showGestureHint",value:function(t){var r=this.internals.settings;r.gestureTarget==="shared"&&(this.gestureHint=this.gestureHint||new nf(this.container),this.gestureHint.show(t,r))}},{key:"setNodesState",value:function(t,r){return this.stateManager.setNodesState(t,r),this}},{key:"setEdgesState",value:function(t,r){return this.stateManager.setEdgesState(t,r),this}},{key:"updateContainerCursor",value:function(){var t=this.stateManager.hovered,r=this.resolvedStageStyle.cursor||"";this.container.style.cursor=t&&Oc(this.internals,t)||r}},{key:"refreshStageStyle",value:function(){this.resolvedStageStyle=or(this.stylesDeclaration.stage,this.stateManager.graphState),this.resolvedStageStyle.background!==void 0&&(this.container.style.backgroundColor=this.resolvedStageStyle.background),this.updateContainerCursor()}},{key:"getNodeDisplayedLabels",value:function(){return new Set(this.labelRenderer.displayedNodeLabels)}},{key:"getEdgeDisplayedLabels",value:function(){return new Set(this.labelRenderer.displayedEdgeLabels)}},{key:"getSettings",value:function(){return H({},this.internals.settings)}},{key:"getSetting",value:function(t){return this.internals.settings[t]}},{key:"getStyles",value:function(){return H({},this.stylesDeclaration)}},{key:"getPrimitives",value:function(){return H({},this.internals.primitives)}},{key:"setSetting",value:function(t,r){return this.internals.settings[t]=r,va(this.internals.settings),this.handleSettingsUpdate(),this.scheduleRefresh(),this}},{key:"updateSetting",value:function(t,r){return this.setSetting(t,r(this.internals.settings[t])),this}},{key:"setSettings",value:function(t){return this.internals.settings=H(H({},this.internals.settings),t),va(this.internals.settings),this.handleSettingsUpdate(),this.scheduleRefresh(),this}},{key:"resize",value:function(t){var r=this.width,i=this.height;if(this.width=this.container.offsetWidth,this.height=this.container.offsetHeight,this.internals.pixelRatio=Tn(),this.width===0)if(this.internals.settings.allowInvalidContainer)this.width=1;else throw new Error("Sigma: Container has no width. You can set the allowInvalidContainer setting to true to stop seeing this error.");if(this.height===0)if(this.internals.settings.allowInvalidContainer)this.height=1;else throw new Error("Sigma: Container has no height. You can set the allowInvalidContainer setting to true to stop seeing this error.");if(!t&&r===this.width&&i===this.height)return this;this.labelRenderer.labelsDirty=!0;for(var o=0,s=[this.mouseLayer].concat(Q(Object.values(this.extraElements)));o<s.length;o++){var l=s[o];l.style.width=this.width+"px",l.style.height=this.height+"px"}return this.webGLContext&&(this.stageCanvas.setAttribute("width",this.width*this.internals.pixelRatio+"px"),this.stageCanvas.setAttribute("height",this.height*this.internals.pixelRatio+"px"),this.webGLContext.viewport(0,0,this.width*this.internals.pixelRatio,this.height*this.internals.pixelRatio)),this.emit("resize"),this}},{key:"clear",value:function(){return this.emit("beforeClear"),this.webGLContext.bindFramebuffer(WebGLRenderingContext.FRAMEBUFFER,null),this.webGLContext.clear(WebGLRenderingContext.COLOR_BUFFER_BIT),this.emit("afterClear"),this}},{key:"scheduleStateRefresh",value:function(){this.needToRefreshState=!0,this.scheduleRender()}},{key:"refreshState",value:function(){var t=this,r;this.stateManager.flushGraphStateFlags();var i=this.stateManager.graphStateChanged&&this.internals.nodeStyleAnalysis.dependency==="graph-state",o=this.stateManager.graphStateChanged&&this.edgeStyleAnalysis.dependency==="graph-state",s=!1;if(i)this.internals.graph.forEachNode(function(g){t.refreshNodeState(g)&&(s=!0)});else if(this.internals.nodeStyleAnalysis.dependency!=="static"){var l=O(this.stateManager.dirtyNodes),u;try{for(l.s();!(u=l.n()).done;){var d=u.value;this.refreshNodeState(d)&&(s=!0)}}catch(g){l.e(g)}finally{l.f()}}if(o)this.internals.graph.forEachEdge(function(g){t.refreshEdgeState(g)&&(s=!0)});else if(this.edgeStyleAnalysis.dependency!=="static"){var h=O(this.stateManager.dirtyEdges),c;try{for(h.s();!(c=h.n()).done;){var f=c.value;this.refreshEdgeState(f)&&(s=!0)}}catch(g){h.e(g)}finally{h.f()}}this.stateManager.graphStateChanged&&(r=this.stylesDeclaration)!==null&&r!==void 0&&r.stage&&this.refreshStageStyle(),this.stateManager.clearDirtyTracking(),s&&(this.pendingProcess="full")}},{key:"refreshNodeState",value:function(t){var r=this.internals.nodeDataCache[t];if(!r||this.nodeReducer){var i,o,s,l,u=(i=this.internals.nodeDataCache[t])===null||i===void 0?void 0:i.depth,d=(o=this.internals.nodeDataCache[t])===null||o===void 0?void 0:o.zIndex,h=(s=this.internals.nodeDataCache[t])===null||s===void 0?void 0:s.labelAttachment;this.updateNode(t);var c=this.internals.nodeDataCache[t];this.internals.attachmentManager&&c.labelAttachment!==h&&this.internals.attachmentManager.invalidateNode(t);var f;this.internals.nodeShapeMap&&this.internals.nodeGlobalShapeIds&&c.shape&&c.shape in this.internals.nodeShapeMap?f=this.internals.nodeGlobalShapeIds[this.internals.nodeShapeMap[c.shape]]:f=Dn(c.shape||"circle"),(l=this.internals.nodeDataTexture).updateNode.apply(l,[t,c.x,c.y,c.size,f].concat(Q(ca(c)),[c.color])),u&&c.depth!==u&&this.updateNodeDepthRanges(t,u,c.depth);var g=this.nodeProgramIndex[t];return g!==void 0&&(this.addNodeToProgram(t,g),this.nodeProgram.invalidateBuffers()),d!==void 0&&c.zIndex!==d}var y=this.internals.graph.getNodeAttributes(t),m=this.stateManager.getNodeState(t),v=r.size,p=r.shape,b=r.depth,T=r.zIndex,_=r.labelAttachment,E=r.rotationAlignment,A=r.labelRotationAlignment,w=r.color;rr(this.stylesDeclaration.nodes,y,m,this.stateManager.graphState,this.internals.graph,r),this.postEvaluateNode(r,y,m);var S=this.nodeGraphCoords[t],C=r.x!==S.x||r.y!==S.y;if(C&&(S.x=r.x,S.y=r.y),this.normalizationFunction.applyTo(r),this.internals.nodeShapeMap?(!r.shape||!(r.shape in this.internals.nodeShapeMap))&&(r.shape=Object.keys(this.internals.nodeShapeMap)[0]):this.nodeShapeSlug&&(r.shape=this.nodeShapeSlug),this.internals.attachmentManager&&r.labelAttachment!==_&&this.internals.attachmentManager.invalidateNode(t),Dt(this.internals.nodesWithForcedLabels,t,vt(r)),Dt(this.internals.nodesWithBackdrop,t,lr(r)),C||r.size!==v||r.shape!==p||r.rotationAlignment!==E||r.labelRotationAlignment!==A||r.color!==w){var G,L;this.internals.nodeShapeMap&&this.internals.nodeGlobalShapeIds&&r.shape&&r.shape in this.internals.nodeShapeMap?L=this.internals.nodeGlobalShapeIds[this.internals.nodeShapeMap[r.shape]]:L=Dn(r.shape||"circle"),(G=this.internals.nodeDataTexture).updateNode.apply(G,[t,r.x,r.y,r.size,L].concat(Q(ca(r)),[r.color]))}this.itemBuckets.nodes.set(t,r.depth),r.depth!==b&&this.updateNodeDepthRanges(t,b,r.depth);var N=this.nodeProgramIndex[t];return N!==void 0&&(this.addNodeToProgram(t,N),this.nodeProgram.invalidateBuffers()),r.zIndex!==T}},{key:"refreshEdgeState",value:function(t){var r=this.internals.edgeDataCache[t];if(!r||this.edgeReducer){var i=r?.depth,o=r?.zIndex;this.updateEdge(t);var s=this.internals.edgeDataCache[t];i&&s.depth!==i&&this.updateEdgeDepthRanges(t,i,s.depth);var l=this.edgeProgramIndex[t];return l!==void 0&&(this.addEdgeToProgram(t,l),this.edgeProgram.invalidateBuffers()),o!==void 0&&s.zIndex!==o}var u=this.internals.graph.getEdgeAttributes(t),d=this.stateManager.getEdgeState(t),h=r.depth,c=r.zIndex,f=r.size,g=r.path,y=r.selfLoopPath,m=r.parallelPath,v=r.head,p=r.tail;ir(this.stylesDeclaration.edges,u,d,this.stateManager.graphState,this.internals.graph,r),this.postEvaluateEdge(r,u),this.applyEdgeSpread(t,r,d),Dt(this.internals.edgesWithForcedLabels,t,vt(r)),this.itemBuckets.edges.set(t,r.depth),r.depth!==h&&this.updateEdgeDepthRanges(t,h,r.depth);var b=this.edgeProgramIndex[t];if(b!==void 0){var T=r.size!==f||r.path!==g||r.selfLoopPath!==y||r.parallelPath!==m||r.head!==v||r.tail!==p;if(T)this.addEdgeToProgram(t,b),this.edgeProgram.invalidateBuffers();else{var _=this.internals.graph.source(t),E=this.internals.graph.target(t),A=this.internals.nodeDataCache[_],w=this.internals.nodeDataCache[E],S=this.edgeTextureIndexCache[t];this.edgeProgram.process(Ft(this.pickingState,"edge",t),b,A,w,r,S),this.edgeProgram.invalidateBuffers()}}return r.zIndex!==c}},{key:"refresh",value:function(t){var r=this,i=t?.skipIndexation!==void 0?t?.skipIndexation:!1,o=t?.schedule!==void 0?t.schedule:!1,s=!t||!t.partialGraph;if(s)this.clearEdgeIndices(),this.clearNodeIndices(),this.internals.graph.forEachNode(function(A){return r.addNode(A)}),this.edgeGroups.rebuild(),this.internals.graph.forEachEdge(function(A){return r.addEdge(A)}),this.pendingProcess="full";else{for(var l,u,d=((l=t.partialGraph)===null||l===void 0?void 0:l.nodes)||[],h=0,c=d?.length||0;h<c;h++){var f,g,y=""+d[h],m=(f=this.internals.nodeDataCache[y])===null||f===void 0?void 0:f.labelAttachment;if(this.updateNode(y),this.internals.attachmentManager&&((g=this.internals.nodeDataCache[y])!==null&&g!==void 0&&g.labelAttachment||m)&&this.internals.attachmentManager.invalidateNode(y),i){var v=this.nodeProgramIndex[y];if(v===void 0)throw new Error('Sigma: node "'.concat(y,`" can't be repaint`));this.addNodeToProgram(y,v)}}i&&d.length>0&&(this.nodeProgram.invalidateBuffers(),this.labelRenderer.labelsDirty=!0);for(var p=(t==null||(u=t.partialGraph)===null||u===void 0?void 0:u.edges)||[],b=0,T=p.length;b<T;b++){var _=""+p[b];if(this.updateEdge(_),i){var E=this.edgeProgramIndex[_];if(E===void 0)throw new Error('Sigma: edge "'.concat(_,`" can't be repaint`));this.addEdgeToProgram(_,E)}}i&&p.length>0&&(this.edgeProgram.invalidateBuffers(),this.labelRenderer.labelsDirty=!0),!i&&this.pendingProcess!=="full"&&(this.pendingProcess=p.length>0?"full":"nodes")}return o?this.scheduleRender():this.render(),this}},{key:"scheduleRender",value:function(){var t=this;return this.renderFrame||(this.renderFrame=requestAnimationFrame(function(){t.render()})),this}},{key:"scheduleRefresh",value:function(t){return this.refresh(H(H({},t),{},{schedule:!0}))}},{key:"getViewportZoomedState",value:function(t,r){var i=this.camera.getState(),o=i.ratio,s=i.angle,l=i.x,u=i.y,d=this.internals.settings,h=d.minCameraRatio,c=d.maxCameraRatio;typeof c=="number"&&(r=Math.min(r,c)),typeof h=="number"&&(r=Math.max(r,h));var f=r/o,g={x:this.width/2,y:this.height/2},y=this.viewportToFramedGraph(t),m=this.viewportToFramedGraph(g);return{angle:s,x:(y.x-m.x)*(1-f)+l,y:(y.y-m.y)*(1-f)+u,ratio:r}}},{key:"viewRectangle",value:function(){var t=this.viewportToFramedGraph({x:0,y:0}),r=this.viewportToFramedGraph({x:this.width,y:0}),i=this.viewportToFramedGraph({x:0,y:this.height});return{x1:t.x,y1:t.y,x2:r.x,y2:r.y,height:r.y-i.y}}},{key:"framedGraphToViewport",value:function(t){var r=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{},i=!!r.cameraState||!!r.viewportDimensions||!!r.graphDimensions||!!r.padding,o=r.matrix||(i?ft(r.cameraState||this.camera.getState(),r.viewportDimensions||this.getDimensions(),r.graphDimensions||this.getGraphDimensions(),r.padding||this.getStagePadding()):this.matrix),s=Yt(o,t);return{x:(1+s.x)*this.width/2,y:(1-s.y)*this.height/2}}},{key:"viewportToFramedGraph",value:function(t){var r=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{},i=!!r.cameraState||!!r.viewportDimensions||!!r.graphDimensions||!!r.padding,o=r.matrix||(i?ft(r.cameraState||this.camera.getState(),r.viewportDimensions||this.getDimensions(),r.graphDimensions||this.getGraphDimensions(),r.padding||this.getStagePadding(),!0):this.invMatrix),s=Yt(o,{x:t.x/this.width*2-1,y:1-t.y/this.height*2});return isNaN(s.x)&&(s.x=0),isNaN(s.y)&&(s.y=0),s}},{key:"viewportToGraph",value:function(t){var r=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{};return this.normalizationFunction.inverse(this.viewportToFramedGraph(t,r))}},{key:"graphToViewport",value:function(t){var r=arguments.length>1&&arguments[1]!==void 0?arguments[1]:{};return this.framedGraphToViewport(this.normalizationFunction(t),r)}},{key:"graphToFramedGraph",value:function(t){return this.normalizationFunction(t)}},{key:"framedGraphToGraph",value:function(t){return this.normalizationFunction.inverse(t)}},{key:"getGraphToViewportRatio",value:function(){var t={x:0,y:0},r={x:1,y:1},i=Math.sqrt(Math.pow(t.x-r.x,2)+Math.pow(t.y-r.y,2)),o=this.graphToViewport(t),s=this.graphToViewport(r),l=Math.sqrt(Math.pow(o.x-s.x,2)+Math.pow(o.y-s.y,2));return l/i}},{key:"computeNodeExtent",value:function(){var t=this.nodeGraphCoords,r=Object.keys(t);if(!r.length)return{x:[0,1],y:[0,1]};for(var i=1/0,o=-1/0,s=1/0,l=-1/0,u=0,d=r.length;u<d;u++){var h=t[r[u]],c=h.x,f=h.y;c<i&&(i=c),c>o&&(o=c),f<s&&(s=f),f>l&&(l=f)}return{x:[i,o],y:[s,l]}}},{key:"getBBox",value:function(){return this.nodeExtent}},{key:"getCustomBBox",value:function(){return this.customBBox}},{key:"setCustomBBox",value:function(t){return this.customBBox=t,this.scheduleRender(),this}},{key:"kill",value:function(){var t,r,i,o,s;this.emit("kill"),this.removeAllListeners(),this.camera.cancelAnimation(),this.unbindCameraHandlers(),window.removeEventListener("resize",this.activeListeners.handleResize),this.mouseCaptor.kill(),this.touchCaptor.kill(),this.internals.hoverResolver.kill(),this.unbindGraphHandlers(),this.clearIndices(),this.clearState(),this.internals.nodeDataCache={},this.internals.edgeDataCache={},this.renderFrame&&(cancelAnimationFrame(this.renderFrame),this.renderFrame=null);for(var l=this.container;l.firstChild;)l.removeChild(l.firstChild);this.nodeProgram.kill(),this.nodeFramePass.kill(),this.edgeProgram.kill(),this.edgeFramePass.kill(),this.internals.labelProgram.kill(),(t=this.internals.edgeLabelProgram)===null||t===void 0||t.kill(),(r=this.internals.edgeLabelBackgroundProgram)===null||r===void 0||r.kill(),this.internals.backdropProgram.kill(),this.internals.labelBackgroundProgram.kill(),(i=this.internals.attachmentProgram)===null||i===void 0||i.kill(),(o=this.internals.attachmentManager)===null||o===void 0||o.kill(),this.internals.attachmentProgram=null,this.internals.attachmentManager=null;var u=O(this.customLayerPrograms.values()),d;try{for(u.s();!(d=u.n()).done;){var h=d.value.program;h.kill()}}catch(g){u.e(g)}finally{u.f()}if(this.customLayerPrograms.clear(),this.sdfAtlas&&(this.sdfAtlas=null),this.internals.nodeDataTexture&&(this.internals.nodeDataTexture.kill(),this.internals.nodeDataTexture=null),this.internals.nodeFrameTexture&&(this.internals.nodeFrameTexture.kill(),this.internals.nodeFrameTexture=null),this.internals.edgeDataTexture&&(this.internals.edgeDataTexture.kill(),this.internals.edgeDataTexture=null),this.internals.edgeFrameTexture&&(this.internals.edgeFrameTexture.kill(),this.internals.edgeFrameTexture=null),this.webGLContext){var c;(c=this.webGLContext.getExtension("WEBGL_lose_context"))===null||c===void 0||c.loseContext(),this.webGLContext=null}(s=this.gestureHint)===null||s===void 0||s.kill(),this.gestureHint=null,this.mouseLayer.remove();for(var f in this.extraElements)this.extraElements[f].remove();this.extraElements={}}},{key:"scaleSize",value:function(){var t=arguments.length>0&&arguments[0]!==void 0?arguments[0]:1,r=arguments.length>1&&arguments[1]!==void 0?arguments[1]:this.camera.ratio;return t/this.internals.settings.zoomToSizeRatioFunction(r)*(this.getSetting("itemSizesReference")==="positions"?r*this.graphToViewportRatio:1)}},{key:"getStageCanvas",value:function(){return this.stageCanvas}},{key:"getMouseLayer",value:function(){return this.mouseLayer}}])})(ha),Ns=hf;var V=a=>document.querySelector(a),ae=a=>String(a??"").replace(/[&<>"']/g,n=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[n]),ve=(a,n=0)=>Number(a||0).toLocaleString("vi-VN",{maximumFractionDigits:n}),Gn=new URLSearchParams(location.search),cf={PERSON:"#4c77a2",ORGANIZATION:"#477f76",BANK:"#306d91",REGULATOR:"#896793",GOVERNMENT_AGENCY:"#916a50",BOND_ISSUE:"#88915a",BOND:"#88915a"},ff={CEO_OF:"T\u1ED5ng gi\xE1m \u0111\u1ED1c",CHAIR_OF:"Ch\u1EE7 t\u1ECBch",BOARD_MEMBER_OF:"H\u0110QT",FOUNDED:"S\xE1ng l\u1EADp",OWNS_SHARES_IN:"S\u1EDF h\u1EEFu c\u1ED5 ph\u1EA7n",SUBSIDIARY_OF:"C\xF4ng ty con",ACQUIRED:"Mua l\u1EA1i",LENDS_TO:"Cho vay",ISSUED_BOND:"Ph\xE1t h\xE0nh tr\xE1i phi\u1EBFu",JOINT_VENTURE_WITH:"Li\xEAn doanh",PARTNERS_WITH:"H\u1EE3p t\xE1c",SANCTIONED_BY:"X\u1EED ph\u1EA1t",PROSECUTED_BY:"Kh\u1EDFi t\u1ED1 / truy t\u1ED1"},B={mode:Gn.get("mode")==="quarantine"?"quarantine":"passed",view:Gn.get("node")?"neighborhood":["overview","global"].includes(Gn.get("view"))?Gn.get("view"):"overview",focusId:Gn.get("node"),communityId:null,target:null,metrics:null,options:null,graphData:null,renderer:null,layout:null,request:0,limits:{global:[300,700],neighborhood:[80,200]}};async function bt(a,n){let e=await fetch(a,n);if(!e.ok){let t;try{t=(await e.json()).detail}catch{t=e.statusText}throw Error(t||e.statusText)}return e.json()}function gf(a){let n=a>>>0;return()=>(n=1664525*n+1013904223>>>0,n/4294967296)}function Pr(){B.layout&&(B.layout.stop(),B.layout=null),B.renderer&&(B.renderer.kill(),B.renderer=null),V("#graph").replaceChildren()}function Ms(a,n){let e=[...V(a).querySelectorAll("input[type=checkbox]")],t=e.filter(r=>r.checked).map(r=>r.value);return t.length===e.length?[]:t.length?t:[`__NO_${n}__`]}function $s(){let a=Math.max(1,Number(B.metrics?.node_count||3e4)),n=Math.max(0,Number(B.metrics?.edge_count||5e4)),e=Math.min(a,Math.max(1,Number(V("#node-limit").value)||1)),t=Math.min(n,Math.max(0,Number(V("#edge-limit").value)||0)),r=Math.min(1e3,Math.max(0,Number(V("#min-degree").value)||0));return V("#node-limit").value=e,V("#edge-limit").value=t,V("#min-degree").value=r,{nodeLimit:e,edgeLimit:t,minDegree:r,hops:Number(V("#hops").value),types:Ms("#type-filters","TYPE"),predicates:Ms("#predicate-filters","RELATION")}}function vf(a){let n=new URLSearchParams({mode:B.mode,min_incident_edges:a.minDegree});return a.types.forEach(e=>n.append("types",e)),a.predicates.forEach(e=>n.append("predicates",e)),n}function Vs(){let a=new URLSearchParams({mode:B.mode,view:B.view});B.focusId&&B.view==="neighborhood"&&a.set("node",B.focusId),history.replaceState(null,"","?"+a)}function Fr(){document.querySelectorAll("#view-tabs button").forEach(n=>n.classList.toggle("active",n.dataset.view===B.view||B.view==="community"&&n.dataset.view==="global")),V("#filter-note").textContent=B.view==="overview"?"\u1EDE T\u1ED5ng quan, gi\u1EDBi h\u1EA1n node/c\u1EA1nh \xE1p d\u1EE5ng sau khi m\u1EDF m\u1EA1ng chi ti\u1EBFt.":"Gi\u1EDBi h\u1EA1n l\xE0 m\u1EE9c t\u1ED1i \u0111a. S\u1ED1 th\u1EF1c v\u1EBD c\xF3 th\u1EC3 th\u1EA5p h\u01A1n khi b\u1ED9 l\u1ECDc lo\u1EA1i c\u1EA1nh ho\u1EB7c node.";let a=B.view==="overview";V("#node-limit").disabled=a,V("#edge-limit").disabled=a,V("#hops").disabled=B.view!=="neighborhood"}function zn(a,n=null,e=null){if(a==="neighborhood"&&!n){V("#graph-note").textContent="H\xE3y t\xECm ho\u1EB7c click m\u1ED9t node \u0111\u1EC3 m\u1EDF m\u1EA1ng quanh n\xF3.";return}if(B.view!==a&&(a==="global"||a==="neighborhood"||a==="community")){let t=B.limits[a==="neighborhood"?"neighborhood":"global"];V("#node-limit").value=t[0],V("#edge-limit").value=t[1]}B.view=a,B.focusId=a==="neighborhood"?n:null,B.communityId=a==="community"?e:null,Fr(),Vs(),Pa()}function Ws(a,n,e){V(a).replaceChildren(...Object.entries(n).map(([t,r])=>{let i=document.createElement("label");return i.innerHTML=`<input type="checkbox" value="${ae(t)}" checked>
      <span>${ae(e(t))}</span><small>${ve(r)}</small>`,i}))}async function qs(){let a=B.mode;try{let[n,e]=await Promise.all([bt("/api/stats?mode="+a),bt("/api/graph/options?mode="+a)]);if(B.mode!==a)return;B.metrics=n,B.options=e,V("#summary").innerHTML=`<div><b>${ve(n.node_count)}</b><span>node ngu\u1ED3n</span></div>
      <div><b>${ve(n.edge_count)}</b><span>${a==="passed"?"c\u1EA1nh qua QA":"c\u1EA1nh \u1EE9ng vi\xEAn"}</span></div>
      <div><b>${ve(n.relation_types)}</b><span>lo\u1EA1i quan h\u1EC7</span></div>
      <div><b>${ve(n.analysis.largest_component)}</b><span>node trong th\xE0nh ph\u1EA7n l\u1EDBn nh\u1EA5t</span></div>`,V("#mode-note").textContent=a==="passed"?"M\u1EA1ng Passed ch\u1EC9 g\u1ED3m quan h\u1EC7 \u0111\xE3 qua c\u1ED5ng QA t\u1EF1 \u0111\u1ED9ng; \u0111\xE2y ch\u01B0a ph\u1EA3i \u0111\xE1nh gi\xE1 gold.":"M\u1EA1ng Quarantine g\u1ED3m \u1EE9ng vi\xEAn c\u1EA7n r\xE0 so\xE1t. C\u1EA1nh t\xEAn chung v\xE0 s\u1EF1 ki\u1EC7n b\u1ECB ph\u1EE7 \u0111\u1ECBnh ch\u1EC9 c\xF3 \u1EDF b\u1EA3ng quan h\u1EC7.",V("#quality-badge").textContent=a.toUpperCase(),document.body.classList.toggle("quarantine-mode",a==="quarantine"),Ws("#type-filters",e.types,t=>t),Ws("#predicate-filters",e.predicates,t=>ff[t]||t),V("#node-limit").max=n.node_count,V("#edge-limit").max=n.edge_count,Pa()}catch(n){V("#summary").textContent=n.message}}function Us(a){Pr();let n=document.createElement("div");n.className="graph-message",n.textContent=a,V("#graph").append(n)}function pf(a){let n=a.view==="overview",e=n?new Ot:new Bt;for(let t of a.nodes){let r=n?t.member_count:t.incident_edges;e.addNode(t.id,{label:t.name,name:t.name,type:t.type,community:n?t.id:t.community,component:n?t.id:t.component,size:n?5+Math.min(18,Math.sqrt(r)*1.05):4+Math.min(11,Math.sqrt(r)*.95),color:n?"#456f91":cf[t.type]||"#72869a"})}for(let t of a.edges)!e.hasNode(t.source)||!e.hasNode(t.target)||t.source===t.target||e.addEdgeWithKey(t.uid,t.source,t.target,{color:B.mode==="quarantine"?"#c9ae89":"#b7c7d3",size:n?Math.min(4,1+Math.log1p(t.weight)/2):1.1});return Os.default.assign(e,{hierarchyAttributes:n?[]:["component","community"],rng:gf(317)}),a.view==="neighborhood"&&a.focus_id&&e.hasNode(a.focus_id)&&(e.setNodeAttribute(a.focus_id,"x",0),e.setNodeAttribute(a.focus_id,"y",0),a.nodes.filter(t=>t.id!==a.focus_id).sort((t,r)=>(t.hop??0)-(r.hop??0)||r.incident_edges-t.incident_edges||t.id.localeCompare(r.id)).forEach((t,r)=>{let i=r*2.399963229728653,o=18+3.2*Math.sqrt(r);e.setNodeAttribute(t.id,"x",o*Math.cos(i)),e.setNodeAttribute(t.id,"y",o*Math.sin(i))})),e}function mf(a){let n={overview:"C\u1ED9ng \u0111\u1ED3ng trong m\u1EA1ng",global:"C\xE1c node trong to\xE0n m\u1EA1ng",community:`C\u1ED9ng \u0111\u1ED3ng ${B.communityId}`,neighborhood:"M\u1EA1ng quanh node \u0111\u01B0\u1EE3c ch\u1ECDn"};V("#graph-title").textContent=n[a.view],V("#graph-eyebrow").textContent=a.view==="overview"?"B\u1EA2N \u0110\u1ED2 T\u1ED4NG QUAN":a.view==="neighborhood"?"CH\xC2N DUNG M\u1EA0NG":"S\u01A0 \u0110\u1ED2 NODE & C\u1EA0NH";let e=a.counts;V("#graph-counts").textContent=a.view==="overview"?`${ve(e.filtered_nodes)} node \xB7 ${ve(e.filtered_edges)} c\u1EA1nh \u0111\u1EE7 l\u1ECDc \xB7 ${ve(e.shown_communities)}/${ve(e.total_communities)} c\u1ED9ng \u0111\u1ED3ng m\u1EDF ri\xEAng`:`${ve(e.drawn_nodes)}/${ve(e.filtered_nodes)} node \xB7 ${ve(e.drawn_edges)}/${ve(e.filtered_edges)} c\u1EA1nh \u0111\u01B0\u1EE3c v\u1EBD`,V("#graph-note").textContent=a.view==="overview"?"M\u1ED7i ch\u1EA5m l\xE0 m\u1ED9t c\u1ED9ng \u0111\u1ED3ng; k\xEDch th\u01B0\u1EDBc theo s\u1ED1 node. Click \u0111\u1EC3 m\u1EDF, ho\u1EB7c ch\u1ECDn \u201CHi\u1EC7n t\u1EA5t c\u1EA3 sau l\u1ECDc\u201D.":e.truncated_nodes||e.truncated_edges?"\u0110\xE3 c\u1EAFt theo gi\u1EDBi h\u1EA1n. T\u0103ng s\u1ED1 node/c\u1EA1nh \u1EDF b\u1ED9 \u0111i\u1EC1u khi\u1EC3n \u0111\u1EC3 xem th\xEAm.":"K\xE9o \u0111\u1EC3 di chuy\u1EC3n \xB7 cu\u1ED9n \u0111\u1EC3 ph\xF3ng to \xB7 click node \u0111\u1EC3 m\u1EDF m\u1EA1ng quanh n\xF3."}async function Pa(){if(!B.metrics)return;let a=++B.request,n=$s(),e=vf(n),t=B.view==="overview",r="/api/graph/"+(t?"overview":"subgraph");t||(e.set("scope",B.view),e.set("max_nodes",n.nodeLimit),e.set("max_edges",n.edgeLimit),e.set("hops",n.hops),B.view==="neighborhood"&&e.set("node_id",B.focusId),B.view==="community"&&e.set("community_id",B.communityId)),r+="?"+e,V("#graph-counts").textContent="\u0110ang l\u1ECDc v\xE0 b\u1ED1 tr\xED m\u1EA1ng\u2026";try{let i=await bt(r);if(a!==B.request)return;if(B.graphData=i,mf(i),!i.nodes.length){Us("Kh\xF4ng c\xF3 node th\u1ECFa b\u1ED9 l\u1ECDc. Gi\u1EA3m b\u1EADc t\u1ED1i thi\u1EC3u ho\u1EB7c ch\u1ECDn th\xEAm lo\u1EA1i quan h\u1EC7.");return}Pr();let o=pf(i),s=new Ns(o,V("#graph"),{settings:{renderLabels:i.nodes.length<1200,itemSizesReference:t?"positions":"screen",labelDensity:t?.25:i.nodes.length>40?.3:.8,labelRenderedSizeThreshold:t?10:i.nodes.length>40?7:5,renderEdgeLabels:!1,enableEdgeEvents:!t&&i.edges.length<=2500,hideEdgesOnMove:i.edges.length>3e3,minCameraRatio:.015,maxCameraRatio:5}});if(B.renderer=s,s.on("clickNode",({node:l})=>{t?l==="community:other"?zn("global"):zn("community",null,Number(l.split(":")[1])):Ir(l)}),!t&&i.edges.length<=2500&&s.on("clickEdge",({edge:l})=>Gr(l)),B.view==="neighborhood"&&i.nodes.length<=20&&i.edges.length){B.layout=new Hs.default(o,{settings:{...Bs.default.inferSettings(o),barnesHutOptimize:!0,gravity:1.5,slowDown:5}}),B.layout.start();let l=B.layout;setTimeout(()=>{B.layout===l&&l.stop()},1700)}if(B.view==="neighborhood"){let l=i.nodes.find(u=>u.id===B.focusId);l&&yf(l)}}catch(i){a===B.request&&Us(i.message)}}function Ir(a){B.target=null,V("#target").value="",V("#ask").disabled=!0,zn("neighborhood",a)}function yf(a){let n=B.mode==="quarantine";V("#inspector").innerHTML=`${n?'<p class="candidate-warning">\u1EE8ng vi\xEAn ch\u01B0a ki\u1EC3m \u0111\u1ECBnh \xB7 ki\u1EC3m tra b\xE0i b\xE1o tr\u01B0\u1EDBc khi k\u1EBFt lu\u1EADn.</p>':""}
    <div class="subtitle">${ae(a.type)} \xB7 ${ae(a.identity_status||"")}</div>
    <h3>${ae(a.name)}</h3><div class="subtitle">${ae(a.id)}</div>
    <div class="stat-grid"><div class="stat"><b>${ve(a.incident_edges)}</b><span>Quan h\u1EC7 k\u1EC1 sau l\u1ECDc</span></div>
      <div class="stat"><b>${ve(a.degree)}</b><span>B\u1EADc snapshot</span></div>
      <div class="stat"><b>${ve(a.pagerank,6)}</b><span>PageRank snapshot</span></div>
      <div class="stat"><b>${ve(a.core_number)}</b><span>k-core snapshot</span></div></div>
    <button type="button" class="inline-action" id="focus-current">V\u1EBD m\u1EA1ng quanh node n\xE0y</button>`,V("#focus-current").onclick=()=>Ir(a.id);let e=(B.graphData?.edges||[]).filter(r=>r.source===a.id||r.target===a.id),t=new Map((B.graphData?.nodes||[]).map(r=>[r.id,r]));V("#relation-list").innerHTML=`<h4>${ve(e.length)} c\u1EA1nh \u0111ang v\u1EBD s\xE1t node n\xE0y</h4>${e.slice(0,40).map(r=>{let i=t.get(r.source===a.id?r.target:r.source);return`<button type="button" class="relation-item" data-edge="${ae(r.uid)}">
      <strong>${ae(r.source===a.id?"\u2192":"\u2190")} ${ae(r.predicate)}</strong>
      <span>${ae(i?.name||"Node kh\xE1c")} \xB7 ${ve(r.article_count)} b\xE0i</span></button>`}).join("")}${e.length>40?'<p class="help">Hi\u1EC7n 40 c\u1EA1nh \u0111\u1EA7u; t\u0103ng gi\u1EDBi h\u1EA1n v\xE0 click c\u1EA1nh tr\xEAn s\u01A1 \u0111\u1ED3 \u0111\u1EC3 xem ch\u1EE9ng c\u1EE9.</p>':""}`,V("#relation-list").querySelectorAll("[data-edge]").forEach(r=>r.onclick=()=>Gr(r.dataset.edge)),n&&js(a.id),V("#ask").disabled=!B.target}async function js(a,n=0){let e=B.mode;try{let t=await bt(`/api/graph/review/${encodeURIComponent(a)}?offset=${n}&limit=20`);if(B.mode!==e||B.view!=="neighborhood"||B.focusId!==a)return;let r=V("#review-relations");r||(r=document.createElement("div"),r.id="review-relations",V("#relation-list").append(r)),n||(r.innerHTML=`<h4>${ve(t.total)} quan h\u1EC7 ch\u1EC9 \u0111\u1EC3 r\xE0 so\xE1t</h4>
        <p class="help">T\xEAn chung, \u0111\u1ECBnh danh y\u1EBFu ho\u1EB7c tr\u1EA1ng th\xE1i kh\xF4ng ph\xF9 h\u1EE3p kh\xF4ng \u0111\u01B0\u1EE3c v\u1EBD th\xE0nh c\u1EA1nh.</p>`);for(let i of t.relations){let o=document.createElement("button");o.type="button",o.className="relation-item review-item",o.innerHTML=`<strong>${ae(i.subject_name)} \u2192 ${ae(i.predicate)} \u2192 ${ae(i.object_name)}</strong>
        <span>${ae(i.endpoint_quality)} \xB7 ${ae(i.factual_status)} \xB7 ${ve(i.article_count)} b\xE0i</span>`,o.onclick=()=>Gr(i.edge_uid),r.append(o)}if(r.querySelector("#more-review")?.remove(),n+t.relations.length<t.total){let i=document.createElement("button");i.id="more-review",i.type="button",i.className="inline-action",i.textContent="Xem th\xEAm quan h\u1EC7 c\u1EA7n r\xE0 so\xE1t",i.onclick=()=>js(a,n+t.relations.length),r.append(i)}}catch(t){B.mode===e&&(V("#relation-list").textContent=t.message)}}async function Gr(a){let n=B.graphData;if(!n||n.view==="overview")return;let e=B.mode;V("#inspector").innerHTML='<p class="muted">\u0110ang t\u1EA3i b\u1EB1ng ch\u1EE9ng\u2026</p>';try{let t=await bt(`/api/graph/edge/${encodeURIComponent(a)}?mode=${e}&limit=20`);if(e!==B.mode)return;let r=t.edge,i=r.quarantine_classes?JSON.parse(r.quarantine_classes):[];V("#inspector").innerHTML=`${e==="quarantine"?'<p class="candidate-warning">QUARANTINE \xB7 Quan h\u1EC7 \u1EE9ng vi\xEAn ch\u01B0a \u0111\u01B0\u1EE3c x\xE1c nh\u1EADn.</p>':""}
      <div class="subtitle">${ae(r.predicate)} \xB7 ${ae(r.factual_status)}</div>
      <h3>${ae(r.subject_name)} \u2192 ${ae(r.object_name)}</h3>
      <p class="subtitle">${ve(r.article_count)} b\xE0i \xB7 ${ve(t.total)} b\u1EB1ng ch\u1EE9ng</p>
      ${i.map(s=>`<span class="tag">${ae(s)}</span>`).join("")}
      <div id="edge-evidence">${t.evidence.map(s=>`<div class="evidence">
        ${e==="quarantine"?`<span class="tag">${ae(s.factual_status||"")}</span>`:""}
        <p>${ae(s.evidence_text||"")}</p>
        <small><a href="${ae(s.source_url||"#")}" target="_blank" rel="noopener noreferrer">${ae(s.publisher||"B\xE0i b\xE1o")}</a>
        \xB7 ${ae(s.published_at||"Kh\xF4ng r\xF5 ng\xE0y")}</small></div>`).join("")}</div>
      ${t.total>t.evidence.length?'<button id="more-evidence" class="inline-action" type="button">Xem th\xEAm b\u1EB1ng ch\u1EE9ng</button>':""}`,V("#relation-list").innerHTML='<p class="help">Click node \u0111\u1EC3 quay l\u1EA1i danh s\xE1ch quan h\u1EC7 c\u1EE7a node \u0111\xF3.</p>';let o=V("#more-evidence");o&&(o.onclick=()=>Xs(a,t.evidence.length,t.total,e))}catch(t){V("#inspector").textContent=t.message}}async function Xs(a,n,e,t){let r=await bt(`/api/graph/edge/${encodeURIComponent(a)}?mode=${t}&offset=${n}&limit=20`);if(B.mode!==t)return;let i=V("#edge-evidence");for(let s of r.evidence){let l=document.createElement("div");l.className="evidence",l.innerHTML=`<p>${ae(s.evidence_text||"")}</p><small><a href="${ae(s.source_url||"#")}"
      target="_blank" rel="noopener noreferrer">${ae(s.publisher||"B\xE0i b\xE1o")}</a> \xB7 ${ae(s.published_at||"")}</small>`,i.append(l)}let o=n+r.evidence.length;o>=e||!r.evidence.length?V("#more-evidence")?.remove():V("#more-evidence").onclick=()=>Xs(a,o,e,t)}function Ys(a,n,e){let t;a.addEventListener("input",()=>{clearTimeout(t);let r=a.value.trim();if(r.length<2){n.replaceChildren();return}let i=B.mode;t=setTimeout(async()=>{try{let o=await bt(`/api/search?mode=${i}&q=${encodeURIComponent(r)}&limit=15`);if(i!==B.mode||a.value.trim()!==r)return;n.replaceChildren(...o.map(s=>{let l=document.createElement("button");return l.type="button",l.innerHTML=`${ae(s.name)}<small>${ae(s.entity_type)} \xB7 b\u1EADc ${ve(s.degree)}</small>`,l.onclick=()=>{n.replaceChildren(),a.value=s.name,e(s)},l})),o.length||(n.textContent="Kh\xF4ng t\xECm th\u1EA5y node.")}catch(o){n.textContent=o.message}},200)})}async function bf(){if(!B.focusId||!B.target)return;let a=V("#question").value.trim()||"Hai th\u1EF1c th\u1EC3 li\xEAn h\u1EC7 v\u1EDBi nhau nh\u01B0 th\u1EBF n\xE0o?";V("#answer").textContent="\u0110ang t\xECm \u0111\u01B0\u1EDDng \u0111i v\xE0 ch\u1EE9ng c\u1EE9\u2026";try{let n=await bt("/api/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({mode:B.mode,start_id:B.focusId,target_id:B.target.node_id,question:a})});V("#answer").innerHTML=`<p>${ae(n.answer)}</p><small>${ae(n.path.retrieval_backend)} \xB7
      ${n.path.hops??"kh\xF4ng c\xF3"} b\u01B0\u1EDBc \xB7 ${n.model_used?"Qwen3.5:9b":"tr\xECnh b\xE0y t\u1EEB graph"}</small>
      ${n.sources.map(e=>`<div class="source">[${e.number}] ${ae(e.subject)} \u2192
        ${ae(e.predicate)} \u2192 ${ae(e.object)} \xB7 <a href="${ae(e.evidence[0]?.source_url||"#")}"
        target="_blank" rel="noopener noreferrer">${ae(e.evidence[0]?.publisher||"B\xE0i b\xE1o")}</a></div>`).join("")}`}catch(n){V("#answer").textContent=n.message}}V("#mode").value=B.mode;V("#mode").onchange=a=>{B.mode=a.target.value,B.view="overview",B.focusId=null,B.communityId=null,B.target=null,B.metrics=null,B.options=null,B.graphData=null,++B.request,Pr(),V("#inspector").innerHTML='<p class="muted">Click c\u1ED9ng \u0111\u1ED3ng, node ho\u1EB7c c\u1EA1nh \u0111\u1EC3 xem chi ti\u1EBFt.</p>',V("#relation-list").replaceChildren(),V("#search").value="",V("#target").value="",V("#search-results").replaceChildren(),V("#target-results").replaceChildren(),V("#ask").disabled=!0,V("#answer").textContent="Ch\u1ECDn node ngu\u1ED3n v\xE0 \u0111\xEDch \u0111\u1EC3 h\u1ECFi.",Fr(),Vs(),qs()};V("#view-tabs").querySelectorAll("button").forEach(a=>a.onclick=()=>zn(a.dataset.view,a.dataset.view==="neighborhood"?B.focusId:null));V("#apply").onclick=()=>{let{nodeLimit:a,edgeLimit:n}=$s();(B.view==="global"||B.view==="community")&&(B.limits.global=[a,n]),B.view==="neighborhood"&&(B.limits.neighborhood=[a,n]),Pa()};V("#reset").onclick=()=>{V("#min-degree").value=1,V("#hops").value=1,document.querySelectorAll(".checks input").forEach(n=>{n.checked=!0}),B.limits={global:[300,700],neighborhood:[80,200]};let a=B.view==="neighborhood"?B.limits.neighborhood:B.limits.global;V("#node-limit").value=a[0],V("#edge-limit").value=a[1],Pa()};V("#show-all").onclick=()=>{B.metrics&&(V("#min-degree").value=0,V("#node-limit").value=B.metrics.node_count,V("#edge-limit").value=B.options?.eligible_edges||B.metrics.edge_count,B.limits.global=[Number(V("#node-limit").value),Number(V("#edge-limit").value)],zn("global"))};V("#fit").onclick=()=>B.renderer?.getCamera().animate({x:.5,y:.5,ratio:1},{duration:350});V("#ask").onclick=bf;Ys(V("#search"),V("#search-results"),a=>Ir(a.node_id));Ys(V("#target"),V("#target-results"),a=>{B.target=a,V("#ask").disabled=!B.focusId});Fr();qs();})();
/*! Bundled license information:

sigma/dist/edge-data-texture-e4fbbc22.esm.js:
  (*! regenerator-runtime -- Copyright (c) 2014-present, Facebook, Inc. -- license (MIT): https://github.com/babel/babel/blob/main/packages/babel-helpers/LICENSE *)
*/
