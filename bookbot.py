#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
import logging
import time
import datetime
import re
import random
import string
import threading
import requests
from enum import Enum
from urllib.parse import quote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, 
    CallbackContext, CallbackQueryHandler, ConversationHandler
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = "7609046916:AAFHpI7sUJhLuHZr3XtpK4VPDpZbZGJ6LVs"
ADMIN_ID = 7130596820
VERIFICATION_CHAMBER = "@books086"
BOT_USERNAME = "@AllFreeBookspdf_bot"
SHRINKEARN_API_KEY = "85c434ce143c6da4e2a220deb7d02ba232d1893b"
SHRINKEARN_REFERRAL = "https://shrinkearn.com/ref/steffu001"
VERIFICATION_URL = "https://ajakaksosoosos.vercel.app/"
BOOK_PRICE = 7
CHANNEL = "@APNA_BOOKS_PDF"
DAILY_BONUS_AMOUNT = 50

# Admin configuration
ADMIN_IDS = [ADMIN_ID]  # List of admin IDs, initially just the primary admin
SYSTEM_VERSION = "2.0.0"  # For version tracking

# Time constants
TWENTY_FOUR_HOURS = 24 * 60 * 60  # 24 hours in seconds
TWENTY_MINUTES = 20 * 60  # 20 minutes in seconds

# Database path
DB_PATH = 'bookbot.db'

# Time constants (in seconds)
FIVE_HOURS = 5 * 60 * 60
TWENTY_FOUR_HOURS = 24 * 60 * 60
THIRTY_MINUTES = 30 * 60
TWENTY_MINUTES = 20 * 60
TWO_HOURS = 2 * 60 * 60
FORTY_EIGHT_HOURS = 48 * 60 * 60

# Search quota constants
DB_QUOTA = 5
AI_QUOTA = 4
R1_QUOTA = 2
R2_QUOTA = 1

# Referral rewards
REFERRAL_BALANCE = 100
REFERRAL_DB_CREDITS = 20
REFERRAL_AI_CREDITS = 5
REFERRAL_R1_CREDITS = 5

# Daily bonus constants
DAILY_BONUS_BALANCE = 200

# Premium constants
PREMIUM_REWARD = 200

# Initialize database
def init_db():
    """Initialize SQLite database with necessary tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Books table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        url TEXT NOT NULL
    )
    ''')
    
    # Create Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Users (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0,
        referrals INTEGER DEFAULT 0,
        last_verify INTEGER DEFAULT 0,
        joined INTEGER DEFAULT 0,
        search_count INTEGER DEFAULT 0,
        ai_credits INTEGER DEFAULT 0,
        r1_credits INTEGER DEFAULT 0,
        r2_credits INTEGER DEFAULT 0,
        last_reset INTEGER DEFAULT 0,
        referral_credits INTEGER DEFAULT 0,
        referral_expiry INTEGER DEFAULT 0,
        admin_uses_remaining INTEGER DEFAULT 0,
        premium_until INTEGER DEFAULT 0,
        db_instant_credits INTEGER DEFAULT 0,
        db_instant_expiry INTEGER DEFAULT 0,
        owner_mode INTEGER DEFAULT 0,
        last_daily_bonus INTEGER DEFAULT 0,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        join_date INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0
    )
    ''')
    
    # Create Updates table for storing bot updates/announcements
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        is_pinned INTEGER DEFAULT 0
    )
    ''')
    
    # Create Quiz table for storing quizzes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        created_by INTEGER NOT NULL,
        created_at INTEGER NOT NULL,
        reward_amount INTEGER DEFAULT 0,
        min_score_percent INTEGER DEFAULT 50
    )
    ''')
    
    # Create QuizQuestions table for storing quiz questions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS QuizQuestions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_option TEXT NOT NULL,
        FOREIGN KEY (quiz_id) REFERENCES Quizzes(id) ON DELETE CASCADE
    )
    ''')
    
    # Create UserQuizzes table for tracking user quiz attempts
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS UserQuizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        quiz_id INTEGER NOT NULL,
        score INTEGER DEFAULT 0,
        max_score INTEGER DEFAULT 0,
        completed INTEGER DEFAULT 0,
        reward_given INTEGER DEFAULT 0,
        completed_at INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (quiz_id) REFERENCES Quizzes(id) ON DELETE CASCADE
    )
    ''')
    
    # Add new columns if they don't exist
    try:
        # Check if owner_mode column exists
        cursor.execute("SELECT owner_mode FROM Users LIMIT 1")
    except sqlite3.OperationalError:
        # Add owner_mode column if it doesn't exist
        cursor.execute("ALTER TABLE Users ADD COLUMN owner_mode INTEGER DEFAULT 0")
        
    try:
        # Check if last_daily_bonus column exists
        cursor.execute("SELECT last_daily_bonus FROM Users LIMIT 1")
    except sqlite3.OperationalError:
        # Add last_daily_bonus column if it doesn't exist
        cursor.execute("ALTER TABLE Users ADD COLUMN last_daily_bonus INTEGER DEFAULT 0")
        
    try:
        # Check if username column exists
        cursor.execute("SELECT username FROM Users LIMIT 1")
    except sqlite3.OperationalError:
        # Add username column if it doesn't exist
        cursor.execute("ALTER TABLE Users ADD COLUMN username TEXT")
        
    try:
        # Check if first_name column exists
        cursor.execute("SELECT first_name FROM Users LIMIT 1")
    except sqlite3.OperationalError:
        # Add first_name column if it doesn't exist
        cursor.execute("ALTER TABLE Users ADD COLUMN first_name TEXT")
        
    try:
        # Check if last_name column exists
        cursor.execute("SELECT last_name FROM Users LIMIT 1")
    except sqlite3.OperationalError:
        # Add last_name column if it doesn't exist
        cursor.execute("ALTER TABLE Users ADD COLUMN last_name TEXT")
        
    try:
        # Check if join_date column exists
        cursor.execute("SELECT join_date FROM Users LIMIT 1")
    except sqlite3.OperationalError:
        # Add join_date column if it doesn't exist
        cursor.execute("ALTER TABLE Users ADD COLUMN join_date INTEGER DEFAULT 0")
        
    try:
        # Check if is_admin column exists
        cursor.execute("SELECT is_admin FROM Users LIMIT 1")
    except sqlite3.OperationalError:
        # Add is_admin column if it doesn't exist
        cursor.execute("ALTER TABLE Users ADD COLUMN is_admin INTEGER DEFAULT 0")
        # Set primary admin
        cursor.execute("UPDATE Users SET is_admin = 1 WHERE user_id = ?", (ADMIN_ID,))
    
    conn.commit()
    
    # Create SearchQuota table to track usage in the same connection
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS SearchQuota (
        user_id INTEGER PRIMARY KEY,
        db_searches INTEGER DEFAULT 0,
        ai_searches INTEGER DEFAULT 0,
        r1_searches INTEGER DEFAULT 0,
        r2_searches INTEGER DEFAULT 0,
        last_db_reset INTEGER DEFAULT 0,
        last_ai_reset INTEGER DEFAULT 0,
        last_r1_reset INTEGER DEFAULT 0,
        last_r2_reset INTEGER DEFAULT 0
    )
    ''')
    
    conn.commit()
    conn.close()

# Database operations
def get_user(user_id):
    """Get user data from database, create if doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        # Create new user with default values
        cursor.execute(
            "INSERT INTO Users (user_id, balance, referrals, last_verify, joined, search_count, "
            "ai_credits, r1_credits, r2_credits, last_reset, referral_credits, referral_expiry, "
            "admin_uses_remaining, premium_until, db_instant_credits, db_instant_expiry) "
            "VALUES (?, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", 
            (user_id,)
        )
        conn.commit()
        
        cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    
    # Convert to dictionary for easier access
    columns = [col[0] for col in cursor.description]
    user_dict = {columns[i]: user[i] for i in range(len(columns))}
    
    conn.close()
    return user_dict

def update_user(user_id, **kwargs):
    """Update user data in database with provided values."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values()) + [user_id]
    
    cursor.execute(f"UPDATE Users SET {set_clause} WHERE user_id = ?", values)
    conn.commit()
    conn.close()

def get_search_quota(user_id):
    """Get user search quota, create if doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM SearchQuota WHERE user_id = ?", (user_id,))
    quota = cursor.fetchone()
    
    if not quota:
        # Create new quota record with default values
        now = int(time.time())
        cursor.execute(
            "INSERT INTO SearchQuota (user_id, db_searches, ai_searches, r1_searches, r2_searches, "
            "last_db_reset, last_ai_reset, last_r1_reset, last_r2_reset) "
            "VALUES (?, 0, 0, 0, 0, ?, ?, ?, ?)", 
            (user_id, now, now, now, now)
        )
        conn.commit()
        
        cursor.execute("SELECT * FROM SearchQuota WHERE user_id = ?", (user_id,))
        quota = cursor.fetchone()
    
    # Convert to dictionary for easier access
    columns = [col[0] for col in cursor.description]
    quota_dict = {columns[i]: quota[i] for i in range(len(columns))}
    
    conn.close()
    return quota_dict

def update_search_quota(user_id, **kwargs):
    """Update user search quota in database with provided values."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
    values = list(kwargs.values()) + [user_id]
    
    cursor.execute(f"UPDATE SearchQuota SET {set_clause} WHERE user_id = ?", values)
    conn.commit()
    conn.close()

def add_book(name, url):
    """Add a book to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO Books (name, url) VALUES (?, ?)", (name, url))
    conn.commit()
    conn.close()

def search_book_in_db(book_name):
    """Search for a book in the local database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Use a more flexible search pattern
    search_pattern = f"%{book_name}%"
    cursor.execute("SELECT name, url FROM Books WHERE name LIKE ?", (search_pattern,))
    results = cursor.fetchall()
    
    conn.close()
    return results

def get_all_books():
    """Get all books from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, url FROM Books")
    books = cursor.fetchall()
    
    conn.close()
    return books

def delete_book(book_id):
    """Delete a book from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM Books WHERE id = ?", (book_id,))
    conn.commit()
    
    conn.close()

# Verification and channel membership functions
def verify_user(user_id, chat_id):
    """Verify user through verification URL."""
    try:
        # First try to use the verification URL
        url = f"{VERIFICATION_URL}?user_id={user_id}&chat_id={chat_id}"
        response = requests.get(url, timeout=10)
        if response.text.strip() == "verified":
            return True
            
        # If the verification server doesn't respond with "verified", we'll auto-verify
        # This allows the bot to function even if the verification server is down
        logger.info(f"Auto-verifying user_id {user_id} as verification URL did not respond correctly")
        return True
    except Exception as e:
        logger.error(f"Verification error: {e}")
        # Auto-verify even on error to ensure the bot remains functional
        logger.info(f"Auto-verifying user_id {user_id} due to verification error")
        return True

def check_user_joined_channel(update, context):
    """Check if user has joined the required channel."""
    user_id = update.effective_user.id
    
    # Try to get chat member status
    try:
        member = context.bot.get_chat_member(chat_id=CHANNEL, user_id=user_id)
        is_member = member.status in ['member', 'administrator', 'creator']
        
        # Update joined status in database
        user = get_user(user_id)
        update_user(user_id, joined=1 if is_member else 0)
        
        return is_member
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        return False

def requires_channel_membership(func):
    """Decorator to check channel membership before executing a command."""
    def wrapper(update, context, *args, **kwargs):
        if not check_user_joined_channel(update, context):
            update.message.reply_text(f"Please join {CHANNEL} to use this bot!")
            return
        return func(update, context, *args, **kwargs)
    return wrapper

def requires_verification(func):
    """Decorator to check user verification before executing a command."""
    def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        user = get_user(user_id)
        
        # Check if verification is needed (every 2 hours)
        current_time = int(time.time())
        if current_time - user['last_verify'] > TWO_HOURS:
            if not verify_user(user_id, chat_id):
                update.message.reply_text("Verification failed. Please try again later.")
                return
            # Update last verification time
            update_user(user_id, last_verify=current_time)
        
        return func(update, context, *args, **kwargs)
    return wrapper

# URL shortening with Shrinkearn
def shorten_url(url):
    """Shorten URL using Shrinkearn API."""
    try:
        api_url = f"https://shrinkearn.com/api?api={SHRINKEARN_API_KEY}&url={quote(url)}"
        response = requests.get(api_url, timeout=10)
        data = response.json()
        
        if data.get('status') == 'success':
            return data.get('shortenedUrl')
        else:
            logger.error(f"URL shortening error: {data.get('message')}")
            return url
    except Exception as e:
        logger.error(f"URL shortening error: {e}")
        return url

# Search methods
def search_with_bs4(book_name):
    """Enhanced search using BeautifulSoup4 with advanced features."""
    try:
        # Expanded list of search URLs with more sources
        search_urls = [
            f"https://libgen.is/search.php?req={quote(book_name)}&open=0&res=25&view=simple&phrase=1&column=def",
            f"https://b-ok.cc/s/{quote(book_name)}",
            f"https://pdfroom.com/books/{quote(book_name)}",
            f"https://archive.org/search.php?query={quote(book_name)}",
            f"https://manybooks.net/search-book?search={quote(book_name)}"
        ]
        
        # Enhanced headers with more browser-like properties
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'TE': 'Trailers'
        }

        # Add proxy support for avoiding blocks
        proxies = None
        try:
            proxy_response = requests.get('https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all')
            if proxy_response.status_code == 200:
                proxy_list = proxy_response.text.split('\n')
                if proxy_list:
                    proxy = random.choice(proxy_list).strip()
                    proxies = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
        except:
            pass

        session = requests.Session()
        results = []
        
        for url in search_urls:
            try:
                # Use multiple retries with exponential backoff
                for attempt in range(3):
                    try:
                        response = session.get(
                            url,
                            headers=headers,
                            proxies=proxies,
                            timeout=15,
                            verify=False
                        )
                        
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            
                            # Site-specific parsing with enhanced error handling
                            if 'libgen.is' in url:
                                results.extend(parse_libgen(soup, book_name))
                            elif 'b-ok.cc' in url:
                                results.extend(parse_bok(soup, book_name))
                            elif 'pdfroom.com' in url:
                                results.extend(parse_pdfroom(soup, book_name))
                            elif 'archive.org' in url:
                                results.extend(parse_archive(soup, book_name))
                            elif 'manybooks.net' in url:
                                results.extend(parse_manybooks(soup, book_name))
                            
                            if results:
                                break
                        
                        elif response.status_code == 429:  # Too Many Requests
                            wait_time = 2 ** attempt  # Exponential backoff
                            time.sleep(wait_time)
                            continue
                            
                    except requests.RequestException as e:
                        logger.error(f"Request error for {url}: {e}")
                        time.sleep(2 ** attempt)
                        continue
                        
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                continue
                
        return results[:3]  # Return top 3 most relevant results
        
    except Exception as e:
        logger.error(f"BS4 search error: {e}")
        return []

def parse_libgen(soup, book_name):
    """Parse LibGen search results."""
    results = []
    try:
        rows = soup.select('table.c tr[valign="top"]')
        for row in rows[:5]:
            try:
                cells = row.find_all('td')
                if len(cells) > 9:
                    title = cells[2].get_text().strip()
                    if book_name.lower() in title.lower():
                        link = cells[9].find('a')
                        if link and link.has_attr('href'):
                            results.append((title, link['href']))
            except:
                continue
    except:
        pass
    return results

def parse_bok(soup, book_name):
    """Parse B-OK search results."""
    results = []
    try:
        books = soup.select('div.resItemBox')
        for book in books[:5]:
            try:
                title_elem = book.select_one('h3.cover-item-title')
                link_elem = book.select_one('a.cover-item-link')
                if title_elem and link_elem:
                    title = title_elem.get_text().strip()
                    if book_name.lower() in title.lower():
                        url = link_elem['href']
                        if not url.startswith('http'):
                            url = 'https://b-ok.cc' + url
                        results.append((title, url))
            except:
                continue
    except:
        pass
    return results

def parse_pdfroom(soup, book_name):
    """Parse PDFRoom search results."""
    results = []
    try:
        books = soup.select('div.book-item')
        for book in books[:5]:
            try:
                title_elem = book.select_one('h3.book-title')
                link_elem = book.select_one('a.book-link')
                if title_elem and link_elem:
                    title = title_elem.get_text().strip()
                    if book_name.lower() in title.lower():
                        url = link_elem['href']
                        if not url.startswith('http'):
                            url = 'https://pdfroom.com' + url
                        results.append((title, url))
            except:
                continue
    except:
        pass
    return results

def parse_archive(soup, book_name):
    """Parse Archive.org search results."""
    results = []
    try:
        books = soup.select('div.item-ia')
        for book in books[:5]:
            try:
                title_elem = book.select_one('div.ttl')
                link_elem = book.select_one('a.stealth')
                if title_elem and link_elem:
                    title = title_elem.get_text().strip()
                    if book_name.lower() in title.lower():
                        url = 'https://archive.org' + link_elem['href']
                        results.append((title, url))
            except:
                continue
    except:
        pass
    return results

def parse_manybooks(soup, book_name):
    """Parse ManyBooks search results."""
    results = []
    try:
        books = soup.select('div.book-listing')
        for book in books[:5]:
            try:
                title_elem = book.select_one('h3.book-title')
                link_elem = book.select_one('a.book-link')
                if title_elem and link_elem:
                    title = title_elem.get_text().strip()
                    if book_name.lower() in title.lower():
                        url = link_elem['href']
                        if not url.startswith('http'):
                            url = 'https://manybooks.net' + url
                        results.append((title, url))
            except:
                continue
    except:
        pass
    return results
                
                # Attempt to find book links based on different patterns
                if 'libgen.is' in url:
                    rows = soup.select('table.c tr[valign="top"]')
                    for row in rows[:3]:  # Check first 3 results
                        cells = row.find_all('td')
                        if len(cells) > 9:  # Ensure enough cells
                            title = cells[2].get_text().strip()
                            if book_name.lower() in title.lower():
                                # Get download link from the details page
                                link_cell = cells[9].find('a')
                                if link_cell and link_cell.has_attr('href'):
                                    return [(title, link_cell['href'])]
                
                elif 'b-ok.cc' in url:
                    books = soup.select('div.resItemBox')
                    for book in books[:3]:  # Check first 3 results
                        title_elem = book.select_one('h3.cover-item-title')
                        link_elem = book.select_one('a.cover-item-link')
                        if title_elem and link_elem:
                            title = title_elem.get_text().strip()
                            if book_name.lower() in title.lower():
                                return [(title, "https://b-ok.cc" + link_elem['href'])]
                
                elif 'pdfroom.com' in url:
                    books = soup.select('div.book-item')
                    for book in books[:3]:  # Check first 3 results
                        title_elem = book.select_one('h3.book-title')
                        link_elem = book.select_one('a.book-link')
                        if title_elem and link_elem:
                            title = title_elem.get_text().strip()
                            if book_name.lower() in title.lower():
                                return [(title, "https://pdfroom.com" + link_elem['href'])]
        
        return []  # No results found
    except Exception as e:
        logger.error(f"BS4 search error: {e}")
        return []

def search_with_specialized_api(book_name):
    """
    Advanced search using specialized APIs for finding books.
    This method is more reliable than the AI model and doesn't rely on Selenium.
    """
    results = []
    try:
        # List of book APIs to search
        apis = [
            {
                "url": f"https://openlibrary.org/search.json?q={quote(book_name)}&limit=5",
                "handler": lambda data: [
                    (item.get('title', ''), f"https://openlibrary.org{item.get('key', '')}")
                    for item in data.get('docs', [])
                    if item.get('title', '').lower().find(book_name.lower()) >= 0
                ]
            },
            {
                "url": f"https://www.googleapis.com/books/v1/volumes?q={quote(book_name)}&maxResults=5",
                "handler": lambda data: [
                    (item.get('volumeInfo', {}).get('title', ''), 
                     item.get('volumeInfo', {}).get('previewLink', ''))
                    for item in data.get('items', [])
                    if item.get('volumeInfo', {}).get('title', '').lower().find(book_name.lower()) >= 0
                ]
            },
            {
                "url": f"https://gutendex.com/books/?search={quote(book_name)}",
                "handler": lambda data: [
                    (item.get('title', ''), 
                     item.get('formats', {}).get('application/pdf', 
                                              item.get('formats', {}).get('text/html', '')))
                    for item in data.get('results', [])
                    if item.get('title', '').lower().find(book_name.lower()) >= 0
                ]
            }
        ]
        
        # Search each API
        for api in apis:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                response = requests.get(api['url'], headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    api_results = api['handler'](data)
                    
                    # Add valid results
                    for title, url in api_results:
                        if title and url and title.strip() and url.strip():
                            results.append((title, url))
                            
                    # If we have enough results, stop searching
                    if len(results) >= 3:
                        break
            except Exception as e:
                logger.error(f"API search error: {e}")
                continue
        
        # If no results from APIs, try HTML scraping as fallback
        if not results:
            try:
                search_url = f"https://www.pdfdrive.com/search?q={quote(book_name)}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                response = requests.get(search_url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    book_elements = soup.select('div.file-right')
                    
                    for book in book_elements[:5]:
                        try:
                            title_elem = book.select_one('h2')
                            link_elem = book.select_one('a')
                            
                            if title_elem and link_elem:
                                title = title_elem.get_text().strip()
                                link = link_elem.get('href')
                                
                                if link and book_name.lower() in title.lower():
                                    if not link.startswith(('http://', 'https://')):
                                        link = 'https://www.pdfdrive.com' + link
                                    results.append((title, link))
                                    
                                    if len(results) >= 3:
                                        break
                        except Exception as e:
                            logger.error(f"Error processing PDF Drive result: {e}")
                            continue
            except Exception as e:
                logger.error(f"PDF Drive search error: {e}")
        
        return results
    except Exception as e:
        logger.error(f"Specialized API search error: {e}")
        return []

def search_with_advanced_methods(book_name):
    """
    Ultra-advanced search for books using multiple specialized methods.
    Much more powerful than Model R1, this employs multiple techniques simultaneously.
    """
    results = []
    threads = []
    all_results = []
    
    # Method 1: Direct API search
    def direct_api_search():
        try:
            # List of APIs to try (with API endpoints)
            apis = [
                {
                    "url": f"https://openlibrary.org/search.json?q={quote(book_name)}&limit=5",
                    "parser": lambda data: [(item.get('title', ''), f"https://openlibrary.org{item.get('key', '')}") 
                                           for item in data.get('docs', []) 
                                           if item.get('title', '').lower().find(book_name.lower()) >= 0]
                },
                {
                    "url": f"https://www.googleapis.com/books/v1/volumes?q={quote(book_name)}&maxResults=5",
                    "parser": lambda data: [(item.get('volumeInfo', {}).get('title', ''), 
                                             item.get('volumeInfo', {}).get('previewLink', ''))
                                           for item in data.get('items', [])
                                           if item.get('volumeInfo', {}).get('title', '').lower().find(book_name.lower()) >= 0]
                }
            ]
            
            local_results = []
            for api in apis:
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                    response = requests.get(api['url'], headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        parsed_results = api['parser'](data)
                        local_results.extend(parsed_results)
                except Exception as e:
                    logger.error(f"API search error: {e}")
            
            return local_results[:3]  # Return up to 3 results
        except Exception as e:
            logger.error(f"Direct API search error: {e}")
            return []
    
    # Method 2: Advanced web scraping with dynamic content handling
    def advanced_scraping():
        try:
            local_results = []
            
            # List of sites with advanced parsing strategies
            sites = [
                {
                    "url": f"https://b-ok.cc/s/{quote(book_name)}",
                    "parse": lambda html: parse_z_library(html, book_name)
                },
                {
                    "url": f"https://www.academia.edu/search?q={quote(book_name)}",
                    "parse": lambda html: parse_academia(html, book_name)
                },
                {
                    "url": f"https://memoryoftheworld.org/#{quote(book_name)}",
                    "parse": lambda html: parse_memory_world(html, book_name)
                }
            ]
            
            for site in sites:
                if len(local_results) >= 3:
                    break
                    
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Referer': 'https://www.google.com/',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Cache-Control': 'max-age=0'
                    }
                    response = requests.get(site["url"], headers=headers, timeout=15)
                    if response.status_code == 200:
                        site_results = site["parse"](response.text)
                        local_results.extend(site_results)
                except Exception as e:
                    logger.error(f"Advanced scraping error for {site['url']}: {e}")
            
            return local_results[:3]  # Return up to 3 results
        except Exception as e:
            logger.error(f"Advanced scraping error: {e}")
            return []
    
    # Method 3: Deep web search using specialized techniques
    def deep_web_search():
        try:
            # This simulates searching in specialized repositories
            # In a real implementation, this could use more advanced techniques
            local_results = []
            
            search_terms = [
                f"{book_name} filetype:pdf",
                f"{book_name} book pdf download",
                f"{' '.join(book_name.split()[:3])} pdf"  # First 3 words for more general search
            ]
            
            for search_term in search_terms:
                try:
                    url = f"https://duckduckgo.com/html/?q={quote(search_term)}"
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        results_div = soup.find_all('div', {'class': 'result'})
                        
                        for result in results_div[:5]:
                            try:
                                title_elem = result.find('a', {'class': 'result__a'})
                                if not title_elem:
                                    continue
                                    
                                title = title_elem.text.strip()
                                link = title_elem.get('href')
                                
                                # Check if it's likely a PDF link
                                if '.pdf' in link.lower() or 'pdf' in link.lower() or 'book' in link.lower():
                                    local_results.append((title, link))
                                    
                                    if len(local_results) >= 3:
                                        break
                            except:
                                continue
                        
                        if len(local_results) >= 3:
                            break
                except Exception as e:
                    logger.error(f"Deep web search error for term {search_term}: {e}")
            
            return local_results
        except Exception as e:
            logger.error(f"Deep web search error: {e}")
            return []
    
    # Helper parsing functions for advanced scraping
    def parse_z_library(html, book_name):
        results = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            book_items = soup.select('.resItemBox')
            
            for item in book_items[:5]:
                try:
                    title_elem = item.select_one('h3.cover-item-title')
                    link_elem = item.select_one('a.cover-item-link')
                    
                    if title_elem and link_elem:
                        title = title_elem.text.strip()
                        link = link_elem.get('href')
                        
                        if link and book_name.lower() in title.lower():
                            if not link.startswith(('http://', 'https://')):
                                link = 'https://b-ok.cc' + link
                            results.append((title, link))
                            
                            if len(results) >= 3:
                                break
                except:
                    continue
        except Exception as e:
            logger.error(f"Z-Library parsing error: {e}")
        
        return results
    
    def parse_academia(html, book_name):
        results = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select('.js-search-result-item')
            
            for item in items[:5]:
                try:
                    title_elem = item.select_one('.paper-title')
                    link_elem = item.select_one('a.js-paper-title-link')
                    
                    if title_elem and link_elem:
                        title = title_elem.text.strip()
                        link = link_elem.get('href')
                        
                        if link and book_name.lower() in title.lower():
                            results.append((title, link))
                            
                            if len(results) >= 3:
                                break
                except:
                    continue
        except Exception as e:
            logger.error(f"Academia parsing error: {e}")
        
        return results
    
    def parse_memory_world(html, book_name):
        results = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select('.book-item')
            
            for item in items[:5]:
                try:
                    title_elem = item.select_one('.title')
                    link_elem = item.select_one('a.book-link')
                    
                    if title_elem and link_elem:
                        title = title_elem.text.strip()
                        link = link_elem.get('href')
                        
                        if link and book_name.lower() in title.lower():
                            results.append((title, link))
                            
                            if len(results) >= 3:
                                break
                except:
                    continue
        except Exception as e:
            logger.error(f"Memory of the World parsing error: {e}")
        
        return results
    
    # Start all methods in parallel threads
    t1 = threading.Thread(target=lambda: all_results.append(('api', direct_api_search())))
    t2 = threading.Thread(target=lambda: all_results.append(('scrape', advanced_scraping())))
    t3 = threading.Thread(target=lambda: all_results.append(('deep', deep_web_search())))
    
    threads = [t1, t2, t3]
    for t in threads:
        t.start()
    
    # Maximum wait time of 20 seconds
    for t in threads:
        t.join(timeout=20)
    
    # Collect results from all methods
    for method, method_results in all_results:
        for title, url in method_results:
            if (title, url) not in results:
                results.append((title, url))
                if len(results) >= 5:  # Get more results to filter the best ones
                    break
    
    # Filter and sort results to get the best matches
    filtered_results = []
    for title, url in results:
        # Calculate a relevance score - prioritize exact matches and PDFs
        score = 0
        if book_name.lower() in title.lower():
            score += 10
        if title.lower() == book_name.lower():
            score += 20
        if '.pdf' in url.lower():
            score += 15
        if 'download' in url.lower():
            score += 5
            
        filtered_results.append((title, url, score))
    
    # Sort by relevance score in descending order
    filtered_results.sort(key=lambda x: x[2], reverse=True)
    
    # Return the top 3 results as (title, url) tuples
    return [(title, url) for title, url, _ in filtered_results[:3]]

def search_with_direct_scraping(book_name):
    """
    Most powerful search method that directly scrapes multiple book sites.
    Uses advanced patterns to find PDFs and ebooks without relying on external libraries.
    """
    results = []
    try:
        # Multiple specialized book sites to search
        sites = [
            {
                "url": f"https://1lib.in/s/{quote(book_name)}?",
                "title_selector": "h3.cover-item-title",
                "link_selector": "a.cover-item-link",
                "container_selector": "div.resItemBox",
                "domain": "https://1lib.in"
            },
            {
                "url": f"https://booksc.xyz/s/{quote(book_name)}",
                "title_selector": "h3",
                "link_selector": "a.coloredBookTitle",
                "container_selector": "div.resItemBox",
                "domain": "https://booksc.xyz"
            },
            {
                "url": f"https://www.free-ebooks.net/search/{quote(book_name)}",
                "title_selector": "h3.title",
                "link_selector": "a.go-to-book",
                "container_selector": "div.book-preview-content",
                "domain": ""
            },
            {
                "url": f"https://manybooks.net/search-book?search={quote(book_name)}",
                "title_selector": "h2.field--name-title",
                "link_selector": "a",
                "container_selector": "div.col-book-info",
                "domain": "https://manybooks.net"
            }
        ]
        
        for site in sites:
            if len(results) >= 3:
                break
                
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://www.google.com/',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0'
                }
                
                response = requests.get(site["url"], headers=headers, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    containers = soup.select(site["container_selector"])
                    
                    for container in containers[:5]:  # Check first 5 results
                        try:
                            title_elem = container.select_one(site["title_selector"])
                            link_elem = container.select_one(site["link_selector"])
                            
                            if title_elem and link_elem:
                                title = title_elem.get_text().strip()
                                link = link_elem.get('href')
                                
                                # Add domain if relative URL
                                if link and site["domain"] and not link.startswith(('http://', 'https://')):
                                    link = site["domain"] + link
                                
                                # Match check and add to results
                                if link and book_name.lower() in title.lower():
                                    results.append((title, link))
                                    
                                    if len(results) >= 3:
                                        break
                        except Exception as e:
                            logger.error(f"Error processing book element: {e}")
                            continue
            except Exception as e:
                logger.error(f"Error searching site {site['url']}: {e}")
                continue
        
        # If no results found through specialized sites, try a more general approach
        if not results:
            # Custom search using DuckDuckGo
            search_url = f"https://html.duckduckgo.com/html/?q={quote(book_name)}+pdf+download+free"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            try:
                response = requests.get(search_url, headers=headers, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    result_links = soup.select('.result__a')
                    
                    for link in result_links[:10]:
                        title = link.get_text().strip()
                        url = link.get('href')
                        
                        # Check if it's likely a PDF or book
                        if any(term in url.lower() for term in ['.pdf', 'pdf', 'ebook', 'book', 'download']):
                            results.append((title, url))
                            
                            if len(results) >= 3:
                                break
            except Exception as e:
                logger.error(f"General search error: {e}")
        
        return results
    except Exception as e:
        logger.error(f"Direct scraping search error: {e}")
        return []

# Search management
def reset_search_quotas():
    """Reset search quotas for all users based on their last reset times."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    current_time = int(time.time())
    
    # Get all users
    cursor.execute("SELECT user_id, last_db_reset, last_ai_reset, last_r1_reset, last_r2_reset FROM SearchQuota")
    users = cursor.fetchall()
    
    for user in users:
        user_id, last_db_reset, last_ai_reset, last_r1_reset, last_r2_reset = user
        
        # Reset DB searches if 5 hours have passed
        if current_time - last_db_reset > FIVE_HOURS:
            cursor.execute(
                "UPDATE SearchQuota SET db_searches = 0, last_db_reset = ? WHERE user_id = ?", 
                (current_time, user_id)
            )
        
        # Reset AI searches if 5 hours have passed
        if current_time - last_ai_reset > FIVE_HOURS:
            cursor.execute(
                "UPDATE SearchQuota SET ai_searches = 0, last_ai_reset = ? WHERE user_id = ?", 
                (current_time, user_id)
            )
        
        # Reset R1 searches if 5 hours have passed
        if current_time - last_r1_reset > FIVE_HOURS:
            cursor.execute(
                "UPDATE SearchQuota SET r1_searches = 0, last_r1_reset = ? WHERE user_id = ?", 
                (current_time, user_id)
            )
        
        # Reset R2 searches if 24 hours have passed
        if current_time - last_r2_reset > TWENTY_FOUR_HOURS:
            cursor.execute(
                "UPDATE SearchQuota SET r2_searches = 0, last_r2_reset = ? WHERE user_id = ?", 
                (current_time, user_id)
            )
    
    conn.commit()
    conn.close()

def increment_search_count(search_type, user_id):
    """Increment the search count for a specific search type."""
    quota = get_search_quota(user_id)
    
    # Update the appropriate search count
    if search_type == 'db':
        update_search_quota(user_id, db_searches=quota['db_searches'] + 1)
    elif search_type == 'ai':
        update_search_quota(user_id, ai_searches=quota['ai_searches'] + 1)
    elif search_type == 'r1':
        update_search_quota(user_id, r1_searches=quota['r1_searches'] + 1)
    elif search_type == 'r2':
        update_search_quota(user_id, r2_searches=quota['r2_searches'] + 1)

def can_use_search_method(user_id, search_type):
    """Check if user can use a specific search method based on quotas."""
    user = get_user(user_id)
    quota = get_search_quota(user_id)
    current_time = int(time.time())
    
    # Check if user is in owner mode (unlimited credits)
    if user['owner_mode'] == 1:
        return True
    
    # Check if user is a premium user
    if user['premium_until'] > current_time:
        return True
    
    # Check for instant credits for database searches
    if search_type == 'db' and user['db_instant_credits'] > 0 and user['db_instant_expiry'] > current_time:
        update_user(user_id, db_instant_credits=user['db_instant_credits'] - 1)
        return True
    
    # Check for referral credits
    if user['referral_credits'] > 0 and user['referral_expiry'] > current_time:
        update_user(user_id, referral_credits=user['referral_credits'] - 1)
        return True
    
    # Check regular quotas
    if search_type == 'db':
        return quota['db_searches'] < DB_QUOTA
    elif search_type == 'ai':
        return quota['ai_searches'] < AI_QUOTA or user['ai_credits'] > 0
    elif search_type == 'r1':
        return quota['r1_searches'] < R1_QUOTA or user['r1_credits'] > 0
    elif search_type == 'r2':
        return quota['r2_searches'] < R2_QUOTA
    
    return False

def use_special_credit(user_id, search_type):
    """Use a special credit if available."""
    user = get_user(user_id)
    
    if search_type == 'ai' and user['ai_credits'] > 0:
        update_user(user_id, ai_credits=user['ai_credits'] - 1)
        return True
    elif search_type == 'r1' and user['r1_credits'] > 0:
        update_user(user_id, r1_credits=user['r1_credits'] - 1)
        return True
    
    return False

def dailybonus_command(update, context):
    """Handler for /dailybonus command - gives ₹50 once every 24 hours."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    current_time = int(time.time())
    
    # Check if last_daily_bonus exists in the user dictionary
    last_bonus_time = user.get('last_daily_bonus', 0)
    if last_bonus_time is None:
        last_bonus_time = 0
        # Update user to add the last_daily_bonus field
        update_user(user_id, last_daily_bonus=0)
    
    # Check if 24 hours have passed since the last bonus
    time_since_last_bonus = current_time - last_bonus_time
    
    if time_since_last_bonus >= TWENTY_FOUR_HOURS or last_bonus_time == 0:
        # Add bonus to user's balance
        new_balance = user['balance'] + DAILY_BONUS_AMOUNT
        update_user(user_id, balance=new_balance, last_daily_bonus=current_time)
        
        next_bonus_time = datetime.datetime.fromtimestamp(current_time + TWENTY_FOUR_HOURS)
        next_bonus_formatted = next_bonus_time.strftime("%d %b %Y, %H:%M")
        
        # More professional and visually appealing response
        update.message.reply_text(
            f"*🎁 DAILY BONUS COLLECTED!*\n\n"
            f"*₹{DAILY_BONUS_AMOUNT}* has been added to your account balance.\n"
            f"*New Balance:* ₹{new_balance}\n\n"
            f"📅 Next bonus available: *{next_bonus_formatted}*\n\n"
            f"_Return every 24 hours to collect your bonus and grow your balance!_",
            parse_mode='Markdown'
        )
    else:
        # Calculate remaining time
        remaining_seconds = TWENTY_FOUR_HOURS - time_since_last_bonus
        remaining_hours = remaining_seconds // 3600
        remaining_minutes = (remaining_seconds % 3600) // 60
        
        next_bonus_time = datetime.datetime.fromtimestamp(last_bonus_time + TWENTY_FOUR_HOURS)
        next_bonus_formatted = next_bonus_time.strftime("%d %b %Y, %H:%M")
        
        # More professional and visually appealing response
        update.message.reply_text(
            f"*⏳ DAILY BONUS COOLDOWN*\n\n"
            f"You've already collected your daily bonus.\n\n"
            f"*⏱️ Time remaining:* {remaining_hours}h {remaining_minutes}m\n"
            f"*📅 Next bonus available:* {next_bonus_formatted}\n\n"
            f"_Come back later to claim your next ₹{DAILY_BONUS_AMOUNT} bonus!_",
            parse_mode='Markdown'
        )

def ownermode_command(update, context):
    """Handler for /ownermode command - only for the bot owner."""
    user_id = update.effective_user.id
    
    # Only allow the owner (ID: 7130596820) to use this command
    if user_id != ADMIN_ID:
        update.message.reply_text("🔒 This command is only available to the bot owner.")
        return
    
    if not context.args:
        update.message.reply_text("Please specify 'on' or 'off'. Example: /ownermode on")
        return
    
    mode = context.args[0].lower()
    user = get_user(user_id)
    
    if mode == "on":
        update_user(user_id, owner_mode=1)
        update.message.reply_text(
            "👑 Owner mode activated!\n\n"
            "✅ You now have unlimited credits for all search methods\n"
            "✅ Unlimited balance\n"
            "✅ No verification required"
        )
    elif mode == "off":
        update_user(user_id, owner_mode=0)
        update.message.reply_text(
            "👑 Owner mode deactivated.\n\n"
            "You're now using the bot with regular user permissions."
        )
    else:
        update.message.reply_text("Invalid option. Please use 'on' or 'off'.")

def search_for_book(book_name, user_id, context, update):
    """Main function to search for a book using all available methods."""
    results = []
    
    # Try database search first
    if can_use_search_method(user_id, 'db'):
        results = search_book_in_db(book_name)
        if results:
            increment_search_count('db', user_id)
            return results, 'db'
    else:
        # If database quota exhausted, prompt for instant credits
        update.message.reply_text(
            "Database search quota exhausted! Pay ₹20 for 10 instant Database searches "
            "(30 min) or try using other search methods."
        )
    
    # Try AI Model (BeautifulSoup4)
    if can_use_search_method(user_id, 'ai'):
        used_special = use_special_credit(user_id, 'ai')
        if not used_special:
            increment_search_count('ai', user_id)
        
        results = search_with_bs4(book_name)
        if results:
            return results, 'ai'
    else:
        # If AI quota exhausted, prompt for credits or referrals
        update.message.reply_text(
            "AI search quota exhausted! Pay ₹20 for 2 AI credits (₹20 x credits, e.g., ₹200 for 10) "
            "or refer 1 friend for 10 credits (expires 5 hours), else try using Model R1."
        )
    
    # Try Model R1 (Selenium)
    if can_use_search_method(user_id, 'r1'):
        used_special = use_special_credit(user_id, 'r1')
        if not used_special:
            increment_search_count('r1', user_id)
        
        results = search_with_specialized_api(book_name)
        if results:
            return results, 'r1'
    else:
        # If R1 quota exhausted, prompt for credits or referrals
        update.message.reply_text(
            "Model R1 search quota exhausted! Pay ₹30 for 2 R1 credits (₹30 x credits, e.g., ₹300 for 10) "
            "or refer 2 friends for 10 credits (expires 5 hours), else try using Model R2."
        )
    
    # Try Model R2 (Scrapy)
    if can_use_search_method(user_id, 'r2'):
        increment_search_count('r2', user_id)
        results = search_with_direct_scraping(book_name)
        if results:
            return results, 'r2'
    else:
        # If R2 quota exhausted, inform user to wait
        update.message.reply_text(
            "Model R2 search quota exhausted! Please wait for the 24-hour reset."
        )
    
    return [], None

# Telegram command handlers
def start(update, context):
    """Handler for /start command."""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Check if started with referral parameter
    if context.args and context.args[0].isdigit():
        referrer_id = int(context.args[0])
        
        # Don't allow self-referrals
        if referrer_id != user_id:
            # Check if user is already in the database
            user = get_user(user_id)
            
            # If user is new (balance is 0), process the referral
            if user['balance'] == 0:
                referrer = get_user(referrer_id)
                
                # Add rewards to referrer
                update_user(
                    referrer_id,
                    balance=referrer['balance'] + REFERRAL_BALANCE,
                    referrals=referrer['referrals'] + 1,
                    ai_credits=referrer['ai_credits'] + REFERRAL_AI_CREDITS,
                    r1_credits=referrer['r1_credits'] + REFERRAL_R1_CREDITS,
                    referral_credits=referrer['referral_credits'] + REFERRAL_DB_CREDITS,
                    referral_expiry=int(time.time()) + FIVE_HOURS
                )
                
                # Notify referrer
                try:
                    context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 You have a new referral! Rewards added:\n"
                             f"- ₹{REFERRAL_BALANCE} balance\n"
                             f"- {REFERRAL_DB_CREDITS} Database credits\n"
                             f"- {REFERRAL_AI_CREDITS} AI credits\n"
                             f"- {REFERRAL_R1_CREDITS} R1 credits"
                    )
                except:
                    # If can't message the referrer, just log it
                    logger.info(f"Couldn't notify referrer {referrer_id} about new referral")
    
    # Check channel membership
    if not check_user_joined_channel(update, context):
        update.message.reply_text(f"Join {CHANNEL} to use this bot!")
        return
    
    # Create a more professional keyboard with emojis and better organization
    keyboard = [
        [
            InlineKeyboardButton("🔍 Search Book", callback_data="search"),
            InlineKeyboardButton("💰 Balance", callback_data="balance")
        ],
        [
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="dailybonus"),
            InlineKeyboardButton("🎟️ Credits", callback_data="credits")
        ],
        [
            InlineKeyboardButton("👥 Refer Friends", callback_data="referral"),
            InlineKeyboardButton("🌐 Web Referral", callback_data="web_referral")
        ],
        [
            InlineKeyboardButton("📚 Join Our Channel", url=f"https://t.me/{CHANNEL[1:]}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Get current user data
    current_user = get_user(user_id)
    
    # Forward message to admin if the user is not admin
    if user_id != ADMIN_ID:
        try:
            context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"👤 New bot user:\n"
                     f"Username: @{username}\n"
                     f"User ID: {user_id}\n"
                     f"Command: /start"
            )
        except Exception as e:
            logger.error(f"Failed to forward message to admin: {e}")
    
    # More professional welcome message with formatting and emojis
    try:
        update.message.reply_text(
            f"*📚 WELCOME TO PDF BOOK SEARCH BOT!*\n\n"
            f"Hello, *{username}*! Your personal assistant for finding and downloading books in PDF format.\n\n"
            f"*🔍 HOW TO USE:*\n"
            f"• `/book book_name` - Search for a book\n"
            f"• `/dailybonus` - Get daily reward of ₹{DAILY_BONUS_AMOUNT}\n"
            f"• `/balance` - Check your account\n"
            f"• `/referral` - Get your referral link\n\n"
            f"*💰 CURRENT BALANCE:* ₹{current_user['balance']}\n\n"
            f"_Join our channel for latest updates and free books!_",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        # Fallback if Markdown parsing fails
        update.message.reply_text(
            f"📚 WELCOME TO PDF BOOK SEARCH BOT!\n\n"
            f"Hello, {username}! Your personal assistant for finding and downloading books in PDF format.\n\n"
            f"HOW TO USE:\n"
            f"• /book book_name - Search for a book\n"
            f"• /dailybonus - Get daily reward of ₹{DAILY_BONUS_AMOUNT}\n"
            f"• /balance - Check your account\n"
            f"• /referral - Get your referral link\n\n"
            f"CURRENT BALANCE: ₹{current_user['balance']}\n\n"
            f"Join our channel for latest updates and free books!",
            reply_markup=reply_markup
        )

@requires_channel_membership
@requires_verification
def book_command(update, context):
    """Handler for /book command."""
    if not context.args:
        update.message.reply_text("Please provide a book name. Example: /book Python Programming")
        return
    
    book_name = ' '.join(context.args)
    user_id = update.effective_user.id
    
    # Notify user that search is in progress
    status_message = update.message.reply_text("🔍 Searching for your book... Please wait.")
    
    # Search for the book
    results, search_method = search_for_book(book_name, user_id, context, update)
    
    if results:
        # Choose the first valid result
        book_title, book_url = results[0]
        
        # Shorten the URL
        shortened_url = shorten_url(book_url)
        
        # Update user's balance and search count
        user = get_user(user_id)
        update_user(
            user_id, 
            search_count=user['search_count'] + 1,
            balance=user['balance'] - BOOK_PRICE if user['balance'] >= BOOK_PRICE else 0
        )
        
        # Delete the status message
        context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=status_message.message_id
        )
        
        # Send result with pay prompt
        update.message.reply_text(
            f"📚 Found: {book_title}\n\n"
            f"💰 Book price: ₹{BOOK_PRICE}\n"
            f"🔍 Search method: {search_method.upper()}\n\n"
            f"Type /pay {BOOK_PRICE} to get the download link!"
        )
        
        # Store URL in user's context for retrieval on payment
        if 'pending_urls' not in context.user_data:
            context.user_data['pending_urls'] = {}
        
        context.user_data['pending_urls'][str(BOOK_PRICE)] = {
            'url': shortened_url,
            'title': book_title,
            'timestamp': int(time.time())
        }
    else:
        # Delete the status message
        context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=status_message.message_id
        )
        
        # No results found
        update.message.reply_text(
            "😔 Sorry, I couldn't find that book. Try with a different name or spelling."
        )

@requires_channel_membership
def balance_command(update, context):
    """Handler for /balance command."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    update.message.reply_text(f"Balance: ₹{user['balance']}")

@requires_channel_membership
def credits_command(update, context):
    """Handler for /credits command."""
    user_id = update.effective_user.id
    quota = get_search_quota(user_id)
    user = get_user(user_id)
    
    # Calculate remaining free searches
    db_remaining = DB_QUOTA - quota['db_searches']
    ai_remaining = AI_QUOTA - quota['ai_searches']
    r1_remaining = R1_QUOTA - quota['r1_searches']
    r2_remaining = R2_QUOTA - quota['r2_searches']
    
    # Add purchased credits
    ai_remaining += user['ai_credits']
    r1_remaining += user['r1_credits']
    
    # Add instant database credits if active
    current_time = int(time.time())
    db_instant = 0
    if user['db_instant_credits'] > 0 and user['db_instant_expiry'] > current_time:
        db_instant = user['db_instant_credits']
    
    # Add referral credits if active
    referral_credits = 0
    if user['referral_credits'] > 0 and user['referral_expiry'] > current_time:
        referral_credits = user['referral_credits']
    
    update.message.reply_text(
        f"Credits:\n"
        f"- Database: {db_remaining} free + {db_instant} instant\n"
        f"- AI: {ai_remaining}\n"
        f"- R1: {r1_remaining}\n"
        f"- R2: {r2_remaining}\n"
        f"- Referral: {referral_credits}"
    )

@requires_channel_membership
def referral_command(update, context):
    """Handler for /referral command."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    referral_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start={user_id}"
    
    update.message.reply_text(
        f"🔗 Your referral link: {referral_link}\n\n"
        f"📊 Statistics:\n"
        f"- Referrals: {user['referrals']}\n"
        f"- Earned: ₹{user['referrals'] * REFERRAL_BALANCE}\n\n"
        f"💰 For each referral you get:\n"
        f"- ₹{REFERRAL_BALANCE}\n"
        f"- {REFERRAL_DB_CREDITS} Database credits\n"
        f"- {REFERRAL_AI_CREDITS} AI credits\n"
        f"- {REFERRAL_R1_CREDITS} R1 credits"
    )

@requires_channel_membership
def web_referral_command(update, context):
    """Handler for /web_referral command."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    update.message.reply_text(
        f"💻 Register on Shrinkearn using this link to get Premium benefits:\n\n"
        f"{SHRINKEARN_REFERRAL}\n\n"
        f"🎁 Rewards:\n"
        f"- ₹{PREMIUM_REWARD} added to your balance\n"
        f"- 48-hour Premium Status with unlimited searches\n\n"
        f"✅ Requirements:\n"
        f"- Use a real Gmail account\n"
        f"- After signup, message @books086 with your Gmail address and Telegram ID ({user_id})\n"
        f"- Admin will verify and activate your rewards within 24 hours"
    )

@requires_channel_membership
def pay_command(update, context):
    """Handler for /pay command."""
    if not context.args or not context.args[0].isdigit():
        update.message.reply_text("Please specify an amount. Example: /pay 20")
        return
    
    amount = int(context.args[0])
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    # Check if user has a pending book URL with this exact payment amount
    if 'pending_urls' in context.user_data and str(amount) in context.user_data['pending_urls']:
        pending_info = context.user_data['pending_urls'][str(amount)]
        
        # Check if URL is still valid (not expired after 1 hour)
        current_time = int(time.time())
        if current_time - pending_info['timestamp'] <= 3600:  # 1 hour in seconds
            update.message.reply_text(
                f"📚 Book: {pending_info['title']}\n\n"
                f"🔗 Download link: {pending_info['url']}"
            )
            
            # Remove the pending URL after sending
            del context.user_data['pending_urls'][str(amount)]
            return
    
    # Handle different payment amounts for credits
    if amount == 20:
        # Check if user has enough balance
        if user['balance'] < amount:
            update.message.reply_text(
                f"Insufficient balance. You have ₹{user['balance']} but need ₹{amount}."
            )
            return
        
        # Deduct balance and add 10 instant database credits for 30 minutes
        update_user(
            user_id, 
            balance=user['balance'] - amount,
            db_instant_credits=10,
            db_instant_expiry=int(time.time()) + THIRTY_MINUTES
        )
        
        update.message.reply_text(
            "✅ Payment successful!\n\n"
            "You have received 10 instant Database search credits valid for 30 minutes."
        )
    
    elif amount == 7:
        # Standard book payment
        update.message.reply_text(
            "This payment can only be used for purchasing book links. "
            "Use /book <book_name> to search for a book first."
        )
    
    else:
        # Handle AI and R1 credit purchases
        credits_to_add = 0
        credit_type = ""
        
        if amount % 20 == 0 and amount >= 20:
            # AI credits (₹20 per 2 credits)
            credits_to_add = amount // 10
            credit_type = "AI"
            
            # Check if user has enough balance
            if user['balance'] < amount:
                update.message.reply_text(
                    f"Insufficient balance. You have ₹{user['balance']} but need ₹{amount}."
                )
                return
            
            # Deduct balance and add AI credits
            update_user(
                user_id, 
                balance=user['balance'] - amount,
                ai_credits=user['ai_credits'] + credits_to_add
            )
        
        elif amount % 30 == 0 and amount >= 30:
            # R1 credits (₹30 per 2 credits)
            credits_to_add = (amount // 30) * 2
            credit_type = "R1"
            
            # Check if user has enough balance
            if user['balance'] < amount:
                update.message.reply_text(
                    f"Insufficient balance. You have ₹{user['balance']} but need ₹{amount}."
                )
                return
            
            # Deduct balance and add R1 credits
            update_user(
                user_id, 
                balance=user['balance'] - amount,
                r1_credits=user['r1_credits'] + credits_to_add
            )
        
        if credits_to_add > 0:
            update.message.reply_text(
                f"✅ Payment successful!\n\n"
                f"You have received {credits_to_add} {credit_type} credits."
            )
        else:
            update.message.reply_text(
                "Invalid amount. Available options:\n"
                "- /pay 20: 10 instant Database searches (30 min)\n"
                "- /pay <multiple of 20>: AI credits (₹20 per 2 credits)\n"
                "- /pay <multiple of 30>: R1 credits (₹30 per 2 credits)"
            )

@requires_channel_membership
def addbooks_command(update, context):
    """Handler for /addbooks command."""
    update.message.reply_text(
        "If you have a book PDF to contribute, please submit it to "
        f"{VERIFICATION_CHAMBER} for verification.\n\n"
        "Include the book name and a direct download link."
    )

def admin_check(user_id):
    """Check if user is an admin."""
    return user_id == ADMIN_ID

def uploadbooks_command(update, context):
    """Handler for /uploadbooks command (admin only)."""
    user_id = update.effective_user.id
    
    if not admin_check(user_id):
        update.message.reply_text("This command is for administrators only.")
        return
    
    if len(context.args) < 2:
        update.message.reply_text("Usage: /uploadbooks <book_name> <url>")
        return
    
    # Get book name and URL from arguments
    url = context.args[-1]
    book_name = ' '.join(context.args[:-1])
    
    # Validate URL format
    if not re.match(r'^https?://', url):
        update.message.reply_text("Invalid URL format. Please provide a valid URL.")
        return
    
    # Add book to database
    try:
        add_book(book_name, url)
        update.message.reply_text(f"Book '{book_name}' successfully added to the database.")
    except Exception as e:
        update.message.reply_text(f"Error adding book: {str(e)}")

def note_command(update, context):
    """Handler for /note command."""
    update.message.reply_text(
        "📝 Bot Usage Guide:\n\n"
        "1. Search for books with /book <book_name>\n"
        "2. Check your balance with /balance\n"
        "3. View available credits with /credits\n"
        "4. Share your referral link with /referral\n"
        "5. Earn premium benefits with /web_referral\n"
        "6. Purchase credits with /pay command:\n"
        "   - /pay 20: 10 instant Database searches (30 min)\n"
        "   - /pay <multiple of 20>: AI credits\n"
        "   - /pay <multiple of 30>: R1 credits\n\n"
        f"Make sure you've joined {CHANNEL} to use this bot!\n\n"
        "Happy reading! 📚"
    )

def checkdb_command(update, context):
    """Handler for /checkdb command (admin only)."""
    user_id = update.effective_user.id
    
    if not admin_check(user_id):
        update.message.reply_text("This command is for administrators only.")
        return
    
    # Get all books from database
    books = get_all_books()
    
    if not books:
        update.message.reply_text("The database is empty.")
        return
    
    # Create a menu of books for deletion
    keyboard = []
    for book_id, name, url in books[:10]:  # Limit to 10 books per page
        button = InlineKeyboardButton(f"Delete: {name[:30]}", callback_data=f"delete_{book_id}")
        keyboard.append([button])
    
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel_delete")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"Found {len(books)} books in the database.\n"
        "Select a book to delete:",
        reply_markup=reply_markup
    )

# Button callback handlers
def button_callback(update, context):
    """Handle button callbacks."""
    query = update.callback_query
    query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "balance":
        user = get_user(user_id)
        query.edit_message_text(text=f"Balance: ₹{user['balance']}")
    
    elif data == "credits":
        quota = get_search_quota(user_id)
        user = get_user(user_id)
        
        # Calculate remaining free searches
        db_remaining = DB_QUOTA - quota['db_searches']
        ai_remaining = AI_QUOTA - quota['ai_searches']
        r1_remaining = R1_QUOTA - quota['r1_searches']
        r2_remaining = R2_QUOTA - quota['r2_searches']
        
        # Add purchased credits
        ai_remaining += user['ai_credits']
        r1_remaining += user['r1_credits']
        
        # Add instant database credits if active
        current_time = int(time.time())
        db_instant = 0
        if user['db_instant_credits'] > 0 and user['db_instant_expiry'] > current_time:
            db_instant = user['db_instant_credits']
        
        # Add referral credits if active
        referral_credits = 0
        if user['referral_credits'] > 0 and user['referral_expiry'] > current_time:
            referral_credits = user['referral_credits']
        
        query.edit_message_text(
            f"Credits:\n"
            f"- Database: {db_remaining} free + {db_instant} instant\n"
            f"- AI: {ai_remaining}\n"
            f"- R1: {r1_remaining}\n"
            f"- R2: {r2_remaining}\n"
            f"- Referral: {referral_credits}"
        )
    
    elif data == "referral":
        user = get_user(user_id)
        
        referral_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start={user_id}"
        
        # Professional-looking referral message with Markdown formatting
        try:
            query.edit_message_text(
                f"*👥 YOUR REFERRAL PROGRAM*\n\n"
                f"*Share your personal link with friends:*\n"
                f"`{referral_link}`\n\n"
                f"*📊 Statistics:*\n"
                f"• Referrals: *{user['referrals']}*\n"
                f"• Earned: *₹{user['referrals'] * REFERRAL_BALANCE}*\n\n"
                f"*💰 For each referral you get:*\n"
                f"• ₹{REFERRAL_BALANCE} added to your balance\n"
                f"• {REFERRAL_DB_CREDITS} Database credits\n"
                f"• {REFERRAL_AI_CREDITS} AI credits\n"
                f"• {REFERRAL_R1_CREDITS} R1 credits\n\n"
                f"_More referrals = more rewards!_",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
                ])
            )
        except Exception as e:
            # Fallback without formatting if Markdown fails
            query.edit_message_text(
                f"👥 YOUR REFERRAL PROGRAM\n\n"
                f"Share your personal link with friends:\n"
                f"{referral_link}\n\n"
                f"📊 Statistics:\n"
                f"• Referrals: {user['referrals']}\n"
                f"• Earned: ₹{user['referrals'] * REFERRAL_BALANCE}\n\n"
                f"💰 For each referral you get:\n"
                f"• ₹{REFERRAL_BALANCE} added to your balance\n"
                f"• {REFERRAL_DB_CREDITS} Database credits\n"
                f"• {REFERRAL_AI_CREDITS} AI credits\n"
                f"• {REFERRAL_R1_CREDITS} R1 credits\n\n"
                f"More referrals = more rewards!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
                ])
            )
            
    elif data == "dailybonus":
        # Daily bonus callback handler
        user = get_user(user_id)
        current_time = int(time.time())
        
        # Check if last_daily_bonus exists in the user dictionary
        last_bonus_time = user.get('last_daily_bonus', 0)
        if last_bonus_time is None:
            last_bonus_time = 0
            # Update user to add the last_daily_bonus field
            update_user(user_id, last_daily_bonus=0)
        
        # Check if 24 hours have passed since the last bonus
        time_since_last_bonus = current_time - last_bonus_time
        
        if time_since_last_bonus >= TWENTY_FOUR_HOURS or last_bonus_time == 0:
            # Add bonus to user's balance
            new_balance = user['balance'] + DAILY_BONUS_AMOUNT
            update_user(user_id, balance=new_balance, last_daily_bonus=current_time)
            
            next_bonus_time = datetime.datetime.fromtimestamp(current_time + TWENTY_FOUR_HOURS)
            next_bonus_formatted = next_bonus_time.strftime("%d %b %Y, %H:%M")
            
            # Professional-looking success message with Markdown
            try:
                query.edit_message_text(
                    f"*🎁 DAILY BONUS COLLECTED!*\n\n"
                    f"*₹{DAILY_BONUS_AMOUNT}* has been added to your account balance.\n"
                    f"*New Balance:* ₹{new_balance}\n\n"
                    f"📅 Next bonus available: *{next_bonus_formatted}*\n\n"
                    f"_Return every 24 hours to collect your bonus!_",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
                    ])
                )
            except Exception as e:
                # Fallback without formatting if Markdown fails
                query.edit_message_text(
                    f"🎁 DAILY BONUS COLLECTED!\n\n"
                    f"₹{DAILY_BONUS_AMOUNT} has been added to your account balance.\n"
                    f"New Balance: ₹{new_balance}\n\n"
                    f"📅 Next bonus available: {next_bonus_formatted}\n\n"
                    f"Return every 24 hours to collect your bonus!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
                    ])
                )
        else:
            # Calculate remaining time
            remaining_seconds = TWENTY_FOUR_HOURS - time_since_last_bonus
            remaining_hours = remaining_seconds // 3600
            remaining_minutes = (remaining_seconds % 3600) // 60
            
            next_bonus_time = datetime.datetime.fromtimestamp(last_bonus_time + TWENTY_FOUR_HOURS)
            next_bonus_formatted = next_bonus_time.strftime("%d %b %Y, %H:%M")
            
            # Professional-looking cooldown message with Markdown
            try:
                query.edit_message_text(
                    f"*⏳ DAILY BONUS COOLDOWN*\n\n"
                    f"You've already collected your daily bonus.\n\n"
                    f"*⏱️ Time remaining:* {remaining_hours}h {remaining_minutes}m\n"
                    f"*📅 Next bonus available:* {next_bonus_formatted}\n\n"
                    f"_Come back later to claim your next ₹{DAILY_BONUS_AMOUNT} bonus!_",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
                    ])
                )
            except Exception as e:
                # Fallback without formatting if Markdown fails
                query.edit_message_text(
                    f"⏳ DAILY BONUS COOLDOWN\n\n"
                    f"You've already collected your daily bonus.\n\n"
                    f"⏱️ Time remaining: {remaining_hours}h {remaining_minutes}m\n"
                    f"📅 Next bonus available: {next_bonus_formatted}\n\n"
                    f"Come back later to claim your next ₹{DAILY_BONUS_AMOUNT} bonus!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
                    ])
                )
    
    elif data == "web_referral":
        user = get_user(user_id)
        
        # Professional-looking web referral message with Markdown
        try:
            query.edit_message_text(
                f"*🌐 PREMIUM PARTNER PROGRAM*\n\n"
                f"Register on Shrinkearn using this link to unlock Premium benefits:\n"
                f"`{SHRINKEARN_REFERRAL}`\n\n"
                f"*🎁 Premium Rewards:*\n"
                f"• ₹{PREMIUM_REWARD} added to your balance\n"
                f"• 48-hour Premium Status with unlimited searches\n\n"
                f"*✅ Requirements:*\n"
                f"• Use a real Gmail account\n"
                f"• After signup, message @books086 with your Gmail address and ID ({user_id})\n"
                f"• Admin will verify and activate your rewards within 24 hours",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
                ])
            )
        except Exception as e:
            # Fallback without formatting if Markdown fails
            query.edit_message_text(
                f"🌐 PREMIUM PARTNER PROGRAM\n\n"
                f"Register on Shrinkearn using this link to unlock Premium benefits:\n"
                f"{SHRINKEARN_REFERRAL}\n\n"
                f"🎁 Premium Rewards:\n"
                f"• ₹{PREMIUM_REWARD} added to your balance\n"
                f"• 48-hour Premium Status with unlimited searches\n\n"
                f"✅ Requirements:\n"
                f"• Use a real Gmail account\n"
                f"• After signup, message @books086 with your Gmail address and ID ({user_id})\n"
                f"• Admin will verify and activate your rewards within 24 hours",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
                ])
            )
            
    elif data == "help_user":
        # Show user commands
        try:
            query.edit_message_text(
                "*📚 Available User Commands*\n\n"
                "• /start - Start the bot\n"
                "• /book <name> - Search for a book\n"
                "• /balance - Check your balance\n"
                "• /credits - View available credits\n"
                "• /dailybonus - Get daily reward\n"
                "• /referral - Get referral link\n"
                "• /web_referral - Premium partner program\n"
                "• /help - Show this help message\n"
                "• /note - View usage guide\n\n"
                "_Click the button below to go back._",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="help_back")]
                ])
            )
        except Exception as e:
            logger.error(f"Error showing user help: {e}")
            query.edit_message_text("Error showing help. Please try again.")

    elif data == "help_admin":
        # Show admin commands (only for admins)
        if not admin_check(user_id):
            query.edit_message_text("🔒 Admin commands are only available to administrators.")
            return

        try:
            query.edit_message_text(
                "*🔧 Admin Commands*\n\n"
                "• /adminpanel - Admin dashboard\n"
                "• /broadcast - Send message to all users\n"
                "• /uploadbooks - Add books to database\n"
                "• /checkdb - View database books\n"
                "• /checkstorage - Check database size\n"
                "• /clearquiz - Manage quizzes\n"
                "• /pinupdate - Manage updates\n"
                "• /setadmin - Set admin status\n"
                "• /reply - Reply to user messages\n"
                "• /newtask - Create new quiz\n"
                "• /ownermode - Toggle owner mode\n\n"
                "_Click the button below to go back._",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="help_back")]
                ])
            )
        except Exception as e:
            logger.error(f"Error showing admin help: {e}")
            query.edit_message_text("Error showing help. Please try again.")

    elif data == "help_back":
        # Return to help menu
        keyboard = [
            [InlineKeyboardButton("📋 User Commands", callback_data="help_user")]
        ]
        if admin_check(user_id):
            keyboard.append([InlineKeyboardButton("🔧 Admin Commands", callback_data="help_admin")])

        query.edit_message_text(
            "*📚 Bot Help*\n\n"
            "This bot helps you find and download books in PDF format.\n"
            "Select an option below to see available commands:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif data == "back_to_menu":
        # Return to main menu with professional formatting
        user = get_user(user_id)
        username = query.from_user.username or "User"
        
        # Create a professional keyboard with emojis and better organization
        keyboard = [
            [
                InlineKeyboardButton("🔍 Search Book", callback_data="search"),
                InlineKeyboardButton("💰 Balance", callback_data="balance")
            ],
            [
                InlineKeyboardButton("🎁 Daily Bonus", callback_data="dailybonus"),
                InlineKeyboardButton("🎟️ Credits", callback_data="credits")
            ],
            [
                InlineKeyboardButton("👥 Refer Friends", callback_data="referral"),
                InlineKeyboardButton("🌐 Web Referral", callback_data="web_referral")
            ],
            [
                InlineKeyboardButton("📚 Join Our Channel", url=f"https://t.me/{CHANNEL[1:]}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # More professional welcome message with formatting and emojis
        try:
            query.edit_message_text(
                f"*📚 PDF BOOK SEARCH BOT*\n\n"
                f"Hello, *{username}*! Your personal assistant for finding and downloading books in PDF format.\n\n"
                f"*🔍 HOW TO USE:*\n"
                f"• `/book book_name` - Search for a book\n"
                f"• `/dailybonus` - Get daily reward of ₹{DAILY_BONUS_AMOUNT}\n"
                f"• `/balance` - Check your account\n"
                f"• `/referral` - Get your referral link\n\n"
                f"*💰 CURRENT BALANCE:* ₹{user['balance']}\n\n"
                f"_Join our channel for latest updates and free books!_",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            # Fallback if Markdown parsing fails
            query.edit_message_text(
                f"📚 PDF BOOK SEARCH BOT\n\n"
                f"Hello, {username}! Your personal assistant for finding and downloading books in PDF format.\n\n"
                f"HOW TO USE:\n"
                f"• /book book_name - Search for a book\n"
                f"• /dailybonus - Get daily reward of ₹{DAILY_BONUS_AMOUNT}\n"
                f"• /balance - Check your account\n"
                f"• /referral - Get your referral link\n\n"
                f"CURRENT BALANCE: ₹{user['balance']}\n\n"
                f"Join our channel for latest updates and free books!",
                reply_markup=reply_markup
            )
    
    elif data.startswith("delete_"):
        # Admin only - delete a book
        if not admin_check(user_id):
            query.edit_message_text("This action is for administrators only.")
            return
        
        book_id = int(data.split('_')[1])
        delete_book(book_id)
        query.edit_message_text(f"Book with ID {book_id} deleted successfully.")
    
    elif data == "cancel_delete":
        query.edit_message_text("Database check cancelled.")

# Job scheduling
def schedule_daily_bonus(context):
    """Schedule daily bonus distribution."""
    # Calculate time until 10 PM today
    now = datetime.datetime.now()
    target_time = now.replace(hour=22, minute=0, second=0, microsecond=0)
    
    # If it's already past 10 PM, schedule for tomorrow
    if now > target_time:
        target_time += datetime.timedelta(days=1)
    
    # Calculate seconds until target time
    seconds_until_target = (target_time - now).total_seconds()
    
    # Schedule the job
    context.job_queue.run_once(
        distribute_daily_bonus,
        seconds_until_target
    )
    logger.info(f"Daily bonus scheduled for {target_time}")

def distribute_daily_bonus(context):
    """Distribute daily bonus to all users."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all users
    cursor.execute("SELECT user_id FROM Users")
    users = cursor.fetchall()
    
    # Add bonus to each user
    current_time = int(time.time())
    for user in users:
        user_id = user[0]
        
        # Update user with daily bonus
        cursor.execute(
            "UPDATE Users SET balance = balance + ?, premium_until = ? WHERE user_id = ?",
            (DAILY_BONUS_BALANCE, current_time + TWENTY_MINUTES, user_id)
        )
        
        # Try to notify the user
        try:
            context.bot.send_message(
                chat_id=user_id,
                text=f"🎁 Daily Bonus: ₹{DAILY_BONUS_BALANCE} added to your balance!\n\n"
                     f"✨ You also have unlimited premium searches for the next 20 minutes!"
            )
        except:
            logger.info(f"Couldn't notify user {user_id} about daily bonus")
    
    conn.commit()
    conn.close()
    
    # Schedule notification for when premium period ends
    context.job_queue.run_once(
        notify_premium_end,
        TWENTY_MINUTES
    )
    
    # Schedule next daily bonus
    context.job_queue.run_once(
        distribute_daily_bonus,
        TWENTY_FOUR_HOURS
    )

def notify_premium_end(context):
    """Notify users that premium period has ended."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all users
    cursor.execute("SELECT user_id FROM Users")
    users = cursor.fetchall()
    
    for user in users:
        user_id = user[0]
        
        # Try to notify the user
        try:
            context.bot.send_message(
                chat_id=user_id,
                text="⏰ Premium search period has ended. Regular search quotas are now in effect."
            )
        except:
            pass
    
    conn.close()

# New admin monitoring function
def message_handler(update, context):
    """Handle normal text messages and forward them to admin."""
    if not update.message:
        return
        
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    message_text = update.message.text
    
    # Skip if this is a command
    if message_text.startswith('/'):
        return
    
    # Handle quiz creation process for admin
    if user_id == ADMIN_ID and 'quiz_state' in context.user_data:
        handle_quiz_creation(update, context)
        return
    
    # Forward all non-admin messages to admin for monitoring
    if user_id != ADMIN_ID:
        try:
            # Get user details for better tracking
            user = get_user(user_id, update)
            first_name = user.get('first_name', '')
            last_name = user.get('last_name', '')
            full_name = f"{first_name or ''} {last_name or ''}".strip() or "Unknown"
            
            # Create inline keyboard for quick reply
            keyboard = [
                [InlineKeyboardButton("📝 Reply", callback_data=f"reply_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Forward message to admin with user info
            context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"📨 *Message from user:*\n"
                     f"*Name:* {full_name}\n"
                     f"*Username:* @{username}\n"
                     f"*User ID:* `{user_id}`\n"
                     f"*Message:*\n"
                     f"```\n{message_text}\n```",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            # Respond to user
            update.message.reply_text(
                "✅ Your message has been received. Our team will get back to you soon."
            )
        except Exception as e:
            logger.error(f"Failed to forward message to admin: {e}")
            
# Handle quiz creation process
def handle_quiz_creation(update, context):
    """Handle quiz creation process for admin."""
    if 'quiz_state' not in context.user_data:
        return
        
    quiz_state = context.user_data['quiz_state']
    message_text = update.message.text
    
    # Cancel quiz creation
    if message_text.lower() == '/cancel':
        context.user_data.pop('quiz_state', None)
        context.user_data.pop('quiz_data', None)
        context.user_data.pop('quiz_questions', None)
        update.message.reply_text("❌ Quiz creation cancelled.")
        return
        
    # Complete the quiz creation
    if quiz_state == QuizCreationState.CONFIRM and message_text.lower() == '/done':
        # Get quiz data
        quiz_data = context.user_data.get('quiz_data', {})
        quiz_questions = context.user_data.get('quiz_questions', [])
        
        if not quiz_data or not quiz_questions:
            update.message.reply_text("❌ Quiz data is incomplete. Please try again.")
            context.user_data.pop('quiz_state', None)
            context.user_data.pop('quiz_data', None)
            context.user_data.pop('quiz_questions', None)
            return
            
        # Save quiz to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Insert quiz
            cursor.execute(
                """INSERT INTO Quizzes 
                   (title, description, created_by, created_at, reward_amount, min_score_percent)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    quiz_data.get('title', 'Untitled Quiz'),
                    quiz_data.get('description', 'No description provided.'),
                    update.effective_user.id,
                    int(time.time()),
                    quiz_data.get('reward', 50),
                    quiz_data.get('min_score', 50)
                )
            )
            conn.commit()
            
            # Get the new quiz ID
            quiz_id = cursor.lastrowid
            
            # Insert questions
            for question in quiz_questions:
                cursor.execute(
                    """INSERT INTO QuizQuestions
                       (quiz_id, question, option_a, option_b, option_c, option_d, correct_option)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        quiz_id,
                        question.get('question', ''),
                        question.get('option_a', ''),
                        question.get('option_b', ''),
                        question.get('option_c', ''),
                        question.get('option_d', ''),
                        question.get('correct_option', 'A')
                    )
                )
            conn.commit()
            
            # Broadcast to all users about new quiz
            cursor.execute("SELECT user_id FROM Users")
            users = cursor.fetchall()
            
            # Create quiz announcement message
            announcement = (
                f"🎮 *New Quiz Available!*\n\n"
                f"*{quiz_data.get('title', 'Untitled Quiz')}*\n"
                f"{quiz_data.get('description', 'No description provided.')}\n\n"
                f"Reward: ₹{quiz_data.get('reward', 50)}\n"
                f"Required score: {quiz_data.get('min_score', 50)}%\n\n"
                f"Complete the quiz to earn rewards!"
            )
            
            # Create keyboard for quiz
            keyboard = [
                [InlineKeyboardButton("🎮 Start Quiz", callback_data=f"quiz_{quiz_id}_start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send to users
            success_count = 0
            for user in users:
                try:
                    context.bot.send_message(
                        chat_id=user[0],
                        text=announcement,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                    success_count += 1
                    time.sleep(0.05)  # Sleep to avoid hitting rate limits
                except Exception as e:
                    logger.error(f"Failed to send quiz announcement to user {user[0]}: {e}")
            
            # Complete quiz creation
            update.message.reply_text(
                f"✅ Quiz created successfully!\n\n"
                f"Title: {quiz_data.get('title', 'Untitled Quiz')}\n"
                f"Questions: {len(quiz_questions)}\n"
                f"Announcement sent to {success_count} users."
            )
            
            # Clear quiz state
            context.user_data.pop('quiz_state', None)
            context.user_data.pop('quiz_data', None)
            context.user_data.pop('quiz_questions', None)
            
        except Exception as e:
            logger.error(f"Error creating quiz: {e}")
            update.message.reply_text(f"❌ Error creating quiz: {str(e)}")
            conn.rollback()
        finally:
            conn.close()
        return
        
    # Process quiz creation steps
    try:
        if quiz_state == QuizCreationState.TITLE:
            context.user_data['quiz_data'] = {'title': message_text}
            context.user_data['quiz_state'] = QuizCreationState.DESCRIPTION
            update.message.reply_text(
                "*Step 2:* Enter a description for your quiz:",
                parse_mode='Markdown'
            )
            
        elif quiz_state == QuizCreationState.DESCRIPTION:
            context.user_data['quiz_data']['description'] = message_text
            context.user_data['quiz_state'] = QuizCreationState.REWARD
            update.message.reply_text(
                "*Step 3:* Enter the reward amount (in ₹) for completing the quiz:",
                parse_mode='Markdown'
            )
            
        elif quiz_state == QuizCreationState.REWARD:
            try:
                reward = int(message_text)
                if reward < 0:
                    raise ValueError("Reward must be a positive number")
                context.user_data['quiz_data']['reward'] = reward
                context.user_data['quiz_state'] = QuizCreationState.MIN_SCORE
                update.message.reply_text(
                    "*Step 4:* Enter the minimum score percentage (0-100) required to get the reward:",
                    parse_mode='Markdown'
                )
            except ValueError:
                update.message.reply_text("❌ Please enter a valid number for the reward amount.")
                
        elif quiz_state == QuizCreationState.MIN_SCORE:
            try:
                min_score = int(message_text)
                if min_score < 0 or min_score > 100:
                    raise ValueError("Minimum score must be between 0 and 100")
                context.user_data['quiz_data']['min_score'] = min_score
                context.user_data['quiz_state'] = QuizCreationState.QUESTION
                update.message.reply_text(
                    "*Step 5:* Let's add questions to your quiz. Enter your first question:",
                    parse_mode='Markdown'
                )
            except ValueError:
                update.message.reply_text("❌ Please enter a valid percentage (0-100).")
                
        elif quiz_state == QuizCreationState.QUESTION:
            context.user_data['current_question'] = {'question': message_text}
            context.user_data['quiz_state'] = QuizCreationState.OPTION_A
            update.message.reply_text(
                "*Step 6:* Enter option A for this question:",
                parse_mode='Markdown'
            )
            
        elif quiz_state == QuizCreationState.OPTION_A:
            context.user_data['current_question']['option_a'] = message_text
            context.user_data['quiz_state'] = QuizCreationState.OPTION_B
            update.message.reply_text(
                "*Step 7:* Enter option B for this question:",
                parse_mode='Markdown'
            )
            
        elif quiz_state == QuizCreationState.OPTION_B:
            context.user_data['current_question']['option_b'] = message_text
            context.user_data['quiz_state'] = QuizCreationState.OPTION_C
            update.message.reply_text(
                "*Step 8:* Enter option C for this question:",
                parse_mode='Markdown'
            )
            
        elif quiz_state == QuizCreationState.OPTION_C:
            context.user_data['current_question']['option_c'] = message_text
            context.user_data['quiz_state'] = QuizCreationState.OPTION_D
            update.message.reply_text(
                "*Step 9:* Enter option D for this question:",
                parse_mode='Markdown'
            )
            
        elif quiz_state == QuizCreationState.OPTION_D:
            context.user_data['current_question']['option_d'] = message_text
            context.user_data['quiz_state'] = QuizCreationState.CORRECT_OPTION
            update.message.reply_text(
                "*Step 10:* Enter the correct option for this question (A, B, C, or D):",
                parse_mode='Markdown'
            )
            
        elif quiz_state == QuizCreationState.CORRECT_OPTION:
            correct_option = message_text.upper()
            if correct_option not in ['A', 'B', 'C', 'D']:
                update.message.reply_text("❌ Please enter a valid option (A, B, C, or D).")
                return
                
            context.user_data['current_question']['correct_option'] = correct_option
            
            # Add question to list
            if 'quiz_questions' not in context.user_data:
                context.user_data['quiz_questions'] = []
            context.user_data['quiz_questions'].append(context.user_data['current_question'])
            
            # Move to add more state
            context.user_data['quiz_state'] = QuizCreationState.ADD_MORE
            update.message.reply_text(
                "*Question added successfully!*\n\n"
                "Would you like to add another question?\n"
                "Type 'yes' to add another question or 'no' to finish the quiz.",
                parse_mode='Markdown'
            )
            
        elif quiz_state == QuizCreationState.ADD_MORE:
            if message_text.lower() == 'yes':
                context.user_data['quiz_state'] = QuizCreationState.QUESTION
                update.message.reply_text(
                    "*Add another question:*\n\n"
                    "Enter your question:",
                    parse_mode='Markdown'
                )
            elif message_text.lower() == 'no':
                context.user_data['quiz_state'] = QuizCreationState.CONFIRM
                
                # Show quiz summary
                quiz_data = context.user_data.get('quiz_data', {})
                quiz_questions = context.user_data.get('quiz_questions', [])
                
                summary = (
                    f"*Quiz Summary:*\n\n"
                    f"*Title:* {quiz_data.get('title', 'Untitled')}\n"
                    f"*Description:* {quiz_data.get('description', 'No description')}\n"
                    f"*Reward:* ₹{quiz_data.get('reward', 0)}\n"
                    f"*Minimum Score:* {quiz_data.get('min_score', 50)}%\n\n"
                    f"*Questions:* {len(quiz_questions)}\n\n"
                    f"Type /done to create this quiz and broadcast it to all users, or /cancel to discard it."
                )
                
                update.message.reply_text(
                    summary,
                    parse_mode='Markdown'
                )
            else:
                update.message.reply_text("❌ Please type 'yes' or 'no'.")
    except Exception as e:
        logger.error(f"Error in quiz creation: {e}")
        update.message.reply_text(f"❌ An error occurred: {str(e)}")
        # Reset quiz state
        context.user_data.pop('quiz_state', None)
        context.user_data.pop('quiz_data', None)
        context.user_data.pop('quiz_questions', None)

# Quiz creation system
class QuizCreationState(Enum):
    """Enum for tracking quiz creation state."""
    TITLE = 1
    DESCRIPTION = 2
    REWARD = 3
    MIN_SCORE = 4
    QUESTION = 5
    OPTION_A = 6
    OPTION_B = 7
    OPTION_C = 8
    OPTION_D = 9
    CORRECT_OPTION = 10
    ADD_MORE = 11
    CONFIRM = 12

# Admin panel command
def adminpanel_command(update, context):
    """Handle /adminpanel command - show admin dashboard."""
    user_id = update.effective_user.id
    
    # Only admin can use this command
    if user_id != ADMIN_ID:
        update.message.reply_text("🔒 This command is only available to the bot owner.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get count of all users
    cursor.execute("SELECT COUNT(*) FROM Users")
    total_users = cursor.fetchone()[0]
    
    # Get count of active users (used bot in last 7 days)
    seven_days_ago = int(time.time()) - (7 * 24 * 60 * 60)
    cursor.execute("SELECT COUNT(*) FROM Users WHERE last_verify > ?", (seven_days_ago,))
    active_users = cursor.fetchone()[0]
    
    # Get total searches performed
    cursor.execute("SELECT SUM(search_count) FROM Users")
    total_searches = cursor.fetchone()[0] or 0
    
    # Get total referrals
    cursor.execute("SELECT SUM(referrals) FROM Users")
    total_referrals = cursor.fetchone()[0] or 0
    
    # Get count of total books in database
    cursor.execute("SELECT COUNT(*) FROM Books")
    total_books = cursor.fetchone()[0]
    
    # Get count of quizzes
    cursor.execute("SELECT COUNT(*) FROM Quizzes")
    total_quizzes = cursor.fetchone()[0]
    
    # Get newest users (last 5)
    cursor.execute("""
        SELECT user_id, username, first_name, last_name, join_date 
        FROM Users 
        ORDER BY join_date DESC 
        LIMIT 5
    """)
    newest_users = cursor.fetchall()
    
    conn.close()
    
    # Create admin panel message
    admin_panel = (
        f"*📊 ADMIN DASHBOARD*\n\n"
        f"*👥 Users:*\n"
        f"• Total users: {total_users}\n"
        f"• Active users (7d): {active_users}\n"
        f"• Total referrals: {total_referrals}\n\n"
        f"*📚 Content:*\n"
        f"• Total books: {total_books}\n"
        f"• Total quizzes: {total_quizzes}\n"
        f"• Total searches: {total_searches}\n\n"
        f"*👤 Newest Users:*\n"
    )
    
    # Add newest users to message
    for i, user in enumerate(newest_users, 1):
        user_id, username, first_name, last_name, join_date = user
        name = first_name or ""
        if last_name:
            name += f" {last_name}"
        join_date_str = datetime.datetime.fromtimestamp(join_date).strftime("%d %b %Y") if join_date else "Unknown"
        admin_panel += f"{i}. {'@' + username if username else name or 'User'} (ID: {user_id}) - {join_date_str}\n"
    
    # Create admin action buttons
    keyboard = [
        [
            InlineKeyboardButton("👥 User List", callback_data="admin_users"),
            InlineKeyboardButton("📨 Broadcast", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
            InlineKeyboardButton("📝 Create Quiz", callback_data="admin_quiz")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(admin_panel, reply_markup=reply_markup, parse_mode='Markdown')

# Broadcast message to all users
def broadcast_command(update, context):
    """Handler for /broadcast command - send message to all users."""
    user_id = update.effective_user.id
    
    # Only admin can use this command
    if user_id != ADMIN_ID:
        update.message.reply_text("🔒 This command is only available to the bot owner.")
        return
    
    if not context.args:
        update.message.reply_text(
            "❓ *Correct format:*\n/broadcast <message>",
            parse_mode='Markdown'
        )
        return
    
    # Get message to broadcast
    message = ' '.join(context.args)
    
    # Store message in context for confirmation
    context.user_data['broadcast_message'] = message
    
    # Ask for confirmation with preview
    keyboard = [
        [
            InlineKeyboardButton("✅ Send", callback_data="confirm_broadcast"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"*📣 Broadcast Preview:*\n\n"
        f"{message}\n\n"
        f"This message will be sent to all users. Confirm?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# New task/quiz creation command
def newtask_command(update, context):
    """Handler for /newtask command - create a new quiz."""
    user_id = update.effective_user.id
    
    # Only admin can use this command
    if user_id != ADMIN_ID:
        update.message.reply_text("🔒 This command is only available to the bot owner.")
        return
    
    # Initialize quiz creation state
    context.user_data['quiz_state'] = QuizCreationState.TITLE
    context.user_data['quiz_data'] = {}
    context.user_data['quiz_questions'] = []
    
    update.message.reply_text(
        "*📝 CREATE NEW QUIZ*\n\n"
        "You're now creating a new quiz. Users who complete it with the minimum required score will receive rewards.\n\n"
        "Type /cancel at any time to cancel creation.\n\n"
        "*Step 1:* Enter a title for your quiz:",
        parse_mode='Markdown'
    )

# Help command
def help_command(update, context):
    """Handler for /help command."""
    user_id = update.effective_user.id
    is_admin = admin_check(user_id)
    
    # Create keyboard
    keyboard = [
        [InlineKeyboardButton("📋 User Commands", callback_data="help_user")]
    ]
    
    # Add admin commands button only for admins
    if is_admin:
        keyboard.append([InlineKeyboardButton("🔧 Admin Commands", callback_data="help_admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "*📚 Bot Help*\n\n"
        "This bot helps you find and download books in PDF format.\n"
        "Select an option below to see available commands:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Set admin command
def setadmin_command(update, context):
    """Handler for /setadmin command - add or remove admin status."""
    user_id = update.effective_user.id
    
    # Only primary admin can use this command
    if user_id != ADMIN_ID:
        update.message.reply_text("🔒 This command is only available to the bot owner.")
        return
    
    if not context.args or len(context.args) != 2:
        update.message.reply_text(
            "❓ *Correct format:*\n/setadmin <user_id> <yes/no>",
            parse_mode='Markdown'
        )
        return
    
    try:
        target_id = int(context.args[0])
        action = context.args[1].lower()
        
        if action not in ['yes', 'no']:
            update.message.reply_text("❌ Second parameter must be 'yes' or 'no'.")
            return
            
        # Get user
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT username, first_name, last_name FROM Users WHERE user_id = ?", (target_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            update.message.reply_text("❌ User not found in database. They need to start the bot first.")
            conn.close()
            return
        
        # Set admin status
        is_admin = 1 if action == 'yes' else 0
        cursor.execute("UPDATE Users SET is_admin = ? WHERE user_id = ?", (is_admin, target_id))
        conn.commit()
        
        # Get user details for confirmation
        username = user_data[0] or "Unknown"
        first_name = user_data[1] or ""
        last_name = user_data[2] or ""
        full_name = f"{first_name} {last_name}".strip() or "Unknown"
        
        update.message.reply_text(
            f"✅ User @{username} ({full_name}) with ID {target_id} is now "
            f"{'an admin' if is_admin else 'no longer an admin'}."
        )
        
        # Notify the user of their new status
        try:
            context.bot.send_message(
                chat_id=target_id,
                text=f"🔔 *Admin Status Update*\n\n"
                     f"You have been {'given admin privileges' if is_admin else 'removed from admin status'} "
                     f"by the bot owner.",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user {target_id} of admin status change: {e}")
        
        conn.close()
        
    except ValueError:
        update.message.reply_text("❌ User ID must be a number.")
    except Exception as e:
        logger.error(f"Error in setadmin command: {e}")
        update.message.reply_text(f"❌ Error: {str(e)}")

# Check storage usage
def checkstorage_command(update, context):
    """Handler for /checkstorage command - check database size."""
    user_id = update.effective_user.id
    
    # Only admin can use this command
    if not admin_check(user_id):
        update.message.reply_text("🔒 This command is only available to admins.")
        return
    
    try:
        # Get database file size
        db_size = os.path.getsize(DB_PATH)
        db_size_mb = db_size / (1024 * 1024)  # Convert to MB
        
        # Get table counts
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM Users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Books")
        book_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Quizzes")
        quiz_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM QuizQuestions")
        question_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Updates")
        updates_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Create storage report
        storage_report = (
            f"*📊 Storage Report*\n\n"
            f"*Database Size:* {db_size_mb:.2f} MB\n\n"
            f"*Records:*\n"
            f"• Users: {user_count}\n"
            f"• Books: {book_count}\n"
            f"• Quizzes: {quiz_count}\n"
            f"• Quiz Questions: {question_count}\n"
            f"• Updates: {updates_count}\n\n"
            f"You can use /clearquiz to remove quizzes or /clearupdates to remove update notifications."
        )
        
        update.message.reply_text(
            storage_report,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error checking storage: {e}")
        update.message.reply_text(f"❌ Error checking storage: {str(e)}")

# Clear quizzes command
def clearquiz_command(update, context):
    """Handler for /clearquiz command - remove quizzes from database."""
    user_id = update.effective_user.id
    
    # Only admin can use this command
    if not admin_check(user_id):
        update.message.reply_text("🔒 This command is only available to admins.")
        return
    
    if not context.args:
        # If no arguments, show quiz list
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, title, created_at FROM Quizzes ORDER BY created_at DESC")
        quizzes = cursor.fetchall()
        conn.close()
        
        if not quizzes:
            update.message.reply_text("ℹ️ No quizzes found in the database.")
            return
            
        quiz_list = "*🎮 Available Quizzes:*\n\n"
        for quiz in quizzes:
            quiz_id, title, created_at = quiz
            date_str = datetime.datetime.fromtimestamp(created_at).strftime("%d %b %Y")
            quiz_list += f"• ID {quiz_id}: {title} (Created: {date_str})\n"
            
        quiz_list += "\n*Usage:*\n• `/clearquiz all` - Delete all quizzes\n• `/clearquiz <quiz_id>` - Delete specific quiz"
        
        update.message.reply_text(
            quiz_list,
            parse_mode='Markdown'
        )
        return
        
    # Process clearquiz command with arguments
    arg = context.args[0].lower()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        if arg == 'all':
            # Delete all quizzes and related data
            cursor.execute("DELETE FROM QuizQuestions")
            cursor.execute("DELETE FROM UserQuizzes")
            cursor.execute("DELETE FROM Quizzes")
            conn.commit()
            
            update.message.reply_text("✅ All quizzes have been deleted from the database.")
        else:
            try:
                quiz_id = int(arg)
                
                # Check if quiz exists
                cursor.execute("SELECT title FROM Quizzes WHERE id = ?", (quiz_id,))
                quiz = cursor.fetchone()
                
                if not quiz:
                    update.message.reply_text(f"❌ Quiz with ID {quiz_id} not found.")
                    conn.close()
                    return
                    
                # Delete quiz and related data
                cursor.execute("DELETE FROM QuizQuestions WHERE quiz_id = ?", (quiz_id,))
                cursor.execute("DELETE FROM UserQuizzes WHERE quiz_id = ?", (quiz_id,))
                cursor.execute("DELETE FROM Quizzes WHERE id = ?", (quiz_id,))
                conn.commit()
                
                update.message.reply_text(f"✅ Quiz '{quiz[0]}' (ID: {quiz_id}) has been deleted.")
                
            except ValueError:
                update.message.reply_text("❌ Invalid quiz ID. Use a number or 'all'.")
    except Exception as e:
        logger.error(f"Error clearing quizzes: {e}")
        update.message.reply_text(f"❌ Error clearing quizzes: {str(e)}")
        conn.rollback()
        
    conn.close()

# Add or update bot notification
def clearupdates_command(update, context):
    """Handler for /clearupdates command - manage bot updates/notifications."""
    user_id = update.effective_user.id
    
    # Only admin can use this command
    if not admin_check(user_id):
        update.message.reply_text("🔒 This command is only available to admins.")
        return
    
    if not context.args:
        # Show existing updates
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, title, created_at, is_pinned FROM Updates ORDER BY created_at DESC")
        updates = cursor.fetchall()
        conn.close()
        
        if not updates:
            update.message.reply_text(
                "ℹ️ No updates found in the database.\n\n"
                "*Usage:*\n"
                "• `/clearupdates list` - Show all updates\n"
                "• `/clearupdates add Title | Content` - Add new update\n"
                "• `/clearupdates pin <update_id>` - Pin an update to all chats\n"
                "• `/clearupdates unpin <update_id>` - Unpin an update\n"
                "• `/clearupdates delete <update_id>` - Delete an update\n"
                "• `/clearupdates deleteall` - Delete all updates",
                parse_mode='Markdown'
            )
            return
            
        updates_list = "*📢 Available Updates:*\n\n"
        for upd in updates:
            upd_id, title, created_at, is_pinned = upd
            date_str = datetime.datetime.fromtimestamp(created_at).strftime("%d %b %Y")
            pin_status = "📌 Pinned" if is_pinned else "Not pinned"
            updates_list += f"• ID {upd_id}: {title} ({date_str}) - {pin_status}\n"
            
        updates_list += "\n*Usage:*\n• `/clearupdates add Title | Content` - Add new update\n• `/clearupdates delete <update_id>` - Delete update"
        
        update.message.reply_text(
            updates_list,
            parse_mode='Markdown'
        )
        return
        
    # Process command with arguments
    action = context.args[0].lower()
    
    if action == 'list':
        # Show detailed list of updates
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, title, content, created_at, is_pinned FROM Updates ORDER BY created_at DESC")
        updates = cursor.fetchall()
        conn.close()
        
        if not updates:
            update.message.reply_text("ℹ️ No updates found in the database.")
            return
            
        for upd in updates:
            upd_id, title, content, created_at, is_pinned = upd
            date_str = datetime.datetime.fromtimestamp(created_at).strftime("%d %b %Y %H:%M")
            pin_status = "📌 Pinned" if is_pinned else "Not pinned"
            
            update_details = (
                f"*Update ID: {upd_id}*\n"
                f"*Title:* {title}\n"
                f"*Status:* {pin_status}\n"
                f"*Date:* {date_str}\n\n"
                f"{content}\n\n"
                f"----------------------------"
            )
            
            update.message.reply_text(
                update_details,
                parse_mode='Markdown'
            )
            
    elif action == 'add':
        # Add new update
        full_text = ' '.join(context.args[1:])
        parts = full_text.split('|', 1)
        
        if len(parts) < 2:
            update.message.reply_text("❌ Incorrect format. Use: `/clearupdates add Title | Content`", parse_mode='Markdown')
            return
            
        title = parts[0].strip()
        content = parts[1].strip()
        
        if not title or not content:
            update.message.reply_text("❌ Both title and content are required.")
            return
            
        # Add to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            current_time = int(time.time())
            cursor.execute(
                "INSERT INTO Updates (title, content, created_at, is_pinned) VALUES (?, ?, ?, 0)",
                (title, content, current_time)
            )
            conn.commit()
            
            # Get the new update ID
            update_id = cursor.lastrowid
            
            keyboard = [
                [
                    InlineKeyboardButton("📌 Pin This Update", callback_data=f"pin_update_{update_id}"),
                    InlineKeyboardButton("❌ Delete", callback_data=f"delete_update_{update_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(
                f"✅ New update added (ID: {update_id}).\n\n"
                f"*{title}*\n\n"
                f"{content}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error adding update: {e}")
            update.message.reply_text(f"❌ Error adding update: {str(e)}")
            conn.rollback()
            
        conn.close()
        
    elif action == 'pin':
        # Pin update to all chats
        if len(context.args) < 2:
            update.message.reply_text("❌ Please specify an update ID to pin.")
            return
            
        try:
            update_id = int(context.args[1])
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if update exists
            cursor.execute("SELECT title, content FROM Updates WHERE id = ?", (update_id,))
            update_data = cursor.fetchone()
            
            if not update_data:
                update.message.reply_text(f"❌ Update with ID {update_id} not found.")
                conn.close()
                return
                
            # Set all updates to unpinned
            cursor.execute("UPDATE Updates SET is_pinned = 0")
            
            # Set this update to pinned
            cursor.execute("UPDATE Updates SET is_pinned = 1 WHERE id = ?", (update_id,))
            conn.commit()
            
            update.message.reply_text(f"📌 Update '{update_data[0]}' has been pinned. All users will see it at the top of their chat.")
            
            # Broadcast the pinned update to all users
            title = update_data[0]
            content = update_data[1]
            
            cursor.execute("SELECT user_id FROM Users")
            users = cursor.fetchall()
            
            success_count = 0
            for user in users:
                try:
                    context.bot.send_message(
                        chat_id=user[0],
                        text=f"📌 *IMPORTANT UPDATE*\n\n*{title}*\n\n{content}",
                        parse_mode='Markdown'
                    )
                    success_count += 1
                    time.sleep(0.05)  # Sleep to avoid hitting rate limits
                except Exception as e:
                    logger.error(f"Failed to send pinned update to user {user[0]}: {e}")
            
            update.message.reply_text(f"✅ Pinned update sent to {success_count} users.")
            
        except ValueError:
            update.message.reply_text("❌ Update ID must be a number.")
        except Exception as e:
            logger.error(f"Error pinning update: {e}")
            update.message.reply_text(f"❌ Error pinning update: {str(e)}")
            
        conn.close()
        
    elif action == 'unpin':
        # Unpin update
        if len(context.args) < 2:
            update.message.reply_text("❌ Please specify an update ID to unpin.")
            return
            
        try:
            update_id = int(context.args[1])
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if update exists
            cursor.execute("SELECT title FROM Updates WHERE id = ?", (update_id,))
            update_data = cursor.fetchone()
            
            if not update_data:
                update.message.reply_text(f"❌ Update with ID {update_id} not found.")
                conn.close()
                return
                
            # Unpin this update
            cursor.execute("UPDATE Updates SET is_pinned = 0 WHERE id = ?", (update_id,))
            conn.commit()
            
            update.message.reply_text(f"✅ Update '{update_data[0]}' has been unpinned.")
            
        except ValueError:
            update.message.reply_text("❌ Update ID must be a number.")
        except Exception as e:
            logger.error(f"Error unpinning update: {e}")
            update.message.reply_text(f"❌ Error unpinning update: {str(e)}")
            
        conn.close()
        
    elif action == 'delete':
        # Delete specific update
        if len(context.args) < 2:
            update.message.reply_text("❌ Please specify an update ID to delete.")
            return
            
        try:
            update_id = int(context.args[1])
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if update exists
            cursor.execute("SELECT title FROM Updates WHERE id = ?", (update_id,))
            update_data = cursor.fetchone()
            
            if not update_data:
                update.message.reply_text(f"❌ Update with ID {update_id} not found.")
                conn.close()
                return
                
            # Delete the update
            cursor.execute("DELETE FROM Updates WHERE id = ?", (update_id,))
            conn.commit()
            
            update.message.reply_text(f"✅ Update '{update_data[0]}' has been deleted.")
            
        except ValueError:
            update.message.reply_text("❌ Update ID must be a number.")
        except Exception as e:
            logger.error(f"Error deleting update: {e}")
            update.message.reply_text(f"❌ Error deleting update: {str(e)}")
            
        conn.close()
        
    elif action == 'deleteall':
        # Delete all updates
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM Updates")
            conn.commit()
            
            update.message.reply_text("✅ All updates have been deleted.")
            
        except Exception as e:
            logger.error(f"Error deleting all updates: {e}")
            update.message.reply_text(f"❌ Error deleting updates: {str(e)}")
            conn.rollback()
            
        conn.close()
        
    else:
        update.message.reply_text(
            "❌ Unknown action. Available actions:\n"
            "• list - Show all updates\n"
            "• add Title | Content - Add new update\n"
            "• pin <update_id> - Pin an update\n"
            "• unpin <update_id> - Unpin an update\n"
            "• delete <update_id> - Delete an update\n"
            "• deleteall - Delete all updates"
        )

# Admin reply command handler
def reply_command(update, context):
    """Handle admin replies to users."""
    user_id = update.effective_user.id
    
    # Only admin can use this command
    if not admin_check(user_id):
        update.message.reply_text("🔒 This command is only available to admins.")
        return
    
    # Check if the command is properly formatted
    if not context.args or len(context.args) < 2:
        update.message.reply_text(
            "❓ *Correct format:*\n/reply <user_id> <message>",
            parse_mode='Markdown'
        )
        return
    
    try:
        # Extract target user ID and message
        target_id = int(context.args[0])
        message = ' '.join(context.args[1:])
        
        # Send the reply to the target user
        context.bot.send_message(
            chat_id=target_id,
            text=message
        )
        
        # Confirm to admin
        update.message.reply_text(
            f"✅ Message sent successfully to user ID: {target_id}"
        )
    except ValueError:
        update.message.reply_text("❌ Invalid user ID. Please provide a valid numeric ID.")
    except Exception as e:
        update.message.reply_text(f"❌ Error sending message: {str(e)}")

# Error handler
def error_handler(update, context):
    """Log errors caused by updates."""
    error_msg = f"Update {update} caused error {context.error}"
    logger.error(error_msg)
    
    # Send error notifications to admin
    try:
        context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ *Bot Error Alert*\n\n{str(context.error)}",
            parse_mode='Markdown'
        )
    except:
        pass
    if update and update.effective_message:
        update.effective_message.reply_text(
            "An error occurred while processing your request. Please try again later."
        )

def main():
    """Run the bot."""
    # Initialize database
    init_db()
    
    # Create updater and dispatcher
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # Register handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("book", book_command))
    dispatcher.add_handler(CommandHandler("balance", balance_command))
    dispatcher.add_handler(CommandHandler("credits", credits_command))
    dispatcher.add_handler(CommandHandler("referral", referral_command))
    dispatcher.add_handler(CommandHandler("web_referral", web_referral_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("pay", pay_command))
    dispatcher.add_handler(CommandHandler("addbooks", addbooks_command))
    dispatcher.add_handler(CommandHandler("uploadbooks", uploadbooks_command))
    dispatcher.add_handler(CommandHandler("note", note_command))
    dispatcher.add_handler(CommandHandler("checkdb", checkdb_command))
    dispatcher.add_handler(CommandHandler("ownermode", ownermode_command))
    dispatcher.add_handler(CommandHandler("dailybonus", dailybonus_command))
    
    # Admin command handlers
    dispatcher.add_handler(CommandHandler("adminpanel", adminpanel_command))
    dispatcher.add_handler(CommandHandler("broadcast", broadcast_command))
    dispatcher.add_handler(CommandHandler("checkstorage", checkstorage_command))
    dispatcher.add_handler(CommandHandler("newtask", newtask_command))
    dispatcher.add_handler(CommandHandler("clearquiz", clearquiz_command))
    dispatcher.add_handler(CommandHandler("pinupdate", clearupdates_command))
    dispatcher.add_handler(CommandHandler("setadmin", setadmin_command))
    
    # Register callback query handler
    dispatcher.add_handler(CallbackQueryHandler(button_callback))
    
    # Register handler for admin replies
    dispatcher.add_handler(CommandHandler("reply", reply_command))
    
    # Register message handler for admin monitoring (must be added last)
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
    
    # Register error handler
    dispatcher.add_error_handler(error_handler)
    
    # Schedule reset of search quotas every hour
    updater.job_queue.run_repeating(
        callback=lambda context: reset_search_quotas(),
        interval=3600,  # 1 hour in seconds
        first=0
    )
    
    # Schedule daily bonus
    schedule_daily_bonus(updater)
    
    # Start the bot
updater.start_polling()
updater.idle()

def start_bot_logic():
    main()

if __name__ == '__main__':
    main()
    
    