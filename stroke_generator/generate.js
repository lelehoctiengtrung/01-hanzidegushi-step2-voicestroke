const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const http = require('http');
const { execSync } = require('child_process');

const CONFIG = {
    character: '门',
    width: 500,
    height: 500,
    fps: 15,
    outputDir: path.join(__dirname, 'output'),
    tempDir: path.join(__dirname, 'temp')
};

if (!fs.existsSync(CONFIG.outputDir)) fs.mkdirSync(CONFIG.outputDir, { recursive: true });
if (!fs.existsSync(CONFIG.tempDir)) fs.mkdirSync(CONFIG.tempDir, { recursive: true });

function checkFFmpeg() {
    try {
        execSync('ffmpeg -version', { stdio: 'ignore' });
        return true;
    } catch {
        return false;
    }
}

function getContentType(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    if (ext === '.html') return 'text/html; charset=utf-8';
    if (ext === '.js') return 'application/javascript; charset=utf-8';
    if (ext === '.json') return 'application/json; charset=utf-8';
    if (ext === '.css') return 'text/css; charset=utf-8';
    if (ext === '.svg') return 'image/svg+xml';
    if (ext === '.png') return 'image/png';
    if (ext === '.gif') return 'image/gif';
    return 'application/octet-stream';
}

function startStaticServer(rootDir) {
    const server = http.createServer((req, res) => {
        try {
            const requestUrl = new URL(req.url, 'http://127.0.0.1');
            const pathname = decodeURIComponent(requestUrl.pathname === '/' ? '/index.html' : requestUrl.pathname);
            const requestedPath = path.resolve(rootDir, `.${pathname}`);

            if (!requestedPath.startsWith(rootDir + path.sep) && requestedPath !== rootDir) {
                res.writeHead(403);
                res.end('Forbidden');
                return;
            }

            fs.readFile(requestedPath, (error, content) => {
                if (error) {
                    res.writeHead(error.code === 'ENOENT' ? 404 : 500, { 'Content-Type': 'text/plain; charset=utf-8' });
                    res.end(error.message);
                    return;
                }
                res.writeHead(200, { 'Content-Type': getContentType(requestedPath) });
                res.end(content);
            });
        } catch (error) {
            res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
            res.end(error.message);
        }
    });

    return new Promise((resolve, reject) => {
        server.once('error', reject);
        server.listen(0, '127.0.0.1', () => {
            resolve({ server, origin: `http://127.0.0.1:${server.address().port}` });
        });
    });
}

function stopStaticServer(server) {
    return new Promise((resolve) => {
        if (!server || !server.listening) return resolve();
        server.close(() => resolve());
    });
}

async function generateGIF(character) {
    console.log(`🎨 Generating clean transparent Bordeaux Red stroke_order.gif for "${character}"...`);
    const { server, origin } = await startStaticServer(__dirname);
    let browser;
    const tempFrameDir = path.join(CONFIG.tempDir, character);
    if (!fs.existsSync(tempFrameDir)) {
        fs.mkdirSync(tempFrameDir, { recursive: true });
    }

    try {
        browser = await puppeteer.launch({
            headless: 'new',
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        });

        const page = await browser.newPage();
        await page.setViewport({ width: CONFIG.width, height: CONFIG.height });
        await page.goto(`${origin}/index.html?char=${encodeURIComponent(character)}`, {
            waitUntil: 'networkidle0',
            timeout: 30000
        });

        await page.waitForFunction(() => window.animationReady === true, { timeout: 15000 });
        await new Promise(r => setTimeout(r, 400));

        // Start stroke animation
        await page.evaluate(() => window.startStrokeAnimation());

        const frameInterval = 1000 / CONFIG.fps;
        const maxFrames = 150;
        let frameCount = 0;

        for (let i = 0; i < maxFrames; i++) {
            const framePath = path.join(tempFrameDir, `frame${String(frameCount).padStart(4, '0')}.png`);
            await page.screenshot({
                path: framePath,
                omitBackground: true,
                clip: { x: 0, y: 0, width: CONFIG.width, height: CONFIG.height }
            });
            frameCount++;

            if (i >= 30) {
                const isDone = await page.evaluate(() => window.animationComplete === true);
                if (isDone) {
                    for (let h = 0; h < 8; h++) {
                        const hPath = path.join(tempFrameDir, `frame${String(frameCount).padStart(4, '0')}.png`);
                        await page.screenshot({
                            path: hPath,
                            omitBackground: true,
                            clip: { x: 0, y: 0, width: CONFIG.width, height: CONFIG.height }
                        });
                        frameCount++;
                    }
                    break;
                }
            }
            await new Promise(r => setTimeout(r, frameInterval));
        }

        console.log(`📸 Captured ${frameCount} transparent frames for "${character}".`);
        const outputChar = path.join(CONFIG.outputDir, `${character}.gif`);
        const outputStandard = path.join(CONFIG.outputDir, 'stroke_order.gif');

        if (checkFFmpeg()) {
            const ffmpegCmd = `ffmpeg -y -framerate ${CONFIG.fps} -i "${path.join(tempFrameDir, 'frame%04d.png')}" -vf "split[s0][s1];[s0]palettegen=reserve_transparent=1[p];[s1][p]paletteuse=alpha_threshold=128" "${outputChar}"`;
            execSync(ffmpegCmd, { stdio: 'ignore' });
            fs.copyFileSync(outputChar, outputStandard);
            console.log(`✅ Saved transparent GIF to: ${outputStandard}`);
        } else {
            throw new Error('FFmpeg is required to compile transparent GIF');
        }

        return outputStandard;
    } finally {
        if (browser) await browser.close();
        await stopStaticServer(server);
        try {
            fs.rmSync(tempFrameDir, { recursive: true, force: true });
        } catch {}
    }
}

async function main() {
    const character = process.argv[2] || CONFIG.character;
    try {
        const out = await generateGIF(character);
        console.log(`🎉 Completed GIF generation for "${character}": ${out}`);
    } catch (e) {
        console.error(`❌ Error generating GIF for "${character}":`, e);
        process.exit(1);
    }
}

if (require.main === module) {
    main();
}

module.exports = { generateGIF };
