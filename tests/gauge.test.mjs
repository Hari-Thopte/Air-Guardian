import test from 'node:test';
import assert from 'node:assert/strict';
import {gaugeGeometry} from '../assets/day-ui.js';
test('gauge uses one fixed concentration scale and correct needle coordinates',()=>{
  let previous=-Infinity;
  for(const value of [8,30,45,113,150]){
    const {maximum,x,y}=gaugeGeometry(value);
    assert.equal(maximum,150);
    const angle=Math.PI*(1-value/150);
    assert.ok(Math.abs(x-(100+72*Math.cos(angle)))<1e-8);
    assert.ok(Math.abs(y-(100-72*Math.sin(angle)))<1e-8);
    assert.ok(x>previous);previous=x;
    assert.ok(x>=28&&x<=172&&y>=28&&y<=100);
  }
  assert.equal(gaugeGeometry(1000).x,172);
  assert.equal(gaugeGeometry(-1).x,28);
});
