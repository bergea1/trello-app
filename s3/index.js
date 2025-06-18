import puppeteer from 'puppeteer-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';
import dotenv from 'dotenv';
import { S3, PutObjectCommand, GetObjectCommand } from "@aws-sdk/client-s3";
import fs from 'fs/promises';
import { getConfig } from './config.js';

dotenv.config();
puppeteer.use(StealthPlugin());

const REFRESH_INTERVAL = 5 * 60 * 1000;

const requestHeaders = {
  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
  Referer: 'https://www.google.com/',
};

(async () => {
  const config = await getConfig();
  console.log('Loaded config:', config);

  const s3Client = new S3({
    forcePathStyle: false,
    endpoint: `https://${config.SPACE_REGION}.digitaloceanspaces.com`,
    region: config.SPACE_REGION,
    credentials: {
      accessKeyId: config.SPACE_KEY,
      secretAccessKey: config.SPACE_SECRET,
    },
  });

  async function readS3File() {
    try {
      const command = new GetObjectCommand({
        Bucket: config.SPACE_BUCKET,
        Key: config.SPACE_PATH,
      });

      const { Body } = await s3Client.send(command);

      const streamToString = (stream) =>
        new Promise((resolve, reject) => {
          const chunks = [];
          stream.on("data", (chunk) => chunks.push(chunk));
          stream.on("end", () => resolve(Buffer.concat(chunks).toString("utf-8")));
          stream.on("error", reject);
        });

      return await streamToString(Body);
    } catch (err) {
      console.error("Error reading file from S3:", err);
    }
  }

  async function uploadToS3() {
    const fileBuffer = await fs.readFile('./localStorage.json');
    try {
      const command = new PutObjectCommand({
        Bucket: config.SPACE_BUCKET,
        Key: config.SPACE_PATH,
        Body: fileBuffer,
        ContentType: "application/json",
      });

      await s3Client.send(command);
      console.log("File uploaded successfully.");
    } catch (err) {
      console.error("Error uploading file to S3:", err);
    }
  }

  async function loginWithGoogle() {
    let browser;
    const fileContent = await readS3File();
    if (!fileContent) return;

    try {
      browser = await puppeteer.launch({
        headless: true,
        defaultViewport: null,
        executablePath: '/usr/bin/google-chrome',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
      });

      const page = await browser.newPage();
      await page.setDefaultNavigationTimeout(0);
      await page.setDefaultTimeout(0);
      await page.setExtraHTTPHeaders({ ...requestHeaders });
      await page.setViewport({ width: 1200, height: 692 });
      await page.goto(config.WEBSITE_URL, { waitUntil: 'load' });

      await page.evaluate(storage => {
        try {
          const data = JSON.parse(storage);
          for (let key in data) {
            localStorage.setItem(key, data[key]);
          }
          console.log("localStorage successfully restored!");
        } catch (err) {
          console.error("Error parsing localStorage JSON:", err);
        }
      }, fileContent);

      await checkLogin(page);

      while (true) {
        await refreshAndGetToken(page);
        await new Promise(resolve => setTimeout(resolve, REFRESH_INTERVAL));
      }

    } catch (error) {
      console.error("Error during login:", error);
    } finally {
      if (browser && browser.close) {
        await browser.close();
        console.log("Browser closed.");
      }
    }
  }

  async function checkLogin(page) {
    while (true) {
      await new Promise(resolve => setTimeout(resolve, 10000));
      await page.goto(config.TARGET_URL, { waitUntil: 'load' });
      if (page.url().includes(config.TARGET_URL)) {
        console.log("Logged in successfully! Retrieving token...");
        return;
      }
    }
  }

  async function refreshAndGetToken(page) {
    if (!page || page.isClosed()) {
      console.error("ERROR: `page` is undefined! Cannot refresh.");
      return;
    }

    try {
      console.log("Refreshing page...");

      await page.reload({ waitUntil: "domcontentloaded" });
      await new Promise(resolve => setTimeout(resolve, 2000));

      const localStorageData = await page.evaluate(() => {
        const data = {};
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          data[key] = localStorage.getItem(key);
        }
        return data;
      });

      await fs.writeFile('./localStorage.json', JSON.stringify(localStorageData, null, 2), 'utf-8');
      await uploadToS3();

      const token = await page.evaluate(() => localStorage.getItem('cf.escenic.credentials') || '');
      console.log("Token:", token);
      // sendToken(token);

    } catch (error) {
      console.error("Error during token retrieval:", error);
    }
  }

  async function keepSessionAlive() {
    while (true) {
      try {
        await loginWithGoogle();
      } catch (err) {
        console.error("Session crashed:", err);
      }

      console.log("Restarting session in 10 seconds...");
      await new Promise(res => setTimeout(res, 10000));
    }
  }

  // Start the whole process
  await keepSessionAlive();
})();