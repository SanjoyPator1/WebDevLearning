export function getTrueKeys(obj) {
  const trueKeys = [];
  for (const [key, value] of Object.entries(obj)) {
    if (value === true) {
      trueKeys.push(key);
    }
  }
  return trueKeys;
}
