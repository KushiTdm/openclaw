#!/usr/bin/env python3
"""
Thread Splitter - Découpe intelligent de threads
Respecte la limite de 280 caractères par tweet
"""

import json
import sys
import argparse
from pathlib import Path

MAX_TWEET_LENGTH = 280

class ThreadSplitter:
    def __init__(self):
        pass
    
    def split_by_paragraphs(self, full_text):
        """
        Découpe par paragraphes (séparés par \n\n)
        """
        paragraphs = full_text.strip().split('\n\n')
        tweets = []
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Si le paragraphe tient dans un tweet
            if len(para) <= MAX_TWEET_LENGTH:
                tweets.append({"text": para, "images": []})
            else:
                # Découper en phrases
                sentences = para.split('. ')
                current_tweet = ""
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence.endswith('.'):
                        sentence += '.'
                    
                    if len(current_tweet) + len(sentence) + 1 <= MAX_TWEET_LENGTH:
                        current_tweet += sentence + " "
                    else:
                        if current_tweet:
                            tweets.append({"text": current_tweet.strip(), "images": []})
                        current_tweet = sentence + " "
                
                if current_tweet:
                    tweets.append({"text": current_tweet.strip(), "images": []})
        
        return tweets
    
    def add_thread_indicators(self, tweets):
        """Ajoute les indicateurs 1/N, 2/N, etc."""
        total = len(tweets)
        
        for i, tweet in enumerate(tweets, 1):
            # Ajouter uniquement si ça tient
            indicator = f"{i}/{total}"
            
            # Vérifier si on peut ajouter l'indicateur
            if len(tweet['text']) + len(indicator) + 1 <= MAX_TWEET_LENGTH:
                # Ajouter au début du tweet
                tweet['text'] = f"{indicator} {tweet['text']}"
        
        return tweets
    
    def split_thread(self, full_text, add_indicators=True):
        """Point d'entrée principal"""
        tweets = self.split_by_paragraphs(full_text)
        
        if add_indicators and len(tweets) > 1:
            tweets = self.add_thread_indicators(tweets)
        
        return tweets


def main():
    parser = argparse.ArgumentParser(description='Thread Splitter')
    parser.add_argument('--input', required=True, help='Texte complet du thread')
    parser.add_argument('--output', help='Fichier JSON de sortie')
    parser.add_argument('--no-indicators', action='store_true', help='Ne pas ajouter 1/N')
    
    args = parser.parse_args()
    
    splitter = ThreadSplitter()
    tweets = splitter.split_thread(args.input, not args.no_indicators)
    
    result = {"tweets": tweets}
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ Thread sauvegardé: {args.output}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print(f"\n📊 Thread : {len(tweets)} tweets")
    for i, tweet in enumerate(tweets, 1):
        print(f"  Tweet {i}: {len(tweet['text'])} caractères")


if __name__ == "__main__":
    main()
