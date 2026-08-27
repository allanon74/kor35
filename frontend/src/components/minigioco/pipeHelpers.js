/** Utility condivise per pipe_connect (FE). */

export const rotatePipeMask = (mask, times) => {
  let conn = mask & 15;
  for (let t = 0; t < (times % 4); t += 1) {
    let next = 0;
    if (conn & 1) next |= 2;
    if (conn & 2) next |= 4;
    if (conn & 4) next |= 8;
    if (conn & 8) next |= 1;
    conn = next;
  }
  return conn;
};

/** Celle raggiungibili da `start` con le connessioni attuali. */
export const pipeReachableFrom = (size, bases, rotations, start = 0) => {
  const total = size * size;
  if (!bases?.length || bases.length !== total) return new Set();
  const conns = bases.map((b, i) => rotatePipeMask(Number(b) || 0, Number(rotations?.[i]) || 0));
  const stack = [start];
  const seen = new Set([start]);
  const dirs = [
    [-1, 0, 1, 4],
    [0, 1, 2, 8],
    [1, 0, 4, 1],
    [0, -1, 8, 2],
  ];
  while (stack.length) {
    const cur = stack.pop();
    const r = Math.floor(cur / size);
    const c = cur % size;
    for (const [dr, dc, outM, inM] of dirs) {
      const nr = r + dr;
      const nc = c + dc;
      if (nr >= 0 && nr < size && nc >= 0 && nc < size) {
        const nxt = nr * size + nc;
        if (!seen.has(nxt) && (conns[cur] & outM) && (conns[nxt] & inM)) {
          seen.add(nxt);
          stack.push(nxt);
        }
      }
    }
  }
  return seen;
};

export const isPipeSolved = (size, bases, rotations, start, end) => {
  const reachable = pipeReachableFrom(size, bases, rotations, start);
  return reachable.has(end);
};
