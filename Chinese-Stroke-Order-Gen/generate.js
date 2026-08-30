const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const http = require('http');
const { execSync } = require('child_process');

// 配置参数
const CONFIG = {
    character: '中', // 要生成的汉字
    width: 500,
    height: 500,
    fps: 15, // 帧率
    outputDir: './output',
    tempDir: './temp',
    mode: process.env.HANZI_RENDER_MODE || 'transparent'
};

// 确保输出目录存在
if (!fs.existsSync(CONFIG.outputDir)) {
    fs.mkdirSync(CONFIG.outputDir, { recursive: true });
}
if (!fs.existsSync(CONFIG.tempDir)) {
    fs.mkdirSync(CONFIG.tempDir, { recursive: true });
}

// 检查FFmpeg是否可用
function checkFFmpeg() {
    try {
        execSync('ffmpeg -version', { stdio: 'ignore' });
        return true;
    } catch {
        return false;
    }
}

function getContentType(filePath) {
    const extension = path.extname(filePath).toLowerCase();
    if (extension === '.html') return 'text/html; charset=utf-8';
    if (extension === '.js') return 'application/javascript; charset=utf-8';
    if (extension === '.json') return 'application/json; charset=utf-8';
    if (extension === '.css') return 'text/css; charset=utf-8';
    if (extension === '.svg') return 'image/svg+xml';
    if (extension === '.png') return 'image/png';
    if (extension === '.gif') return 'image/gif';
    return 'application/octet-stream';
}

function getBrowserExecutablePath() {
    const candidates = [
        process.env.PUPPETEER_EXECUTABLE_PATH,
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Chromium.app/Contents/MacOS/Chromium'
    ].filter(Boolean);

    for (const candidate of candidates) {
        if (fs.existsSync(candidate)) {
            return candidate;
        }
    }

    return null;
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
                    const statusCode = error.code === 'ENOENT' ? 404 : 500;
                    res.writeHead(statusCode, { 'Content-Type': 'text/plain; charset=utf-8' });
                    res.end(statusCode === 404 ? 'Not Found' : error.message);
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
            const { port } = server.address();
            resolve({
                server,
                origin: `http://127.0.0.1:${port}`
            });
        });
    });
}

function stopStaticServer(server) {
    return new Promise((resolve, reject) => {
        if (!server || !server.listening) {
            resolve();
            return;
        }

        server.close(error => {
            if (error) {
                reject(error);
                return;
            }
            resolve();
        });
    });
}

async function generateGIF(character) {
    console.log(`开始生成汉字 "${character}" 的笔顺动画GIF...`);

    const { server, origin } = await startStaticServer(__dirname);
    let browser;

    const tempFrameDir = path.join(CONFIG.tempDir, character);
    if (!fs.existsSync(tempFrameDir)) {
        fs.mkdirSync(tempFrameDir, { recursive: true });
    }

    try {
        const executablePath = getBrowserExecutablePath();
        if (executablePath) {
            console.log(`使用浏览器: ${executablePath}`);
        }

        browser = await puppeteer.launch({
            headless: 'new',
            executablePath: executablePath || undefined,
            args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        });

        browser.on('disconnected', () => {
            console.error('浏览器连接已断开');
        });

        const page = await browser.newPage();
        page.on('pageerror', error => {
            console.error('页面脚本错误:', error.message);
        });
        page.on('error', error => {
            console.error('页面错误:', error.message);
        });
        page.on('requestfailed', request => {
            const failure = request.failure();
            console.error(`资源加载失败: ${request.url()} - ${failure ? failure.errorText : 'unknown error'}`);
        });

        await page.setViewport({
            width: CONFIG.width,
            height: CONFIG.height,
            deviceScaleFactor: 2
        });

        // 加载HTML页面
        await page.goto(`${origin}/index.html?char=${encodeURIComponent(character)}&mode=${encodeURIComponent(CONFIG.mode)}`, {
            waitUntil: 'networkidle0',
            timeout: 30000
        });

        // 等待Hanzi Writer加载
        await page.waitForFunction(() => window.animationReady === true, { timeout: 15000 });

        const loadError = await page.evaluate(() => window.loadError || null);
        if (loadError) {
            throw new Error(loadError);
        }

        const strokeCount = await page.evaluate(() => {
            if (!window.writer || !window.writer._character) return 0;
            return window.writer._character.strokes.length;
        });

        if (strokeCount === 0) {
            throw new Error(`未能获取汉字 "${character}" 的笔画数据`);
        }

        console.log(`汉字 "${character}" 共有 ${strokeCount} 个笔画，开始逐帧渲染...`);

        const framesPerStroke = 10;
        const pauseFrames = 3;
        const holdFrames = 12;
        let frameIndex = 0;

        for (let s = 0; s < strokeCount; s++) {
            for (let f = 1; f <= framesPerStroke; f++) {
                const progress = f / framesPerStroke;
                const easedProgress = -Math.cos(progress * Math.PI) / 2 + 0.5;

                await page.evaluate((strokeIdx, portion) => {
                    window.renderProgress(strokeIdx, portion);
                }, s, easedProgress);

                const framePath = path.join(tempFrameDir, `frame${String(frameIndex).padStart(4, '0')}.png`);
                await page.screenshot({
                    path: framePath,
                    omitBackground: CONFIG.mode === 'transparent',
                    clip: {
                        x: 0,
                        y: 0,
                        width: CONFIG.width,
                        height: CONFIG.height
                    }
                });
                frameIndex++;
            }

            if (s < strokeCount - 1) {
                for (let p = 0; p < pauseFrames; p++) {
                    const framePath = path.join(tempFrameDir, `frame${String(frameIndex).padStart(4, '0')}.png`);
                    await page.screenshot({
                        path: framePath,
                        omitBackground: CONFIG.mode === 'transparent',
                        clip: {
                            x: 0,
                            y: 0,
                            width: CONFIG.width,
                            height: CONFIG.height
                        }
                    });
                    frameIndex++;
                }
            }
        }

        // 最后一笔完成后，全字保持展示若干帧
        await page.evaluate((strokeIdx) => {
            window.renderProgress(strokeIdx, 1.0);
        }, strokeCount - 1);

        for (let h = 0; h < holdFrames; h++) {
            const framePath = path.join(tempFrameDir, `frame${String(frameIndex).padStart(4, '0')}.png`);
            await page.screenshot({
                path: framePath,
                omitBackground: CONFIG.mode === 'transparent',
                clip: {
                    x: 0,
                    y: 0,
                    width: CONFIG.width,
                    height: CONFIG.height
                }
            });
            frameIndex++;
        }

        console.log(`已成功录制 ${frameIndex} 帧动画，开始生成高清GIF...`);

        const outputName = CONFIG.mode === 'transparent' ? `${character}-transparent.gif` : `${character}.gif`;
        const outputPath = path.join(CONFIG.outputDir, outputName);
        const altOutputPath = path.join(CONFIG.outputDir, `${character}.gif`);

        // 使用FFmpeg生成GIF
        if (checkFFmpeg()) {
            console.log('使用FFmpeg生成GIF...');
            const outputWidth = CONFIG.width;
            const outputHeight = CONFIG.height;
            const vf = CONFIG.mode === 'transparent'
                ? `scale=${outputWidth}:${outputHeight}:flags=lanczos,split[s0][s1];[s0]palettegen=reserve_transparent=1[p];[s1][p]paletteuse=alpha_threshold=128`
                : `scale=${outputWidth}:${outputHeight}:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse`;
            const ffmpegCmd = `ffmpeg -y -framerate 20 -i "${path.join(tempFrameDir, 'frame%04d.png')}" -vf "${vf}" "${outputPath}"`;
            execSync(ffmpegCmd, { stdio: 'inherit' });
            if (outputPath !== altOutputPath) {
                fs.copyFileSync(outputPath, altOutputPath);
            }
            console.log(`✓ GIF生成完成: ${outputPath}`);
        } else {
            throw new Error('需要FFmpeg来生成GIF');
        }

        // 清理临时文件
        const files = fs.readdirSync(tempFrameDir);
        for (const file of files) {
            fs.unlinkSync(path.join(tempFrameDir, file));
        }
        fs.rmdirSync(tempFrameDir);

        return outputPath;
        
    } catch (error) {
        console.error('生成GIF时出错:', error);
        throw error;
    } finally {
        if (browser) {
            await browser.close();
        }
        await stopStaticServer(server);
    }
}

// 从JSON文件读取汉字列表
function getCharactersFromJSON(jsonPath) {
    try {
        const jsonData = fs.readFileSync(jsonPath, 'utf-8');
        const data = JSON.parse(jsonData);

        // 支持简化格式: ["中","文"]
        if (Array.isArray(data)) {
            const characters = data
                .filter(item => typeof item === 'string' && item.trim())
                .map(item => item.trim());
            return [...new Set(characters)];
        }

        // 兼容旧格式: { data: { records: [ { word: "中" } ] } }
        const words = [];
        if (data.data && data.data.records) {
            data.data.records.forEach(record => {
                if (record.word) {
                    words.push(record.word);
                }
            });
        }

        return [...new Set(words)];
    } catch (error) {
        console.error('读取JSON文件失败:', error);
        throw error;
    }
}

// 并发控制函数
async function runWithConcurrencyLimit(tasks, concurrency = 3) {
    const results = [];
    const errors = [];
    const skipped = [];
    let index = 0;
    
    const runTask = async (character, taskIndex) => {
        // 检查文件是否已存在
        const outputName = CONFIG.mode === 'transparent' ? `${character}-transparent.gif` : `${character}.gif`;
        const outputPath = path.join(CONFIG.outputDir, outputName);
        if (fs.existsSync(outputPath)) {
            skipped.push({ character, path: outputPath });
            console.log(`⊘ [${taskIndex + 1}/${tasks.length}] 跳过 "${character}" (文件已存在): ${outputPath}`);
            return;
        }
        
        try {
            console.log(`\n[${taskIndex + 1}/${tasks.length}] 开始生成汉字 "${character}" 的GIF...`);
            const generatedPath = await generateGIF(character);
            results.push({ character, path: generatedPath, success: true });
            console.log(`✓ [${taskIndex + 1}/${tasks.length}] 成功！GIF文件已保存到: ${generatedPath}`);
        } catch (error) {
            console.error(`✗ [${taskIndex + 1}/${tasks.length}] 生成失败: ${error.message}`);
            errors.push({ character, error: error.message });
        }
    };
    
    // 创建并发池
    const workers = [];
    for (let i = 0; i < concurrency; i++) {
        workers.push((async () => {
            while (index < tasks.length) {
                const currentIndex = index++;
                if (currentIndex < tasks.length) {
                    await runTask(tasks[currentIndex], currentIndex);
                }
            }
        })());
    }
    
    // 等待所有工作线程完成
    await Promise.all(workers);
    
    return { results, errors, skipped };
}

// 主函数
async function main() {
    // 检查是否提供了JSON文件路径
    const jsonPath = process.argv[2];
    let characters = [];
    let concurrency = 3; // 默认并发数
    
    // 检查是否有并发数参数
    if (process.argv[3] && !isNaN(parseInt(process.argv[3]))) {
        concurrency = parseInt(process.argv[3]);
    }
    
    if (jsonPath && jsonPath.endsWith('.json')) {
        // 从JSON文件读取汉字列表
        console.log(`从文件读取汉字列表: ${jsonPath}`);
        characters = getCharactersFromJSON(jsonPath);
        console.log(`找到 ${characters.length} 个汉字: ${characters.join(', ')}`);
        console.log(`并发数: ${concurrency}`);
    } else {
        // 单个汉字模式
        const character = process.argv[2] || CONFIG.character;
        characters = [character];
    }
    
    if (characters.length === 0) {
        console.error('没有找到要生成的汉字');
        process.exit(1);
    }
    
    // 并行生成每个汉字的GIF
    const startTime = Date.now();
    const { results, errors, skipped } = await runWithConcurrencyLimit(characters, concurrency);
    const endTime = Date.now();
    const duration = ((endTime - startTime) / 1000 / 60).toFixed(2);
    
    // 输出总结
    console.log(`\n========== 生成完成 ==========`);
    console.log(`总耗时: ${duration} 分钟`);
    console.log(`成功: ${results.length} 个`);
    console.log(`跳过: ${skipped.length} 个 (文件已存在)`);
    console.log(`失败: ${errors.length} 个`);
    
    if (errors.length > 0) {
        console.log(`\n失败的汉字:`);
        errors.forEach(({ character, error }) => {
            console.log(`  - ${character}: ${error}`);
        });
    }
}

// 运行
if (require.main === module) {
    main();
}

module.exports = { generateGIF };

