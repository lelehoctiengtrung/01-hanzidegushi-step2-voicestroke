const puppeteer = require('puppeteer');
const path = require('path');

async function capture() {
    console.log("Launching Puppeteer...");
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    await page.setViewport({ width: 540, height: 960, deviceScaleFactor: 2 });
    
    const htmlPath = 'file://' + path.resolve('/Users/hanario/Downloads/lelehoctiengtrung/PROJECTS/小/index.html');
    console.log("Opening page:", htmlPath);
    
    await page.goto(htmlPath, { waitUntil: 'networkidle0' });
    
    // Set simulation time to 1.0 second
    await page.evaluate(() => {
        if (window.setSimulationTime) {
            window.setSimulationTime(1.0);
        }
    });
    await new Promise(r => setTimeout(r, 500));
    let element = await page.$('.animated-char-box');
    if (element) {
        await element.screenshot({ path: '/Users/hanario/.gemini/antigravity/brain/94b67fc0-8847-4e3f-8ddf-9a75bd1f66bd/char_box_1s.png' });
    }

    // Set simulation time to 5.0 seconds
    await page.evaluate(() => {
        if (window.setSimulationTime) {
            window.setSimulationTime(5.0);
        }
    });
    await new Promise(r => setTimeout(r, 500));
    if (element) {
        await element.screenshot({ path: '/Users/hanario/.gemini/antigravity/brain/94b67fc0-8847-4e3f-8ddf-9a75bd1f66bd/char_box_5s.png' });
    }

    // Set simulation time to 10.0 seconds
    await page.evaluate(() => {
        if (window.setSimulationTime) {
            window.setSimulationTime(10.0);
        }
    });
    await new Promise(r => setTimeout(r, 500));
    if (element) {
        await element.screenshot({ path: '/Users/hanario/.gemini/antigravity/brain/94b67fc0-8847-4e3f-8ddf-9a75bd1f66bd/char_box_10s.png' });
    }
    
    // Let's also take a screenshot of the cover frame (time = 0)
    await page.evaluate(() => {
        if (window.setSimulationTime) {
            window.setSimulationTime(0.0);
        }
    });
    await new Promise(r => setTimeout(r, 500));
    const coverElement = await page.$('.animated-char-box');
    if (coverElement) {
        await coverElement.screenshot({ path: '/Users/hanario/.gemini/antigravity/brain/94b67fc0-8847-4e3f-8ddf-9a75bd1f66bd/char_box_cover_preview.png' });
        console.log("Screenshot of cover char box saved.");
    }
    
    await browser.close();
}

capture().catch(console.error);
