const { readSecret } = require('./utils/secrets');

let configPromise;

async function loadConfig() {
  const [
    WEBSITE_URL,
    TARGET_URL,
    SPACE_BUCKET,
    SPACE_REGION,
    SPACE_KEY,
    SPACE_SECRET,
    SPACE_PATH,
    SPACE_ENDPOINT
  ] = await Promise.all([
    readSecret('website_url'),
    readSecret('target_url'),
    readSecret('space_bucket'),
    readSecret('space_region'),
    readSecret('space_key'),
    readSecret('space_secret'),
    readSecret('space_path'),
    readSecret('space_endpoint')
  ]);

  return {
    WEBSITE_URL,
    TARGET_URL,
    SPACE_BUCKET,
    SPACE_REGION,
    SPACE_KEY,
    SPACE_SECRET,
    SPACE_PATH,
    SPACE_ENDPOINT,
  };
}

function getConfig() {
  if (!configPromise) {
    configPromise = loadConfig();
  }
  return configPromise;
}

module.exports = { getConfig };
