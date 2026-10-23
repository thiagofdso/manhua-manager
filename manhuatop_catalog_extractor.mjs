import puppeteer from 'puppeteer-core';
import path from 'path';
import fs from 'fs';

const pageNum = parseInt(process.argv[2] || '1', 10);
const query = (process.argv[3] || '').trim();

let targetUrl = '';
if (query) {
    targetUrl = pageNum <= 1
        ? `https://manhuatop.org/?s=${encodeURIComponent(query)}&post_type=wp-manga`
        : `https://manhuatop.org/page/${pageNum}/?s=${encodeURIComponent(query)}&post_type=wp-manga`;
} else {
    targetUrl = pageNum <= 1
        ? 'https://manhuatop.org/manhua-genre/manhua/?m_orderby=alphabet'
        : `https://manhuatop.org/manhua-genre/manhua/page/${pageNum}/?m_orderby=alphabet`;
}

const profileDir = path.resolve('.cache/brave_profile');
fs.mkdirSync(profileDir, { recursive: true });

async function extract() {
    const browser = await puppeteer.launch({
        executablePath: '/usr/bin/brave-browser',
        userDataDir: profileDir,
        headless: true,
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

        await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 45000 }).catch(e => {
            console.error('goto warning:', e.message);
            return null;
        });

        // Handle Cloudflare Turnstile if present
        for (let i = 0; i < 20; i++) {
            const title = (await page.title()).toLowerCase();
            const isChallenge = title.includes('just a moment') ||
                                title.includes('um momento') ||
                                title.includes('cloudflare') ||
                                title.includes('attention required');

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

        await new Promise(r => setTimeout(r, 1500));

        const result = await page.evaluate((currPage, isSearch) => {
            const docTitle = document.title || '';
            const cards = Array.from(document.querySelectorAll('.page-item-detail, .c-tabs-item__content, .comic_post__inner'));
            const items = [];
            const seen = new Set();

            for (const card of cards) {
                const titleLink = card.querySelector('.comic_post__title a, .post-title a, h3 a, a[title]');
                const chEl = card.querySelector('.chapter-item, .chapter, .font-meta.chapter a, .chapter_text');

                const title = titleLink ? (titleLink.innerText || titleLink.getAttribute('title') || '').trim() : '';
                const href = titleLink ? titleLink.href : '';
                if (!title || !href) continue;

                const slugMatch = href.match(/\/manhua\/([^/]+)/);
                if (!slugMatch) continue;

                const slug = slugMatch[1];
                const cleanSlugHref = `https://manhuatop.org/manhua/${slug}/`;
                if (seen.has(cleanSlugHref)) continue;
                seen.add(cleanSlugHref);

                const urlTemplate = `https://manhuatop.org/manhua/${slug}/chapter-{chapter}/`;

                let lastChapter = null;
                if (chEl) {
                    const rawText = chEl.innerText || chEl.textContent || chEl.getAttribute('href') || '';
                    const m = rawText.match(/(?:chapter|ch\.?)\s*(\d+)/i) || rawText.match(/chapter-(\d+)/i) || rawText.match(/(\d+)/);
                    if (m) {
                        lastChapter = parseInt(m[1], 10);
                    }
                }

                items.push({
                    title: title,
                    urlTemplate: urlTemplate,
                    lastChapter: lastChapter
                });
            }

            // Estimate total pages
            let totalPages = 1;
            const titleMatch = docTitle.match(/Page\s+\d+\s+of\s+(\d+)/i);
            if (titleMatch) {
                totalPages = parseInt(titleMatch[1], 10);
            } else {
                const pageLinks = Array.from(document.querySelectorAll('.wp-pagenavi a, .wp-pagenavi span, .pagination a, .pagination span'));
                const nums = [];
                for (const el of pageLinks) {
                    const h = el.getAttribute('href') || '';
                    const t = el.innerText || '';
                    const mH = h.match(/page\/(\d+)/) || h.match(/page=(\d+)/);
                    if (mH) nums.push(parseInt(mH[1], 10));
                    const mT = t.match(/^\d+$/);
                    if (mT) nums.push(parseInt(mT[0], 10));
                }
                if (nums.length > 0) {
                    totalPages = Math.max(...nums);
                } else if (!isSearch) {
                    totalPages = 113;
                }
            }

            const hasNext = !!document.querySelector('.wp-pagenavi .nextpostslink, link[rel="next"], .pagination .next');
            if (hasNext && currPage >= totalPages && items.length > 0) {
                totalPages = currPage + 1;
            } else if (items.length === 0) {
                totalPages = Math.max(1, currPage - 1);
            }

            return {
                status: 'ok',
                page: currPage,
                totalPages: totalPages,
                items: items
            };
        }, pageNum, !!query);

        console.log(JSON.stringify(result));
    } catch (err) {
        console.error(JSON.stringify({ status: 'error', error: err.message, items: [] }));
        process.exit(1);
    } finally {
        await browser.close();
    }
}

extract();
