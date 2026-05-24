import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { google } from "googleapis";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const URLS_FILE = path.join(__dirname, "urls.txt");
const KEY_FILE = path.join(__dirname, "service-account.json");
const ALLOWED_PREFIXES = [
  "https://dsdepannage.fr/",
  "https://www.dsdepannage.fr/"
];
const DELAY_MS = 500;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function fileExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

function isAllowedUrl(url) {
  return ALLOWED_PREFIXES.some((prefix) => url.startsWith(prefix));
}

async function readUrls() {
  const content = await fs.readFile(URLS_FILE, "utf8");
  const urls = [];
  const rejected = [];

  content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .forEach((url, index) => {
      if (isAllowedUrl(url)) {
        urls.push(url);
      } else {
        rejected.push({ line: index + 1, url });
      }
    });

  return { urls: [...new Set(urls)], rejected };
}

async function main() {
  console.log("Google Indexing API - dsdepannage.fr");
  console.log("----------------------------------------");

  if (!(await fileExists(KEY_FILE))) {
    console.error("Erreur: service-account.json est introuvable dans google-indexing.");
    console.error("Place la cle JSON du compte de service dans ce dossier avant de relancer.");
    process.exitCode = 1;
    return;
  }

  const { urls, rejected } = await readUrls();

  if (rejected.length > 0) {
    console.warn("URLs ignorees car elles ne commencent pas par dsdepannage.fr:");
    rejected.forEach((item) => console.warn(`- ligne ${item.line}: ${item.url}`));
    console.log("");
  }

  if (urls.length === 0) {
    console.error("Aucune URL valide trouvee dans urls.txt.");
    process.exitCode = 1;
    return;
  }

  const auth = new google.auth.GoogleAuth({
    keyFile: KEY_FILE,
    scopes: ["https://www.googleapis.com/auth/indexing"]
  });

  const authClient = await auth.getClient();
  const indexing = google.indexing({ version: "v3", auth: authClient });

  let successCount = 0;
  let errorCount = 0;
  const errors = [];

  for (const [index, url] of urls.entries()) {
    const current = index + 1;
    console.log(`[${current}/${urls.length}] Envoi: ${url}`);

    try {
      const response = await indexing.urlNotifications.publish({
        requestBody: {
          url,
          type: "URL_UPDATED"
        }
      });

      successCount += 1;
      const notifyTime = response.data?.urlNotificationMetadata?.latestUpdate?.notifyTime;
      console.log(`OK${notifyTime ? ` - notifyTime: ${notifyTime}` : ""}`);
    } catch (error) {
      errorCount += 1;
      const message = error?.response?.data?.error?.message || error.message || "Erreur inconnue";
      errors.push({ url, message });
      console.error(`ERREUR: ${message}`);
    }

    if (current < urls.length) {
      await sleep(DELAY_MS);
    }
  }

  console.log("");
  console.log("Resume final");
  console.log("------------");
  console.log(`URLs valides lues: ${urls.length}`);
  console.log(`URLs envoyees avec succes: ${successCount}`);
  console.log(`Erreurs: ${errorCount}`);
  console.log(`URLs ignorees: ${rejected.length}`);

  if (errors.length > 0) {
    console.log("");
    console.log("Details des erreurs:");
    errors.forEach((item) => console.log(`- ${item.url}: ${item.message}`));
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error("Erreur fatale:", error.message || error);
  process.exitCode = 1;
});
