import puppeteer from 'puppeteer-core';
import path from 'path';
import fs from 'fs';

const pageNum = parseInt(process.argv[2] || '1', 10);
const query = (process.argv[3] || '').trim();

let targetUrl = '';
if (query) {
    targetUrl = pageNum <= 1
        ? `https://manhuaus.com/?s=${encodeURIComponent(query)}&post_type=wp-manga`
        : `https://manhuaus.com/page/${pageNum}/?s=${encodeURIComponent(query)}&post_type=wp-manga`;
} else {
    targetUrl = pageNum <= 1 ? 'https://manhuaus.com/manga/' : `https://manhuaus.com/manga/page/${pageNum}/`;
}

const profileDir = path.resolve('.cache/brave_profile');
fs.mkdirSync(profileDir, { recursive: true });
const clearanceFile = path.resolve('.cache/manhuaus_clearance.txt');

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

        const resp = await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 45000 }).catch(e => {
            console.error('goto warning:', e.message);
            return null;
        });

        // Wait / handle Cloudflare challenge if present
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

        // Save cf_clearance cookie if available
        try {
            const cookies = await page.cookies();
            const cf = cookies.find(c => c.name === 'cf_clearance');
            if (cf && cf.value) {
                fs.writeFileSync(clearanceFile, cf.value, 'utf-8');
            }
        } catch (e) {}

        const result = await page.evaluate((currPage, isSearch) => {
            const docTitle = document.title || '';
            const cards = Array.from(document.querySelectorAll('.page-item-detail, .c-tabs-item__content'));
            const items = [];
            const seen = new Set();

            for (const card of cards) {
                const titleLink = card.querySelector('.post-title h3 a, .post-title a, h3 a, a[title]');
                const chLink = card.querySelector('.list-chapter .chapter-item a, .latest-chap .chapter a, .chapter a');

                const title = titleLink ? (titleLink.innerText || titleLink.getAttribute('title') || '').trim() : '';
                const href = titleLink ? titleLink.href : '';
                if (!title || !href) continue;

                const slugMatch = href.match(/\/manga\/([^/]+)/);
                if (!slugMatch) continue;

                const slug = slugMatch[1];
                const cleanSlugHref = `https://manhuaus.com/manga/${slug}/`;
                if (seen.has(cleanSlugHref)) continue;
                seen.add(cleanSlugHref);

                const urlTemplate = `https://manhuaus.com/manga/${slug}/chapter-{chapter}/`;

                let lastChapter = null;
                if (chLink) {
                    const rawText = chLink.innerText || chLink.href || '';
                    const m = rawText.match(/(?:chapter|ch\.?)\s*(\d+)/i) || rawText.match(/(\d+)/);
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
            } else if (!isSearch) {
                // Default browse catalog has 112+ pages
                totalPages = 112;
            }

            const hasLoadMore = !!document.querySelector('#navigation-ajax');
            const hasNextLink = !!document.querySelector('link[rel="next"]');

            if ((hasLoadMore || hasNextLink) && currPage >= totalPages && items.length > 0) {
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
