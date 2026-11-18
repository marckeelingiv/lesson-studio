// Layout is plain world-space geometry; content and camera do not own it.
export const cards = [
  {id:'question', title:'01 / Question', x:0, y:0, width:1120, height:630, page:'Question'},
  {id:'evidence', title:'02 / Evidence', x:1240, y:0, width:1120, height:630, page:'Evidence'},
  {id:'definition', title:'03 / Definition', x:2480, y:0, width:1120, height:630, page:'Definition'},
  {id:'answer', title:'04 / Answer', x:3720, y:0, width:1120, height:630, page:'Answer'},
  {id:'trust', title:'05 / Trust and limits', x:4960, y:0, width:1120, height:630, page:'Trust / limits'},
  {id:'lineage', title:'Manifest lineage', x:1240, y:780, width:1440, height:920},
  {id:'table', title:'Saved table / bounded preview', x:2800, y:780, width:1440, height:920},
  {id:'sql', title:'Transformation / never execute', x:2800, y:1820, width:1440, height:900},
  {id:'governance', title:'Column governance / declarations', x:4360, y:780, width:1000, height:920},
  {id:'provenance', title:'Evidence provenance', x:4360, y:1820, width:1120, height:900},
  {id:'tools', title:'External evidence surfaces', x:0, y:780, width:1120, height:920},
];
export const route = ['question', 'evidence', 'lineage', 'table', 'definition', 'sql', 'governance', 'answer', 'tools', 'trust', 'provenance'];
export function routeNext(id, direction) {
  return route[Math.max(0, Math.min(route.length - 1, route.indexOf(id) + direction))];
}
export function boardBounds(items = cards) {
  const x = Math.min(...items.map(card => card.x)), y = Math.min(...items.map(card => card.y));
  return {x, y, width:Math.max(...items.map(card => card.x + card.width)) - x,
    height:Math.max(...items.map(card => card.y + card.height)) - y};
}
