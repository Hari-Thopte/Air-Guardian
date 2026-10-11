import test from 'node:test';
import assert from 'node:assert/strict';
import {roleContext,roleScene} from '../assets/role-ui.js';
const workspace=role=>({membership:{role,class_id:'a'},classes:[{id:'a',label:'Class 3 A'}],children:[{alias:'Child A',class_id:'a',extraCaution:true}],checklist:[{id:'gate',role:'staff'},{id:'class',role:'teacher'}]});
test('role hub uses verified membership rather than a URL role',()=>{
  assert.equal(roleContext(workspace('teacher')).classLabel,'Class 3 A');
  assert.equal(roleContext(workspace('parent')).identity.title,'Today for my child');
});
test('staff presentation never receives child summaries and only exposes own tasks',()=>{
  const context=roleContext(workspace('staff'));
  assert.deepEqual(context.children,[]);assert.deepEqual(context.tasks.map(t=>t.id),['gate']);
});
test('caution indicator is teacher only and missing class remains explicit',()=>{
  const w=workspace('teacher');w.membership.class_id='missing';
  assert.equal(roleContext(w).classLabel,'School-linked class');
  assert.equal(roleContext(w).children[0].extraCaution,true);
  assert.equal(roleContext(workspace('parent')).children[0].extraCaution,false);
});
test('each role has a distinct illustration and arbitrary role text cannot enter SVG',()=>{
  assert.equal(new Set(['admin','teacher','staff','parent','kid'].map(roleScene)).size,5);
  assert.equal(roleScene('<script>'),roleScene('admin'));
});
