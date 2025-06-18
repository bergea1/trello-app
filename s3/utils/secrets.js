import { readFile } from 'fs/promises';

export async function readSecret(name) {
  const path = `/run/secrets/${name}`;
  try {
    const data = await readFile(path, 'utf8');
    return data.trim();
  } catch (err) {
    console.warn(`Warning: Could not read secret "${name}": ${err.message}`);
    return null;
  }
}
