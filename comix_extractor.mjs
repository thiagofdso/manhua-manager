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

async function extract() {
    const browser = await puppeteer.launch({
        executablePath: '/usr/bin/brave-browser',
        userDataDir: profileDir,
        headless: false,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--window-size=1280,800'
        ],
        ignoreDefaultArgs: ['--enable-automation']
    });

    try {
        const page = await browser.newPage();
        await page.setUserAgent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36');

        let chapterUrl = targetUrl;

        // If targetUrl does not contain chapter ID, try resolving it via the title page
        const chMatch = targetUrl.match(/\/(\d+)-chapter-(\d+)/);
        if (!chMatch) {
            const numMatch = targetUrl.match(/chapter[/-](\d+)/i) || targetUrl.match(/\/(\d+)(?:\/|$)/);
            const targetNum = numMatch ? numMatch[1] : null;
            const slugMatch = targetUrl.match(/\/title\/([^/?#]+)/);
            if (slugMatch) {
                const titleUrl = `https://comix.to/title/${slugMatch[1]}`;
                await page.goto(titleUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
                for (let i = 0; i < 20; i++) {
                    const t = await page.title();
                    if (!t.includes('momento') && !t.includes('Just a moment')) break;
                    await new Promise(r => setTimeout(r, 500));
                }
                await new Promise(r => setTimeout(r, 1500));

                const resolvedUrl = await page.evaluate((targetNum) => {
                    const links = Array.from(document.querySelectorAll('a[href*="-chapter-"]'));
                    if (targetNum) {
                        const exact = links.find(a => a.href.includes(`-chapter-${targetNum}`) || (a.textContent && a.textContent.trim() === `Ch.${targetNum}`));
                        if (exact) return exact.href;
                    }
                    return links.length > 0 ? links[0].href : null;
                }, targetNum);

                if (resolvedUrl) {
                    chapterUrl = resolvedUrl;
                }
            }
        }

        await page.goto(chapterUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });

        // Wait for Turnstile if challenge appears
        for (let i = 0; i < 20; i++) {
            const t = await page.title();
            if (!t.includes('momento') && !t.includes('Just a moment')) break;
            await new Promise(r => setTimeout(r, 500));
        }

        // Wait for TanStack query cache to populate chapter data
        let chapterData = null;
        for (let i = 0; i < 25; i++) {
            chapterData = await page.evaluate(() => {
                const root = document.querySelector('#app') || document.querySelector('#__next') || document.querySelector('body > div');
                for (const k in root) {
                    if (k.startsWith('__reactFiber') || k.startsWith('__reactContainer')) {
                        let queue = [root[k]];
                        while (queue.length > 0) {
                            const cur = queue.shift();
                            if (cur?.memoizedProps?.client?.getQueryCache) {
                                const queries = cur.memoizedProps.client.getQueryCache().getAll();
                                const q = queries.find(q => q.queryKey.some(k => typeof k === 'string' && k.includes('chapters')));
                                if (q?.state?.data) return q.state.data;
                            }
                            if (cur?.child) queue.push(cur.child);
                            if (cur?.sibling) queue.push(cur.sibling);
                        }
                    }
                }
                return null;
            });
            if (chapterData && chapterData.G3 && Array.isArray(chapterData.G3) && chapterData.G3.length > 0) {
                break;
            }
            await new Promise(r => setTimeout(r, 400));
        }

        if (!chapterData || !chapterData.G3) {
            console.error(JSON.stringify({ error: 'Failed to extract chapter data from page' }));
            process.exit(2);
        }

        const result = {
            id: chapterData.hm,
            number: chapterData.LA,
            images: chapterData.G3.map(p => p.zr).filter(Boolean),
            prev: chapterData.Hx ? {
                id: chapterData.Hx.hm,
                number: chapterData.Hx.LA,
                url: 'https://comix.to' + chapterData.Hx.zr
            } : null,
            next: chapterData.IK ? {
                id: chapterData.IK.hm,
                number: chapterData.IK.LA,
                url: 'https://comix.to' + chapterData.IK.zr
            } : null
        };

        console.log(JSON.stringify(result));
    } finally {
        await browser.close();
    }
}

extract().catch(err => {
    console.error(JSON.stringify({ error: err.message }));
    process.exit(1);
});
