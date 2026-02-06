#!/usr/bin/env python3
"""
Twitter Poster - Wrapper Python pour Puppeteer
Vérifie la longueur, découpe en thread si nécessaire
"""

import subprocess
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

PUPPETEER_SCRIPT = Path.home() / ".openclaw/workspace-twitter/scripts/twitter_puppeteer.js"
THREAD_SPLITTER = Path.home() / ".openclaw/workspace-twitter/scripts/thread_splitter.py"
LOG_PATH = Path.home() / ".openclaw/workspace-twitter/memory"

MAX_TWEET_LENGTH = 280  # Limite Twitter/X

class TwitterPoster:
    def __init__(self):
        self.puppeteer_script = PUPPETEER_SCRIPT
        self.thread_splitter = THREAD_SPLITTER
    
    def check_length(self, text):
        """Vérifie longueur tweet"""
        length = len(text)
        if length > MAX_TWEET_LENGTH:
            return False, length
        return True, length
    
    def auto_split_thread(self, text):
        """Découpe automatiquement en thread si trop long"""
        print(f"📏 Texte trop long ({len(text)} > {MAX_TWEET_LENGTH})")
        print("🔪 Découpage automatique en thread...")
        
        # Appeler thread_splitter.py
        result = subprocess.run(
            ['python3', str(self.thread_splitter), '--input', text],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Erreur découpage: {result.stderr}")
        
        # Parser le JSON retourné
        thread_data = json.loads(result.stdout)
        return thread_data['tweets']
    
    def post_single_tweet(self, text, image_paths=None, auto_thread=True):
        """Publie un tweet simple via Puppeteer"""
        
        # Vérifier longueur
        is_valid, length = self.check_length(text)
        
        if not is_valid:
            if auto_thread:
                # Découper automatiquement en thread
                tweets = self.auto_split_thread(text)
                print(f"✂️  Converti en thread de {len(tweets)} tweets")
                return self.post_thread(tweets)
            else:
                raise ValueError(
                    f"❌ Tweet trop long: {length} caractères (max {MAX_TWEET_LENGTH})\n"
                    f"💡 Conseil: Raccourcir le texte ou utiliser --auto-thread"
                )
        
        # Publier via Puppeteer
        cmd = ['node', str(self.puppeteer_script), 'single', text]
        
        if image_paths:
            for img in image_paths:
                if Path(img).exists():
                    cmd.append(img)
        
        print(f"🚀 Publication du tweet...")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"❌ Erreur Puppeteer:\n{result.stderr}")
            return None
        
        output = result.stdout
        print(output)
        
        # Extraire l'URL
        url = None
        for line in output.split('\n'):
            if 'twitter.com' in line or 'x.com' in line:
                parts = line.strip().split()
                for part in parts:
                    if 'twitter.com' in part or 'x.com' in part:
                        url = part
                        break
        
        if url:
            self.log_publication('single', url, text)
            print(f"\n✅ Tweet publié: {url}")
        
        return url
    
    def post_thread(self, tweets_data):
        """Publie un thread via Puppeteer"""
        
        # Vérifier longueur de chaque tweet
        for i, tweet in enumerate(tweets_data):
            text = tweet['text'] if isinstance(tweet, dict) else tweet
            is_valid, length = self.check_length(text)
            if not is_valid:
                raise ValueError(
                    f"❌ Tweet {i+1} du thread trop long: {length} caractères (max {MAX_TWEET_LENGTH})"
                )
        
        # Normaliser le format
        normalized_tweets = []
        for tweet in tweets_data:
            if isinstance(tweet, dict):
                normalized_tweets.append(tweet)
            else:
                normalized_tweets.append({'text': tweet, 'images': []})
        
        # Créer fichier temporaire
        thread_file = '/tmp/twitter_thread.json'
        with open(thread_file, 'w', encoding='utf-8') as f:
            json.dump({'tweets': normalized_tweets}, f, ensure_ascii=False, indent=2)
        
        # Publier via Puppeteer
        cmd = ['node', str(self.puppeteer_script), 'thread', thread_file]
        
        print(f"🚀 Publication du thread ({len(normalized_tweets)} tweets)...")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180
        )
        
        if result.returncode != 0:
            print(f"❌ Erreur Puppeteer:\n{result.stderr}")
            return []
        
        output = result.stdout
        print(output)
        
        # Extraire les URLs
        urls = []
        for line in output.split('\n'):
            if ('twitter.com/status/' in line or 'x.com/status/' in line) and 'http' in line:
                parts = line.strip().split()
                for part in parts:
                    if 'twitter.com' in part or 'x.com' in part:
                        if part not in urls:
                            urls.append(part)
        
        if urls:
            self.log_publication('thread', urls, normalized_tweets)
            print(f"\n✅ Thread publié ({len(urls)} tweets)")
            for i, url in enumerate(urls, 1):
                print(f"  {i}. {url}")
        
        return urls
    
    def log_publication(self, pub_type, urls, content):
        """Log la publication"""
        log_file = LOG_PATH / f"{datetime.now().strftime('%Y-%m-%d')}.md"
        LOG_PATH.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%H:%M")
        
        with open(log_file, 'a', encoding='utf-8') as f:
            if pub_type == 'single':
                f.write(f"\n### {timestamp} - Tweet Simple (Puppeteer)\n")
                f.write(f"- URL: {urls}\n")
                f.write(f"- Texte: {content[:100]}...\n")
                f.write(f"- Longueur: {len(content)} caractères\n")
            
            elif pub_type == 'thread':
                f.write(f"\n### {timestamp} - Thread (Puppeteer) ({len(urls)} tweets)\n")
                for i, url in enumerate(urls, 1):
                    f.write(f"- Tweet {i}: {url}\n")
                if content:
                    first_text = content[0]['text'] if isinstance(content[0], dict) else str(content[0])
                    f.write(f"- Premier tweet: {first_text[:60]}...\n")


def main():
    parser = argparse.ArgumentParser(description='Twitter Poster (Puppeteer)')
    parser.add_argument('--type', choices=['single', 'thread'], required=True)
    parser.add_argument('--text', help='Texte du tweet (pour single)')
    parser.add_argument('--images', nargs='*', help='Chemins des images')
    parser.add_argument('--file', help='Fichier JSON config (pour thread)')
    parser.add_argument('--no-auto-thread', action='store_true', 
                       help='Désactiver découpage automatique si trop long')
    
    args = parser.parse_args()
    
    poster = TwitterPoster()
    
    try:
        if args.type == 'single':
            if not args.text:
                print("❌ --text requis pour single tweet")
                sys.exit(1)
            
            poster.post_single_tweet(
                args.text, 
                args.images, 
                auto_thread=not args.no_auto_thread
            )
        
        elif args.type == 'thread':
            if not args.file:
                print("❌ --file requis pour thread")
                sys.exit(1)
            
            with open(args.file, 'r', encoding='utf-8') as f:
                thread_data = json.load(f)
            
            tweets = thread_data.get('tweets', [])
            poster.post_thread(tweets)
    
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
