!function(e,t){var a=function(){t(e.lazySizes),e.removeEventListener("lazyunveilread",a,!0)};t=t.bind(null,e,e.document),"object"==typeof module&&module.exports?t(require("lazysizes")):"function"==typeof define&&define.amd?define(["lazysizes"],t):e.lazySizes?a():e.addEventListener("lazyunveilread",a,!0)}(window,function(e,z,c){"use strict";var g,y,b,f,r,l,s,v,m;e.addEventListener&&(g=c.cfg,y=/\s+/g,b=/\s*\|\s+|\s+\|\s*/g,f=/^(.+?)(?:\s+\[\s*(.+?)\s*\])(?:\s+\[\s*(.+?)\s*\])?$/,r=/^\s*\(*\s*type\s*:\s*(.+?)\s*\)*\s*$/,l=/\(|\)|'/,s={contain:1,cover:1},v=function(e,t){var a;t&&((a=t.match(r))&&a[1]?e.setAttribute("type",a[1]):e.setAttribute("media",g.customMedia[t]||t))},m=function(e){var t,a,r,i,s;e.target._lazybgset&&(a=(t=e.target)._lazybgset,(r=t.currentSrc||t.src)&&(i=l.test(r)?JSON.stringify(r):r,(s=c.fire(a,"bgsetproxy",{src:r,useSrc:i,fullSrc:null})).defaultPrevented||(a.style.backgroundImage=s.detail.fullSrc||"url("+s.detail.useSrc+")")),t._lazybgsetLoading&&(c.fire(a,"_lazyloaded",{},!1,!0),delete t._lazybgsetLoading))},addEventListener("lazybeforeunveil",function(e){var t,a,r,i,s,l,n,d,u,o;!e.defaultPrevented&&(t=e.target.getAttribute("data-bgset"))&&(u=e.target,(o=z.createElement("img")).alt="",o._lazybgsetLoading=!0,e.detail.firesLoad=!0,a=t,r=u,i=o,s=z.createElement("picture"),l=r.getAttribute(g.sizesAttr),n=r.getAttribute("data-ratio"),d=r.getAttribute("data-optimumx"),r._lazybgset&&r._lazybgset.parentNode==r&&r.removeChild(r._lazybgset),Object.defineProperty(i,"_lazybgset",{value:r,writable:!0}),Object.defineProperty(r,"_lazybgset",{value:s,writable:!0}),a=a.replace(y," ").split(b),s.style.display="none",i.className=g.lazyClass,1!=a.length||l||(l="auto"),a.forEach(function(e){var t,a=z.createElement("source");l&&"auto"!=l&&a.setAttribute("sizes",l),(t=e.match(f))?(a.setAttribute(g.srcsetAttr,t[1]),v(a,t[2]),v(a,t[3])):a.setAttribute(g.srcsetAttr,e),s.appendChild(a)}),l&&(i.setAttribute(g.sizesAttr,l),r.removeAttribute(g.sizesAttr),r.removeAttribute("sizes")),d&&i.setAttribute("data-optimumx",d),n&&i.setAttribute("data-ratio",n),s.appendChild(i),r.appendChild(s),setTimeout(function(){c.loader.unveil(o),c.rAF(function(){c.fire(o,"_lazyloaded",{},!0,!0),o.complete&&m({target:o})})}))}),z.addEventListener("load",m,!0),e.addEventListener("lazybeforesizes",function(e){var t,a,r,i;e.detail.instance==c&&e.target._lazybgset&&e.detail.dataAttr&&(t=e.target._lazybgset,r=t,i=(getComputedStyle(r)||{getPropertyValue:function(){}}).getPropertyValue("background-size"),!s[i]&&s[r.style.backgroundSize]&&(i=r.style.backgroundSize),s[a=i]&&(e.target._lazysizesParentFit=a,c.rAF(function(){e.target.setAttribute("data-parent-fit",a),e.target._lazysizesParentFit&&delete e.target._lazysizesParentFit})))},!0),z.documentElement.addEventListener("lazybeforesizes",function(e){var t,a;!e.defaultPrevented&&e.target._lazybgset&&e.detail.instance==c&&(e.detail.width=(t=e.target._lazybgset,a=c.gW(t,t.parentNode),(!t._lazysizesWidth||a>t._lazysizesWidth)&&(t._lazysizesWidth=a),t._lazysizesWidth))}))});

