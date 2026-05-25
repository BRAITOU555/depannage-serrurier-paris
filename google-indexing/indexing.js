import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { google } from "googleapis";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const URLS_FILE = path.join(__dirname, "urls.txt");
const KEY_FILE = path.join(__dirname, "service-account.json");
const LOG_FILE = path.join(__dirname, "sent-log.csv");
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

function explainGoogleError(message) {
  if (/Failed to verify the URL ownership|Permission denied/i.test(message)) {
    return [
      message,
      "Cause probable: le compte de service n'est pas proprietaire ou utilisateur complet de la propriete Search Console qui couvre cette URL.",
      "A verifier: Search Console > Parametres > Utilisateurs et autorisations, avec l'email client du service-account.json."
    ].join(" ");
  }

  if (/Quota exceeded/i.test(message)) {
    return [
      message,
      "Cause probable: quota journalier Google Indexing API atteint.",
      "Solution: relancer demain ou demander une augmentation de quota dans Google Cloud."
    ].join(" ");
  }

  if (/API has not been used|disabled/i.test(message)) {
    return [
      message,
      "Cause probable: Google Indexing API non activee sur le projet Google Cloud du compte de service.",
      "Solution: activer Web Search Indexing API / Indexing API dans Google Cloud."
    ].join(" ");
  }

  return message;
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

function csvEscape(value) {
  return `"${String(value ?? "").replaceAll('"', '""')}"`;
}

async function appendLog({ url, status, message }) {
  const exists = await fileExists(LOG_FILE);
  const now = new Date().toISOString();
  const line = [
    now,
    url,
    status,
    message
  ].map(csvEscape).join(",") + "\n";

  if (!exists) {
    await fs.writeFile(LOG_FILE, "date,url,status,message\n", "utf8");
  }

  await fs.appendFile(LOG_FILE, line, "utf8");
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
      await appendLog({
        url,
        status: "OK",
        message: notifyTime ? `notifyTime: ${notifyTime}` : "URL_UPDATED envoye"
      });
    } catch (error) {
      errorCount += 1;
      const rawMessage = error?.response?.data?.error?.message || error.message || "Erreur inconnue";
      const message = explainGoogleError(rawMessage);
      errors.push({ url, message });
      console.error(`ERREUR: ${message}`);
      await appendLog({
        url,
        status: "ERREUR",
        message
      });
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
