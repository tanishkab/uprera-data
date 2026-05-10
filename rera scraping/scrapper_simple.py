#!/usr/bin/env python3
"""
Simple UP RERA Scraper
"""
import time
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# Initialize Chrome
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 20)

print("🚀 Starting scraper...")

# Navigate to homepage first
print("Step 1: Going to homepage...")
driver.get("https://up-rera.in/")
time.sleep(5)
print(f"✅ Loaded: {driver.title}")
print(f"   URL: {driver.current_url}")

# Close popup if any
try:
    time.sleep(2)
    driver.execute_script("""
        var modals = document.querySelectorAll('.modal');
        modals.forEach(function(modal) { modal.style.display = 'none'; });
        var backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach(function(backdrop) { backdrop.remove(); });
        document.body.classList.remove('modal-open');
        document.body.style.overflow = 'auto';
    """)
    print("✅ Cleared any modals")
except:
    pass

# Scroll down and find Registered Agents
print("\nStep 2: Finding Registered Agents...")
time.sleep(2)

# Scroll down to find it
for i in range(10):
    driver.execute_script(f"window.scrollBy(0, 300);")
    time.sleep(0.3)

time.sleep(2)

# Try to find and click Registered Agents
agent_link = None
selectors = [
    (By.ID, "ctl00_ContentPlaceHolder1_lnkAgents"),
    (By.XPATH, "//a[contains(@href, 'agents')]"),
    (By.XPATH, "//span[contains(text(), 'Registered Agent')]/parent::a"),
    (By.XPATH, "//a[.//span[contains(text(), 'Registered Agent')]]"),
    (By.XPATH, "//*[contains(text(), 'Registered Agent')]"),
]

for method, selector in selectors:
    try:
        agent_link = driver.find_element(method, selector)
        if agent_link and agent_link.is_displayed():
            print(f"✅ Found via: {selector}")
            break
        agent_link = None
    except:
        continue

if agent_link:
    driver.execute_script("arguments[0].click();", agent_link)
    time.sleep(4)
    print(f"✅ Clicked! URL: {driver.current_url}")
else:
    print("⚠️ Not found on homepage, going directly...")
    driver.get("https://up-rera.in/agents")
    time.sleep(4)
    print(f"   URL: {driver.current_url}")

# Check if we landed on maintenance page
if "maintenance" in driver.current_url.lower():
    print("❌ Site is under maintenance! Trying homepage approach...")
    driver.get("https://up-rera.in/")
    time.sleep(5)
    # Try clicking via JS
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
    time.sleep(2)

print(f"\n📍 Current URL: {driver.current_url}")
print(f"📍 Page title: {driver.title}")

# DEBUG: Print what's on the page
print("\n🔍 DEBUG: Looking for tables...")
tables = driver.find_elements(By.TAG_NAME, "table")
print(f"   Found {len(tables)} table(s)")

print("\n🔍 DEBUG: Looking for any links with 'VIEW' or 'Detail'...")
all_links = driver.find_elements(By.TAG_NAME, "a")
view_links = []
for link in all_links:
    txt = link.text.strip().upper()
    if "VIEW" in txt or "DETAIL" in txt:
        view_links.append(link)
        print(f"   Found link: '{link.text.strip()}' | href: {link.get_attribute('href')[:80] if link.get_attribute('href') else 'None'}")

print(f"\n   Total VIEW/DETAIL links: {len(view_links)}")

if not view_links:
    print("\n🔍 DEBUG: Looking for ALL links on the page...")
    for link in all_links[:20]:
        txt = link.text.strip()
        if txt:
            print(f"   Link: '{txt[:50]}'")

# Ask how many agents
num_agents = int(input("\n📝 How many agents to scrape? (default 5): ") or "5")

all_data = []
main_window = driver.current_window_handle

print(f"\n🔄 Scraping {num_agents} agents...")
print("=" * 70)

for agent_num in range(1, num_agents + 1):
    print(f"\n📋 Agent {agent_num}/{num_agents}")

    try:
        # Wait for table
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        time.sleep(0.5)

        # Get all VIEW DETAIL links on the page
        all_view_buttons = driver.find_elements(By.XPATH,
            "//a[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'VIEW')]")

        if not all_view_buttons:
            # Try other selectors
            all_view_buttons = driver.find_elements(By.XPATH, "//a[contains(@id, 'lnkView')]")

        if not all_view_buttons:
            all_view_buttons = driver.find_elements(By.XPATH, "//input[contains(@value, 'View')]")

        print(f"  🔍 Found {len(all_view_buttons)} view buttons")

        if agent_num - 1 >= len(all_view_buttons):
            print(f"  ⚠️ Button {agent_num} not found (only {len(all_view_buttons)} available)")
            continue

        button = all_view_buttons[agent_num - 1]
        print(f"  🖱️  Clicking: '{button.text.strip()}' | tag: {button.tag_name}")

        # Click it
        driver.execute_script("arguments[0].click();", button)
        time.sleep(2)

        # Check if new window
        windows = driver.window_handles

        if len(windows) > 1:
            print(f"  ✅ New window opened")
            # Switch to new window
            for w in windows:
                if w != main_window:
                    driver.switch_to.window(w)
                    break

            time.sleep(1.5)

            # Scrape
            page_text = driver.find_element(By.TAG_NAME, "body").text
            tds = driver.find_elements(By.TAG_NAME, "td")

            data = {
                'Agent_Number': agent_num,
                'Name': 'N/A',
                'Phone': 'N/A',
                'District': 'N/A',
                'Registration_No': 'N/A',
                'Registration_Date': 'N/A',
                'Valid_Upto': 'N/A',
                'Email': 'N/A',
                'Address': 'N/A'
            }

            # Extract from table cells
            for i, td in enumerate(tds):
                txt = td.text.strip().lower()
                nxt = tds[i + 1].text.strip() if i + 1 < len(tds) else ''

                if ("agent name" in txt or "name" in txt) and data['Name'] == 'N/A':
                    data['Name'] = nxt
                elif "registration no" in txt:
                    data['Registration_No'] = nxt
                elif "registration date" in txt:
                    data['Registration_Date'] = nxt
                elif "valid upto" in txt or "validity" in txt:
                    data['Valid_Upto'] = nxt
                elif "district" in txt:
                    data['District'] = nxt
                elif "address" in txt:
                    data['Address'] = nxt

            # Extract phone
            phone_match = re.search(r'([6-9][0-9]{9})', page_text)
            if phone_match:
                data['Phone'] = phone_match.group(1)

            # Extract email
            email_match = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', page_text)
            if email_match:
                data['Email'] = email_match.group(0)

            print(f"  ✅ {data['Name']}")
            print(f"     Phone: {data['Phone']} | Email: {data['Email']}")

            all_data.append(data)

            # Close window and go back
            driver.close()
            driver.switch_to.window(main_window)
            time.sleep(0.3)

        else:
            print(f"  ⚠️ No new window opened. Checking current page...")
            # Maybe it opened as same page - try scraping current page
            time.sleep(1)
            page_text = driver.find_element(By.TAG_NAME, "body").text
            print(f"  📄 Page text preview: {page_text[:200]}")
            # Go back
            driver.back()
            time.sleep(1)

    except Exception as e:
        print(f"  ❌ Error: {e}")
        # Recovery
        try:
            windows = driver.window_handles
            if len(windows) > 1:
                for w in windows:
                    if w != main_window:
                        driver.switch_to.window(w)
                        driver.close()
                driver.switch_to.window(main_window)
        except:
            pass

# Save to CSV
if all_data:
    df = pd.DataFrame(all_data)
    df.to_csv("rera_agents_complete.csv", index=False, encoding='utf-8-sig')
    print(f"\n✅ Saved {len(all_data)} agents to rera_agents_complete.csv")
else:
    print("\n⚠️ No data scraped")

print("\n🔚 Closing browser in 5 seconds...")
time.sleep(5)
driver.quit()
print("✅ Done!")
