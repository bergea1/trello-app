const fs = require('fs').promises;

async function readSecret(name) {
  const path = `/run/secrets/${name}`;
  try {
    const data = await fs.readFile(path, 'utf8');
    return data.trim();
  } catch (err) {
    console.warn(`Warning: Could not read secret "${name}": ${err.message}`);
    return null;
  }
}

module.exports = { readSecret };
