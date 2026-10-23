import puppeteer from 'puppeteer-core';
import path from 'path';
import fs from 'fs';

const targetUrl = process.argv[2];
if (!targetUrl) {
    console.error(JSON.stringify({ error: 'No URL provided' }));
    process.exit(1);
}

const profileDir = path.resolve('.cache/brave_profile');
fs.mkdirSync(profileDir, { recursive: true });
const clearanceFile = path.resolve('.cache/manhuaus_clearance.txt');

async function extract() {
    const browser = await puppeteer.launch({
        executablePath: '/usr/bin/brave-browser',
        userDataDir: profileDir,
        headless: false,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--window-size=1280,1000'
        ],
        ignoreDefaultArgs: ['--enable-automation']
    });

    try {
        const page = await browser.newPage();
        await page.setUserAgent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36');

        await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 45000 }).catch(e => console.error("goto error:", e.message));

        // Handle Cloudflare challenge if present
        for (let i = 0; i < 30; i++) {
            const title = await page.title();
            const isChallenge = title.toLowerCase().includes('just a moment') ||
                                title.toLowerCase().includes('um momento') ||
                                title.toLowerCase().includes('cloudflare') ||
                                title.toLowerCase().includes('attention required');

            if (!isChallenge) break;

            for (const frame of page.frames()) {
                if (frame.url().includes('cloudflare') || frame.url().includes('challenges')) {
                    const checkbox = await frame.$('input[type="checkbox"], #challenge-stage, .ctp-checkbox-label');
                    if (checkbox) {
                        const box = await checkbox.boundingBox();
                        if (box) {
                            await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
                        }
                    }
                }
            }
            await new Promise(r => setTimeout(r, 1000));
        }

        // Wait for reading-content or page break images
        await page.waitForSelector('.reading-content img, .wp-manga-chapter-img', { timeout: 15000 }).catch(() => {});
        await new Promise(r => setTimeout(r, 1500));

        const result = await page.evaluate(() => {
            const imgEls = Array.from(document.querySelectorAll('.reading-content img, .wp-manga-chapter-img'));
            const images = imgEls.map(img => (img.getAttribute('data-src') || img.src || '').trim()).filter(Boolean);
            const nextEl = document.querySelector('a.btn.next_page, a.next_page');
            const prevEl = document.querySelector('a.btn.prev_page, a.prev_page');
            const chapInput = document.querySelector('#wp-manga-current-chap');
            return {
                title: document.title,
                chapVal: chapInput ? chapInput.value : null,
                images: Array.from(new Set(images)),
                nextUrl: nextEl ? nextEl.href : null,
                prevUrl: prevEl ? prevEl.href : null
            };
        });

        // Save cf_clearance cookie
        const cookies = await page.cookies();
        const cf = cookies.find(c => c.name === 'cf_clearance');
        if (cf && cf.value) {
            fs.writeFileSync(clearanceFile, cf.value, 'utf-8');
        }

        let chapterNum = null;
        if (result.chapVal) {
            const m = result.chapVal.match(/(\d+)/);
            if (m) chapterNum = parseInt(m[1], 10);
        }
        if (!chapterNum) {
            const m = targetUrl.match(/chapter-(\d+)/i);
            if (m) chapterNum = parseInt(m[1], 10);
        }

        let nextInfo = null;
        if (result.nextUrl) {
            const m = result.nextUrl.match(/chapter-(\d+)/i);
            nextInfo = {
                url: result.nextUrl,
                number: m ? parseInt(m[1], 10) : (chapterNum ? chapterNum + 1 : null)
            };
        }

        let prevInfo = null;
        if (result.prevUrl) {
            const m = result.prevUrl.match(/chapter-(\d+)/i);
            prevInfo = {
                url: result.prevUrl,
                number: m ? parseInt(m[1], 10) : (chapterNum ? Math.max(1, chapterNum - 1) : null)
            };
        }

        console.log(JSON.stringify({
            status: 'ok',
            images: result.images,
            number: chapterNum,
            next: nextInfo,
            prev: prevInfo,
            clearance: cf ? cf.value : null
        }));

    } catch (err) {
        console.error(JSON.stringify({ error: err.message, images: [] }));
    } finally {
        await browser.close();
    }
}

extract();
