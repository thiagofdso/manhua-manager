import puppeteer from 'puppeteer-core';
import path from 'path';
import fs from 'fs';

const pageNum = parseInt(process.argv[2] || '1', 10);
const query = (process.argv[3] || '').trim();

let targetUrl = '';
if (query) {
    targetUrl = pageNum <= 1 
        ? `https://comix.to/browse?q=${encodeURIComponent(query)}&sort=relevance:desc`
        : `https://comix.to/browse?q=${encodeURIComponent(query)}&sort=relevance:desc&page=${pageNum}`;
} else {
    targetUrl = pageNum <= 1 ? 'https://comix.to/' : `https://comix.to/?page=${pageNum}`;
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
            '--window-size=1280,800'
        ],
        ignoreDefaultArgs: ['--enable-automation']
    });

    try {
        const page = await browser.newPage();
        await page.setUserAgent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36');
        
        await page.goto(targetUrl, { waitUntil: 'networkidle2', timeout: 35000 });
        
        // Wait up to 5s if Turnstile or challenge title appears
        for (let i = 0; i < 10; i++) {
            const title = await page.title();
            if (!title.includes('Just a moment') && !title.includes('momento')) break;
            await new Promise(r => setTimeout(r, 500));
        }

        const result = await page.evaluate((pageNum, isSearch) => {
            const items = [];
            const seen = new Set();

            if (!isSearch) {
                // Section "Latest Updates"
                const sections = Array.from(document.querySelectorAll('section'));
                const latestSec = sections.find(s => s.textContent && s.textContent.includes('Latest Updates'));
                if (!latestSec) {
                    return { status: 'ok', page: pageNum, totalPages: 1, items: [] };
                }

                const cards = Array.from(latestSec.querySelectorAll('.grid-updates a.card'));
                for (const card of cards) {
                    const href = card.getAttribute('href') || '';
                    const titleEl = card.querySelector('.card__title');
                    const chEl = card.querySelector('.card__ch');

                    const title = titleEl ? (titleEl.getAttribute('title') || titleEl.innerText || '').trim() : '';
                    if (!title || !href) continue;

                    const cleanHref = href.startsWith('http') ? href : `https://comix.to${href}`;
                    if (seen.has(cleanHref)) continue;
                    seen.add(cleanHref);

                    const urlTemplate = cleanHref.replace(/\/+$/, '') + '/{chapter}';

                    let lastChapter = null;
                    if (chEl) {
                        const match = (chEl.innerText || '').match(/(\d+)/);
                        if (match) lastChapter = parseInt(match[1], 10);
                    }

                    items.push({
                        title: title,
                        urlTemplate: urlTemplate,
                        lastChapter: lastChapter
                    });
                }
            } else {
                // Search list (.lrow or a.card)
                const rows = Array.from(document.querySelectorAll('.lrow, .grid-updates a.card'));
                for (const row of rows) {
                    const titleLink = row.querySelector('.lrow__title-link, a.card') || row.querySelector('a[href*="/title/"]');
                    const titleEl = row.querySelector('.lrow__title, .card__title');
                    const href = titleLink ? titleLink.getAttribute('href') : (row.getAttribute('href') || '');
                    const title = titleEl ? (titleEl.getAttribute('title') || titleEl.innerText || '').trim() : (row.getAttribute('aria-label') || '').trim();

                    if (!title || !href) continue;

                    const cleanHref = href.startsWith('http') ? href : `https://comix.to${href}`;
                    if (seen.has(cleanHref)) continue;
                    seen.add(cleanHref);

                    const urlTemplate = cleanHref.replace(/\/+$/, '') + '/{chapter}';

                    let lastChapter = null;
                    const text = row.innerText || '';
                    const chMatch = text.match(/(?:CH\.|Ch\.)\s*(\d+)/i) || text.match(/(\d+)/);
                    if (chMatch) {
                        lastChapter = parseInt(chMatch[1], 10);
                    }

                    items.push({
                        title: title,
                        urlTemplate: urlTemplate,
                        lastChapter: lastChapter
                    });
                }
            }

            // Estimate totalPages
            let totalPages = 24;
            const pagerBtns = Array.from(document.querySelectorAll('.npager__num, .pagination a, .pagination button'));
            const pagerNums = pagerBtns.map(b => parseInt(b.innerText.trim(), 10)).filter(n => !isNaN(n));
            if (pagerNums.length > 0) {
                totalPages = Math.max(...pagerNums);
            } else {
                const initEl = document.getElementById('initial-data');
                if (initEl) {
                    try {
                        const initData = JSON.parse(initEl.textContent);
                        for (const k of Object.keys(initData.queries || {})) {
                            if (k.includes('chapter_updated_at')) {
                                const meta = initData.queries[k].meta;
                                if (meta && meta.lastPage) {
                                    totalPages = meta.lastPage;
                                }
                            }
                        }
                    } catch (e) {}
                }
            }

            // If on page 24 or more and items exist, allow advancing
            if (pageNum >= totalPages && items.length > 0) {
                totalPages = pageNum + 1;
            } else if (items.length === 0) {
                totalPages = Math.max(1, pageNum - 1);
            }

            return {
                status: 'ok',
                page: pageNum,
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
