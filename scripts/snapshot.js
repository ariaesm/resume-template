// Render docs/ screenshots and an example PDF from out/*.html with Playwright.
// Usage: python3 render_resume.py && python3 render_resume.py examples/resume-fa.yaml
//        node scripts/snapshot.js
const path = require("path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const jobs = [
  { html: "out/resume.html", png: "docs/screenshot.png", pdf: "docs/resume-example.pdf" },
  { html: "out/resume-fa.html", png: "docs/screenshot-rtl.png" },
];

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 900, height: 1200 } });
  for (const job of jobs) {
    await page.goto("file://" + path.join(root, job.html), { waitUntil: "networkidle" });
    await page.screenshot({ path: path.join(root, job.png), fullPage: true });
    console.log("wrote", job.png);
    if (job.pdf) {
      await page.pdf({ path: path.join(root, job.pdf), format: "A4", printBackground: true, preferCSSPageSize: true });
      console.log("wrote", job.pdf);
    }
  }
  await browser.close();
})();
