import json
import sys
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

BASE_URL = "https://wellfound.com/role/l/"

def build_url(keyword, location):
    keyword = keyword.lower().replace(' ', '-')
    location = location.lower().replace(' ', '-')
    return f"{BASE_URL}{keyword}/{location}"

def is_captcha_page(html):
    return 'captcha' in html.lower() or 'interstitial' in html.lower() or 'cf-chl' in html.lower()

def scrape_jobs(keyword, location, output_file="jobs.json", cookie_string=None):
    url = build_url(keyword, location)
    print(f"Fetching: {url}")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    time.sleep(5)
    html = driver.page_source
    # If captcha detected, open a visible browser for user to solve, and do ALL further work in that session
    if is_captcha_page(html):
        print("CAPTCHA detected! Opening a visible browser window. Please solve the CAPTCHA and press Enter here when done.")
        driver.quit()
        chrome_options = Options()
        # Do NOT add headless this time
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        input("After solving the CAPTCHA in the browser window, press Enter here to continue...")
        # Now, continue with the new session only
        html = driver.page_source
    # Save screenshot and HTML for debugging
    driver.save_screenshot('debug_screenshot.png')
    with open('debug_page.html', 'w', encoding='utf-8') as f:
        f.write(html)
    soup = BeautifulSoup(html, 'html.parser')
    print('HTML DUMP START')
    print(html[:1000])
    print('HTML DUMP END')
    jobs = []
    for card in soup.find_all('div', class_='mb-4 w-full px-4'):
        job = {}
        title_tag = card.find('a', class_='mr-2 text-sm font-semibold text-brand-burgandy hover:underline')
        if title_tag:
            job['title'] = title_tag.get_text(strip=True)
            job['link'] = 'https://wellfound.com' + title_tag['href']
        type_tag = card.find('span', class_='whitespace-nowrap rounded-lg bg-accent-yellow-100 px-2 py-1 text-[10px] font-semibold text-neutral-800')
        if type_tag:
            job['type'] = type_tag.get_text(strip=True)
        loc_tag = card.find('span', class_='pl-1 text-xs')
        if loc_tag:
            job['location'] = loc_tag.get_text(strip=True)
        date_tag = card.find('span', class_='text-xs lowercase text-dark-a')
        if date_tag:
            job['date_posted'] = date_tag.get_text(strip=True)
        company_div = card.find_previous('div', class_='w-full space-y-2 px-4 pb-2 pt-4')
        if company_div:
            company_name_tag = company_div.find('h2', class_='inline text-md font-semibold')
            if company_name_tag:
                job['company'] = company_name_tag.get_text(strip=True)
            company_desc_tag = company_div.find('span', class_='text-xs text-neutral-1000')
            if company_desc_tag:
                job['company_desc'] = company_desc_tag.get_text(strip=True)
            company_size_tag = company_div.find('span', class_='text-xs italic text-neutral-500')
            if company_size_tag:
                job['company_size'] = company_size_tag.get_text(strip=True)
        if job:
            jobs.append(job)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print(f"Extracted {len(jobs)} jobs to {output_file}")
    driver.quit()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract.py <keyword> <location> [output_file]")
    else:
        keyword = sys.argv[1]
        location = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else "jobs.json"
        scrape_jobs(keyword, location, output_file)
