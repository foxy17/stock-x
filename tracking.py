import requests
from bs4 import BeautifulSoup
import datetime
import logging
import hashlib
import sqlite3
import json
import os
import random # Keep for now, might not be needed with SB UC
import time # Keep for potential waits if needed

# Import SeleniumBase
from seleniumbase import Driver
# Removed selenium-wire/uc imports
# import seleniumwire.undetected_chromedriver as uc
# from selenium.webdriver.chrome.options import Options
# Removed Selenium exceptions, SB might handle differently or raise its own
# from selenium.common.exceptions import WebDriverException, TimeoutException

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants for persistent storage
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # Get the directory of the current script
DATABASE_FILE = os.path.join(SCRIPT_DIR, 'seen_items.db') # SQLite database file
MAX_STORED_IDENTIFIERS = 100
# In-memory cache for recent identifiers (keep more in memory for faster lookups)
MEMORY_CACHE_SIZE = 500

# Browser session management
persistent_browser = None
browser_refresh_counter = 0
MAX_BROWSER_REUSES = 20  # Refresh browser after 20 uses

# --- Database Functions ---

def init_database(db_path=DATABASE_FILE):
    """Initialize the SQLite database and create the items table if it doesn't exist."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create table with unique constraint on identifier only
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seen_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                title TEXT,
                description TEXT,
                link TEXT,
                identifier TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create composite index on timestamp and identifier for faster lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp_identifier ON seen_items(timestamp DESC, identifier)')
        
        # Create individual index on identifier for unique lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_identifier ON seen_items(identifier)')
        
        # Create index on created_at for cleanup operations
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON seen_items(created_at DESC)')
        
        conn.commit()
        conn.close()
        logging.info(f"Database initialized with optimized indexes at: {os.path.abspath(db_path)}")
    except sqlite3.Error as e:
        logging.error(f"Error initializing database: {e}")

def load_seen_items(db_path=DATABASE_FILE):
    """Loads seen item dictionaries from SQLite database with optimized in-memory caching."""
    abs_db_path = os.path.abspath(db_path)
    logging.info(f"Attempting to load seen items from: {abs_db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all items ordered by creation time (most recent first)
        cursor.execute('''
            SELECT timestamp, title, description, link, identifier 
            FROM seen_items 
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to the same format as before
        item_objects_list = []
        # Use set for O(1) lookup, but limit size for memory efficiency
        identifiers_set = set()
        
        for row in rows:
            timestamp, title, description, link, identifier = row
            item_object = {
                "timestamp": timestamp,
                "title": title,
                "description": description,
                "link": link,
                "identifier": identifier
            }
            item_objects_list.append(item_object)
            
            # Only keep recent identifiers in memory cache for faster lookups
            if len(identifiers_set) < MEMORY_CACHE_SIZE:
                identifiers_set.add(identifier)
        
        logging.info(f"Loaded {len(item_objects_list)} items with {len(identifiers_set)} identifiers cached in memory from {abs_db_path}")
        return item_objects_list, identifiers_set
        
    except sqlite3.Error as e:
        logging.error(f"Error loading seen items from {abs_db_path}: {e}. Starting fresh.")
        return [], set()

def save_seen_items(item_objects_list, db_path=DATABASE_FILE, max_items=MAX_STORED_IDENTIFIERS):
    """Saves seen item dictionaries to SQLite database, keeping only the most recent ones."""
    abs_db_path = os.path.abspath(db_path)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Clean up old items if we exceed max_items
        cursor.execute('SELECT COUNT(*) FROM seen_items')
        current_count = cursor.fetchone()[0]
        
        if current_count > max_items:
            # Keep only the most recent max_items
            cursor.execute('''
                DELETE FROM seen_items 
                WHERE id NOT IN (
                    SELECT id FROM seen_items 
                    ORDER BY created_at DESC 
                    LIMIT ?
                )
            ''', (max_items,))
            
            deleted_count = cursor.rowcount
            logging.info(f"Trimmed seen items storage by removing {deleted_count} old items. Keeping {max_items} most recent items.")
        
        conn.commit()
        conn.close()
        
    except sqlite3.Error as e:
        logging.error(f"Error trimming seen items in {abs_db_path}: {e}")

def add_new_item(item_object, db_path=DATABASE_FILE):
    """Add a single new item to the SQLite database."""
    abs_db_path = os.path.abspath(db_path)
    logging.info(f"Attempting to add new item to database: {abs_db_path}")
    logging.debug(f"Item details: {item_object['title'][:50]}... (ID: {item_object['identifier'][:20]}...)")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if item already exists first
        cursor.execute('SELECT COUNT(*) FROM seen_items WHERE identifier = ?', (item_object['identifier'],))
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            logging.debug(f"Item already exists in database (duplicate identifier): {item_object['title'][:50]}...")
            conn.close()
            return False
        
        # Insert the new item
        cursor.execute('''
            INSERT INTO seen_items (timestamp, title, description, link, identifier)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            item_object['timestamp'],
            item_object['title'], 
            item_object['description'],
            item_object['link'],
            item_object['identifier']
        ))
        
        if cursor.rowcount > 0:
            logging.info(f"✓ Successfully added new item to database: {item_object['title'][:50]}...")
            conn.commit()
            conn.close()
            return True
        else:
            logging.warning(f"✗ Failed to add item to database (no rows affected): {item_object['title'][:50]}...")
            conn.close()
            return False
        
    except sqlite3.Error as e:
        logging.error(f"✗ Database error adding item: {e}")
        return False

def batch_add_new_items(item_objects_list, db_path=DATABASE_FILE):
    """Batch insert multiple new items to SQLite database for better performance."""
    if not item_objects_list:
        return []
    
    abs_db_path = os.path.abspath(db_path)
    logging.info(f"Attempting to batch add {len(item_objects_list)} items to database: {abs_db_path}")
    
    successful_items = []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First, get ALL identifiers from the items we want to add
        identifiers_to_check = [item['identifier'] for item in item_objects_list]
        
        # Remove duplicates within the batch itself
        unique_identifiers = []
        seen_in_batch = set()
        unique_items = []
        
        for item in item_objects_list:
            if item['identifier'] not in seen_in_batch:
                unique_identifiers.append(item['identifier'])
                unique_items.append(item)
                seen_in_batch.add(item['identifier'])
            else:
                logging.debug(f"Duplicate within batch: {item['title'][:50]}...")
        
        logging.info(f"After removing batch duplicates: {len(unique_items)} unique items")
        
        # Batch check which identifiers already exist in database
        existing_identifiers = set()
        if unique_identifiers:
            # Split into chunks to avoid SQL query limits
            chunk_size = 500  # SQLite variable limit is typically 999
            for i in range(0, len(unique_identifiers), chunk_size):
                chunk = unique_identifiers[i:i+chunk_size]
                placeholders = ','.join('?' * len(chunk))
                cursor.execute(f'SELECT identifier FROM seen_items WHERE identifier IN ({placeholders})', chunk)
                existing_identifiers.update(row[0] for row in cursor.fetchall())
        
        # Prepare data for items that truly don't exist
        batch_data = []
        items_to_add = []
        
        for item_object in unique_items:
            if item_object['identifier'] not in existing_identifiers:
                batch_data.append((
                    item_object['timestamp'],
                    item_object['title'],
                    item_object['description'],
                    item_object['link'],
                    item_object['identifier']
                ))
                items_to_add.append(item_object)
            else:
                logging.debug(f"Skipping database duplicate: {item_object['title'][:50]}...")
        
        logging.info(f"After removing database duplicates: {len(items_to_add)} items to insert")
        
        # Batch insert all new items
        if batch_data:
            try:
                cursor.executemany('''
                    INSERT INTO seen_items (timestamp, title, description, link, identifier)
                    VALUES (?, ?, ?, ?, ?)
                ''', batch_data)
                
                rows_inserted = cursor.rowcount
                conn.commit()
                
                if rows_inserted > 0:
                    logging.info(f"✓ Successfully batch inserted {rows_inserted} new items to database")
                    successful_items = items_to_add
                else:
                    logging.warning(f"✗ Batch insert failed - no rows affected")
                    
            except sqlite3.IntegrityError as e:
                # Handle any remaining unique constraint violations gracefully
                logging.warning(f"Integrity error during batch insert (some duplicates may exist): {e}")
                # Fall back to individual inserts for the problematic batch
                conn.rollback()
                successful_items = []
                
                for item_data, item_object in zip(batch_data, items_to_add):
                    try:
                        cursor.execute('''
                            INSERT INTO seen_items (timestamp, title, description, link, identifier)
                            VALUES (?, ?, ?, ?, ?)
                        ''', item_data)
                        successful_items.append(item_object)
                    except sqlite3.IntegrityError:
                        logging.debug(f"Skipping duplicate item in fallback: {item_object['title'][:50]}...")
                        continue
                
                if successful_items:
                    conn.commit()
                    logging.info(f"✓ Fallback individual inserts: {len(successful_items)} items added")
                    
        else:
            logging.info("No new items to insert - all were duplicates")
        
        conn.close()
        
    except sqlite3.Error as e:
        logging.error(f"✗ Database error during batch insert: {e}")
        
    return successful_items

def check_identifier_exists(identifier, db_path=DATABASE_FILE):
    """Check if identifier exists in database (used for cache misses)."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM seen_items WHERE identifier = ?', (identifier,))
        exists = cursor.fetchone()[0] > 0
        conn.close()
        return exists
    except sqlite3.Error as e:
        logging.error(f"Error checking identifier existence: {e}")
        return False

def update_memory_cache(new_identifiers):
    """Update the in-memory cache with new identifiers, maintaining size limit."""
    global seen_item_identifiers_set
    
    # Add new identifiers to cache
    for identifier in new_identifiers:
        seen_item_identifiers_set.add(identifier)
    
    # If cache is too large, remove oldest identifiers
    # Note: In practice, you might want to implement LRU cache or use a proper cache library
    if len(seen_item_identifiers_set) > MEMORY_CACHE_SIZE:
        # Convert to list, sort, and keep most recent
        # This is a simple implementation; for better performance, consider using collections.OrderedDict
        excess_count = len(seen_item_identifiers_set) - MEMORY_CACHE_SIZE
        identifiers_list = list(seen_item_identifiers_set)
        # Remove first N items (oldest in insertion order - not perfect but acceptable)
        for i in range(excess_count):
            seen_item_identifiers_set.discard(identifiers_list[i])
        
        logging.debug(f"Trimmed memory cache, now contains {len(seen_item_identifiers_set)} identifiers")

# --- End Database Functions ---

# --- Browser Session Management ---

def initialize_persistent_browser():
    """Initialize a persistent SeleniumBase browser session."""
    global persistent_browser, browser_refresh_counter
    
    try:
        # Close existing browser if any
        cleanup_persistent_browser()
        
        # Randomly select a user agent for this session
        selected_agent = random.choice(USER_AGENTS)
        logging.info(f"Initializing persistent browser with User-Agent: {selected_agent}")
        
        # Create new browser session (not using context manager)
        persistent_browser = Driver(uc=True, headless=True, agent=selected_agent)
        
        # Driver automatically initializes - no need for setUp()
        
        browser_refresh_counter = 0
        logging.info("✓ Persistent browser session initialized successfully")
        return True
        
    except Exception as e:
        logging.error(f"✗ Failed to initialize persistent browser: {e}")
        persistent_browser = None
        return False

def cleanup_persistent_browser():
    """Clean up the persistent browser session."""
    global persistent_browser
    
    if persistent_browser:
        try:
            persistent_browser.quit()
            logging.info("✓ Persistent browser session closed")
        except Exception as e:
            logging.warning(f"Warning during browser cleanup: {e}")
        finally:
            persistent_browser = None

def should_refresh_browser():
    """Check if browser should be refreshed based on usage count."""
    global browser_refresh_counter
    return browser_refresh_counter >= MAX_BROWSER_REUSES

def get_persistent_browser():
    """Get the persistent browser, initializing or refreshing if needed."""
    global persistent_browser, browser_refresh_counter
    
    # Initialize browser if it doesn't exist
    if persistent_browser is None:
        if not initialize_persistent_browser():
            return None
    
    # Refresh browser if it's been used too many times
    elif should_refresh_browser():
        logging.info(f"Browser has been used {browser_refresh_counter} times. Refreshing session...")
        if not initialize_persistent_browser():
            return None
    
    return persistent_browser

# --- End Browser Session Management ---

# Initialize database on module load
init_database()
logging.info(f"Database file path: {os.path.abspath(DATABASE_FILE)}")

# Load seen items on module initialization
seen_item_objects_list, seen_item_identifiers_set = load_seen_items()
logging.info(f"Module initialization complete. Loaded {len(seen_item_objects_list)} items, {len(seen_item_identifiers_set)} unique identifiers")

# Define User Agents - Keep for now, SB UC might handle this or we might re-add if needed
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36", # Updated to a more recent common one
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

def get_initial_items():
    """Returns the list of item objects loaded at startup."""
    global seen_item_objects_list, seen_item_identifiers_set
    
    # If in-memory list is empty, reload from database
    if not seen_item_objects_list:
        logging.warning("In-memory item list is empty, reloading from database...")
        seen_item_objects_list, seen_item_identifiers_set = load_seen_items()
    
    logging.info(f"Returning {len(seen_item_objects_list)} items from get_initial_items()")
    # Return a copy to prevent external modification of the original list
    return list(seen_item_objects_list)

def fetch_content(url):
    """Fetches XML content using persistent SeleniumBase browser session."""
    global browser_refresh_counter
    
    xml_content = None
    logging.info(f"Fetching content from: {url} (browser usage: {browser_refresh_counter + 1}/{MAX_BROWSER_REUSES})")

    try:
        # Get persistent browser instance
        browser = get_persistent_browser()
        if not browser:
            logging.error("Failed to get persistent browser instance")
            return None
        
        # Navigate to URL using persistent browser
        logging.info(f"Navigating to: {url}")
        browser.open(url)
        
        # Increment usage counter
        browser_refresh_counter += 1
        
        # Get page source
        xml_content = browser.get_page_source()

        # Optional: Basic check if it looks like a challenge page
        if xml_content and ("challenge-page" in browser.get_current_url() or "Just a moment..." in xml_content):
            logging.warning(f"Page source might contain challenge elements for {url}. Content may be invalid.")
            # Could implement retry logic here if needed

        if xml_content:
            logging.info(f"✓ Successfully fetched page source for {url} (session usage: {browser_refresh_counter}/{MAX_BROWSER_REUSES})")
        else:
            logging.warning(f"✗ Fetched page source for {url} is empty")

    except Exception as e:
        logging.error(f"✗ Error during persistent browser operation for {url}: {e}", exc_info=True)
        
        # On error, try to reinitialize browser for next attempt
        logging.info("Attempting to reinitialize browser due to error...")
        cleanup_persistent_browser()
        browser_refresh_counter = 0

    return xml_content

def get_new_items(url):
    """Fetches XML, parses it, and returns a list of new items with optimized processing."""
    xml_content = fetch_content(url)
    if not xml_content:
        logging.warning(f"fetch_content returned no data for {url}. Skipping parsing.")
        return []

    new_items_found = []
    potential_new_items = []
    consecutive_known_items = 0
    max_consecutive_known = 10  # Stop after 10 consecutive known items (assuming chronological order)
    
    try:
        # Use 'lxml-xml' for potentially stricter XML parsing
        soup = BeautifulSoup(xml_content, 'lxml-xml') 

        items = soup.find_all('item')
        if not items:
            # Fallback: Try html.parser if lxml-xml fails and content might be malformed HTML/XML
            logging.warning("No <item> tags found using 'lxml-xml'. Trying 'html.parser'.")
            soup = BeautifulSoup(xml_content, 'html.parser')
            items = soup.find_all('item')
            if not items:
                 logging.warning("No <item> tags found using 'html.parser' either.")
                 return []

        logging.info(f"Found {len(items)} <item> tags in the fetched content.")

        # Process items with early exit strategy
        for i, item in enumerate(items):
            title_tag = item.find('title')
            description_tag = item.find('description')
            link_tag = item.find('link')
            pub_date_tag = item.find('pubDate')

            title = title_tag.text.strip() if title_tag else "No Title"
            description = description_tag.text.strip() if description_tag else "No Description"
            # Link tag might contain the URL directly or within CDATA
            link_text = link_tag.text.strip() if link_tag else None 
            pub_date = pub_date_tag.text.strip() if pub_date_tag else ""

            identifier = None
            if link_text:
                identifier = link_text
            else:
                logging.warning(f"Link tag missing or empty for item '{title[:30]}...'. Using content hash as identifier.")
                content_to_hash = (title + description).encode('utf-8')
                identifier = hashlib.sha256(content_to_hash).hexdigest()

            # Optimized identifier checking with cache + database fallback
            is_known_item = False
            
            # First check in-memory cache (O(1) lookup)
            if identifier in seen_item_identifiers_set:
                is_known_item = True
            else:
                # Cache miss - check database (this is expensive but necessary for accuracy)
                if check_identifier_exists(identifier):
                    is_known_item = True
                    # Add to cache for future lookups
                    seen_item_identifiers_set.add(identifier)

            if not is_known_item:
                # This is a new item
                item_object = {
                    "timestamp": pub_date,
                    "title": title,
                    "description": description,
                    "link": link_text,
                    "identifier": identifier
                }
                potential_new_items.append(item_object)
                consecutive_known_items = 0  # Reset counter
                logging.debug(f"New item candidate: {title[:50]}... (Published: {pub_date})")
            else:
                consecutive_known_items += 1
                logging.debug(f"Known item skipped: {title[:50]}... (consecutive: {consecutive_known_items})")
                
                # Early exit strategy: if we've seen many consecutive known items,
                # assume we've reached the "old" part of the RSS feed
                if consecutive_known_items >= max_consecutive_known:
                    logging.info(f"Early exit: Found {consecutive_known_items} consecutive known items. "
                               f"Processed {i+1}/{len(items)} items. Assuming remaining items are old.")
                    break

        # Batch process all new items
        if potential_new_items:
            logging.info(f"Processing {len(potential_new_items)} potential new items in batch...")
            
            # Batch insert to database
            successfully_added = batch_add_new_items(potential_new_items)
            
            if successfully_added:
                # Update in-memory tracking
                for item_object in successfully_added:
                    seen_item_objects_list.append(item_object)
                    new_items_found.append(item_object)
                
                # Update memory cache with new identifiers
                new_identifiers = [item['identifier'] for item in successfully_added]
                update_memory_cache(new_identifiers)
                
                logging.info(f"✓ Successfully processed {len(successfully_added)} new items")
                
                # Trim database less frequently (only if we added items)
                save_seen_items(seen_item_objects_list)
            else:
                logging.info("No new items were actually added (all were duplicates)")
        else:
            logging.info("No new items found during parsing")

    except Exception as e:
        logging.error(f"Error parsing content from {url}: {e}", exc_info=True)

    return new_items_found

if __name__ == "__main__":
    import time
    start_time = time.time()
    
    url = "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"
    
    try:
        # Test multiple calls to show browser persistence
        print(f"\n{'='*60}")
        print("PERSISTENT BROWSER TEST - Multiple Calls")
        print(f"{'='*60}")
        
        for i in range(3):
            print(f"\n--- Call {i+1}/3 ---")
            call_start = time.time()
            items = get_new_items(url)
            call_end = time.time()
            print(f"Call {i+1}: Found {len(items)} new items in {call_end - call_start:.2f} seconds")
            print(f"Browser usage count: {browser_refresh_counter}/20")
            time.sleep(1)  # Small delay between calls
        
        end_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"FINAL RESULTS:")
        print(f"{'='*60}")
        print(f"Total time for 3 calls: {end_time - start_time:.2f} seconds")
        print(f"Average time per call: {(end_time - start_time)/3:.2f} seconds")
        print(f"In-memory cache size: {len(seen_item_identifiers_set)}")
        print(f"Total items in database: {len(seen_item_objects_list)}")
        print(f"Browser usage count: {browser_refresh_counter}/{MAX_BROWSER_REUSES}")
        print(f"{'='*60}")
        
    finally:
        # Always cleanup browser on exit
        cleanup_persistent_browser()
