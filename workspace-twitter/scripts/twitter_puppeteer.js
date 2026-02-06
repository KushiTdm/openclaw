#!/usr/bin/env node
/**
 * Twitter Puppeteer Poster - Alternative gratuite à l'API
 * Automatise la publication sur X/Twitter via browser automation
 */

const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const path = require('path');

puppeteer.use(StealthPlugin());

const CREDENTIALS_PATH = path.join(process.env.HOME, '.openclaw/credentials/twitter_puppeteer.json');
const COOKIE_PATH = path.join(process.env.HOME, '.openclaw/workspace-twitter/.cookies.json');

class TwitterPuppeteer {
    constructor() {
        this.browser = null;
        this.page = null;
        this.credentials = null;
    }

    async loadCredentials() {
        if (!fs.existsSync(CREDENTIALS_PATH)) {
            throw new Error(`❌ Credentials non trouvés: ${CREDENTIALS_PATH}`);
        }
        this.credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf-8'));
    }

    async init() {
        console.log('🚀 Lancement du navigateur...');
        
        this.browser = await puppeteer.launch({
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--window-size=1920,1080'
            ]
        });

        this.page = await this.browser.newPage();
        
        await this.page.setUserAgent(
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        );

        await this.page.setViewport({ width: 1920, height: 1080 });

        if (fs.existsSync(COOKIE_PATH)) {
            const cookies = JSON.parse(fs.readFileSync(COOKIE_PATH, 'utf-8'));
            await this.page.setCookie(...cookies);
            console.log('🍪 Cookies chargés');
        }
    }

    async login() {
        console.log('🔐 Connexion à Twitter/X...');
        
        await this.page.goto('https://twitter.com/login', {
            waitUntil: 'networkidle2',
            timeout: 30000
        });

        await this.page.waitForSelector('input[autocomplete="username"]', { timeout: 10000 });
        await this.page.type('input[autocomplete="username"]', this.credentials.username, { delay: 100 });
        
        await this.page.evaluate(() => {
            const buttons = Array.from(document.querySelectorAll('div[role="button"]'));
            const nextButton = buttons.find(b => b.textContent.includes('Next'));
            if (nextButton) nextButton.click();
        });
        
        await this.sleep(2000);

        const unusualActivity = await this.page.$('input[data-testid="ocfEnterTextTextInput"]');
        if (unusualActivity) {
            console.log('⚠️  Vérification email/phone demandée');
            if (this.credentials.email) {
                await this.page.type('input[data-testid="ocfEnterTextTextInput"]', this.credentials.email, { delay: 100 });
                await this.page.evaluate(() => {
                    const buttons = Array.from(document.querySelectorAll('div[role="button"]'));
                    const nextButton = buttons.find(b => b.textContent.includes('Next'));
                    if (nextButton) nextButton.click();
                });
                await this.sleep(2000);
            }
        }

        await this.page.waitForSelector('input[name="password"]', { timeout: 10000 });
        await this.page.type('input[name="password"]', this.credentials.password, { delay: 100 });
        
        await this.page.click('div[data-testid="LoginForm_Login_Button"]');
        await this.page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 15000 });

        console.log('✅ Connecté !');

        const cookies = await this.page.cookies();
        fs.writeFileSync(COOKIE_PATH, JSON.stringify(cookies, null, 2));
        console.log('🍪 Cookies sauvegardés');
    }

    async postTweet(text, imagePaths = []) {
        console.log(`📝 Publication: "${text.substring(0, 50)}..."`);

        await this.page.goto('https://twitter.com/home', {
            waitUntil: 'networkidle2'
        });

        await this.sleep(2000);

        const tweetBox = await this.page.waitForSelector('div[data-testid="tweetTextarea_0"]', { timeout: 10000 });
        await tweetBox.click();
        await this.sleep(500);

        await this.page.keyboard.type(text, { delay: 50 });

        if (imagePaths && imagePaths.length > 0) {
            for (const imagePath of imagePaths) {
                if (fs.existsSync(imagePath)) {
                    console.log(`🖼️  Upload: ${imagePath}`);
                    const uploadInput = await this.page.$('input[data-testid="fileInput"]');
                    await uploadInput.uploadFile(imagePath);
                    await this.sleep(3000);
                }
            }
        }

        await this.sleep(1000);
        await this.page.click('div[data-testid="tweetButtonInline"]');
        await this.sleep(4000);

        console.log('✅ Tweet publié !');

        await this.page.goto(`https://twitter.com/${this.credentials.username}`, {
            waitUntil: 'networkidle2'
        });

        await this.sleep(2000);

        const firstTweetLink = await this.page.$('article a[href*="/status/"]');
        if (firstTweetLink) {
            const href = await this.page.evaluate(el => el.href, firstTweetLink);
            return href;
        }

        return null;
    }

    async postThread(tweets) {
        console.log(`🧵 Thread de ${tweets.length} tweets...`);
        
        const tweetUrls = [];
        
        for (let i = 0; i < tweets.length; i++) {
            const tweet = tweets[i];
            console.log(`\n📝 Tweet ${i + 1}/${tweets.length}`);
            
            if (i === 0) {
                const url = await this.postTweet(tweet.text, tweet.images || []);
                tweetUrls.push(url);
            } else {
                await this.page.goto(tweetUrls[0], { waitUntil: 'networkidle2' });
                await this.sleep(2000);
                
                const replyButton = await this.page.$('div[data-testid="reply"]');
                if (replyButton) {
                    await replyButton.click();
                    await this.sleep(2000);
                    
                    const replyBox = await this.page.waitForSelector('div[data-testid="tweetTextarea_0"]', { timeout: 5000 });
                    await replyBox.click();
                    await this.sleep(500);
                    
                    await this.page.keyboard.type(tweet.text, { delay: 50 });
                    
                    if (tweet.images && tweet.images.length > 0) {
                        for (const imagePath of tweet.images) {
                            if (fs.existsSync(imagePath)) {
                                console.log(`🖼️  Upload: ${imagePath}`);
                                const uploadInput = await this.page.$('input[data-testid="fileInput"]');
                                await uploadInput.uploadFile(imagePath);
                                await this.sleep(3000);
                            }
                        }
                    }
                    
                    await this.sleep(1000);
                    await this.page.click('div[data-testid="tweetButton"]');
                    await this.sleep(4000);
                    
                    const newTweetLink = await this.page.$('article:last-of-type a[href*="/status/"]');
                    if (newTweetLink) {
                        const href = await this.page.evaluate(el => el.href, newTweetLink);
                        tweetUrls.push(href);
                    }
                }
            }
            
            if (i < tweets.length - 1) {
                await this.sleep(2000);
            }
        }

        console.log('\n✅ Thread complet !');
        return tweetUrls;
    }

    async close() {
        if (this.browser) {
            await this.browser.close();
            console.log('🔒 Navigateur fermé');
        }
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

async function main() {
    const args = process.argv.slice(2);
    
    if (args.length < 2) {
        console.log('Usage:');
        console.log('  node twitter_puppeteer.js single "Texte" [image1.jpg]');
        console.log('  node twitter_puppeteer.js thread thread.json');
        process.exit(1);
    }

    const type = args[0];
    const poster = new TwitterPuppeteer();

    try {
        await poster.loadCredentials();
        await poster.init();
        await poster.login();

        if (type === 'single') {
            const text = args[1];
            const images = args.slice(2);
            
            const url = await poster.postTweet(text, images);
            console.log(`\n🐦 URL: ${url}`);
            
        } else if (type === 'thread') {
            const threadFile = args[1];
            const threadData = JSON.parse(fs.readFileSync(threadFile, 'utf-8'));
            
            const urls = await poster.postThread(threadData.tweets);
            console.log('\n🐦 URLs:');
            urls.forEach((url, i) => console.log(`  ${i + 1}. ${url}`));
        }

    } catch (error) {
        console.error('❌ Erreur:', error.message);
        console.error(error.stack);
        process.exit(1);
    } finally {
        await poster.close();
    }
}

main();
