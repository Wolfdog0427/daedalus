export function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

export function randomChoice<T>(items: T[]): T {
  if (items.length === 0) {
    throw new Error('randomChoice: empty array');
  }
  const idx = randomInt(0, items.length - 1);
  return items[idx];
}

/** Fisher-Yates partial shuffle to pick `count` unique items. */
export function randomSubset<T>(items: T[], count: number): T[] {
  if (count >= items.length) return [...items];
  const pool = [...items];
  const result: T[] = [];
  for (let i = 0; i < count; i++) {
    const idx = randomInt(0, pool.length - 1);
    result.push(pool[idx]);
    pool[idx] = pool[pool.length - 1];
    pool.pop();
  }
  return result;
}
