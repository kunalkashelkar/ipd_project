import{c as o,b as y,u as b,r as l,j as e,m as c,d as j}from"./index-6e-d2_PM.js";import{C as w}from"./Card-BeLWx0lV.js";import{Z as N}from"./zap-BG513Gx0.js";import{S as k}from"./shield-check-DQrTA_JS.js";/**
 * @license lucide-react v0.390.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const u=o("Check",[["path",{d:"M20 6 9 17l-5-5",key:"1gmf2c"}]]);/**
 * @license lucide-react v0.390.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const v=o("Database",[["ellipse",{cx:"12",cy:"5",rx:"9",ry:"3",key:"msslwz"}],["path",{d:"M3 5V19A9 3 0 0 0 21 19V5",key:"1wlel7"}],["path",{d:"M3 12A9 3 0 0 0 21 12",key:"mv7ke4"}]]);/**
 * @license lucide-react v0.390.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const C=o("LoaderCircle",[["path",{d:"M21 12a9 9 0 1 1-6.219-8.56",key:"13zald"}]]);/**
 * @license lucide-react v0.390.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const S=o("Network",[["rect",{x:"16",y:"16",width:"6",height:"6",rx:"1",key:"4q2zg0"}],["rect",{x:"2",y:"16",width:"6",height:"6",rx:"1",key:"8cvhb9"}],["rect",{x:"9",y:"2",width:"6",height:"6",rx:"1",key:"1egb70"}],["path",{d:"M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3",key:"1jsf9p"}],["path",{d:"M12 12V8",key:"2874zd"}]]),n=[{id:"parse",label:"Parsing Source Code (Joern)",icon:v,duration:2e3},{id:"taint",label:"Extracting Data Flow & Taint Paths",icon:S,duration:3e3},{id:"gnn",label:"GNN Vulnerability Classification",icon:N,duration:4e3},{id:"llm",label:"LLM Explainability Generation",icon:k,duration:3e3}];function T(){const{id:d}=y(),m=b(),[r,h]=l.useState(0),[x,p]=l.useState(!1);l.useEffect(()=>{let s;const t=a=>{if(a>=n.length){p(!0),s=setTimeout(()=>{m(`/projects/${d}/results`)},1e3);return}s=setTimeout(()=>{h(a+1),t(a+1)},n[a].duration)};return t(0),()=>clearTimeout(s)},[d,m]);const g=Math.min(r/n.length*100,100);return e.jsxs("div",{className:"flex flex-col items-center justify-center min-h-[60vh] max-w-2xl mx-auto py-12",children:[e.jsxs("div",{className:"text-center mb-12",children:[e.jsx("h1",{className:"text-3xl font-bold font-display text-foreground mb-4",children:"Pipeline Execution in Progress"}),e.jsx("p",{className:"text-muted-foreground max-w-md mx-auto",children:"The hybrid XAI vulnerability detection engine is currently analyzing your codebase. Please do not close this window."})]}),e.jsxs(w,{className:"w-full p-8 relative overflow-hidden bg-card/50",children:[e.jsx("div",{className:"absolute top-0 left-0 h-1 bg-muted w-full",children:e.jsx(c.div,{className:"h-full bg-primary",initial:{width:0},animate:{width:`${g}%`},transition:{duration:.5,ease:"easeInOut"}})}),e.jsx("div",{className:"space-y-6 mt-4",children:n.map((s,t)=>{const a=t<r,i=t===r,f=t>r;return e.jsxs("div",{className:`flex items-center gap-4 transition-all duration-500 ${f?"opacity-40":"opacity-100"} ${i?"scale-105":"scale-100"}`,children:[e.jsx("div",{className:`
                  w-10 h-10 rounded-full flex items-center justify-center shrink-0 transition-colors
                  ${a?"bg-emerald-500/20 text-emerald-500":i?"bg-primary/20 text-primary ring-2 ring-primary ring-offset-2 ring-offset-background":"bg-muted text-muted-foreground"}
                `,children:a?e.jsx(u,{className:"w-5 h-5"}):i?e.jsx(C,{className:"w-5 h-5 animate-spin"}):e.jsx(s.icon,{className:"w-5 h-5"})}),e.jsxs("div",{className:"flex-1",children:[e.jsx("h3",{className:`font-medium ${i?"text-primary":a?"text-foreground":"text-muted-foreground"}`,children:s.label}),e.jsx(j,{children:i&&e.jsxs(c.p,{initial:{opacity:0,height:0},animate:{opacity:1,height:"auto"},exit:{opacity:0,height:0},className:"text-sm text-muted-foreground mt-1",children:[t===0&&"Generating Abstract Syntax Trees & Control Flow Graphs...",t===1&&"Identifying sources, sinks, and vulnerable edges...",t===2&&"Running node classification against trained models...",t===3&&"Compiling explanations and mitigation strategies..."]})})]})]},s.id)})})]}),x&&e.jsxs(c.div,{initial:{opacity:0,y:10},animate:{opacity:1,y:0},className:"mt-8 text-emerald-500 flex items-center gap-2 font-medium",children:[e.jsx(u,{className:"w-5 h-5"}),"Pipeline Complete. Redirecting to workspace..."]})]})}export{T as default};
