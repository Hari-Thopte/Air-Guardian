// Safe text interpolation. Deliberate markup composition needs explicit reviewed nodes.
export const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function html(strings,...values){return strings.reduce((result,part,i)=>result+part+(i<values.length?escape(values[i]):''),'');}
