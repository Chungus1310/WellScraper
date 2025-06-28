import json
import sys
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

BASE_URL = "https://wellfound.com/role/l/"

def build_search_url(keyword, location):
    """Build search URL for job listings"""
    keyword = keyword.lower().replace(' ', '-')
    location = location.lower().replace(' ', '-')
    return f"{BASE_URL}{keyword}/{location}"

def is_captcha_page(html):
    """Check if the page contains CAPTCHA or anti-bot measures"""
    return 'captcha' in html.lower() or 'interstitial' in html.lower() or 'cf-chl' in html.lower()

def validate_and_format_job_url(url):
    """Validate and format job URL"""
    if not url:
        return None
    
    if url.startswith('http'):
        return url
    
    if url.startswith('/'):
        return 'https://wellfound.com' + url
    
    return 'https://wellfound.com' + url if not url.startswith('https://wellfound.com') else url

def extract_job_details_from_html(html_content):
    """Extract detailed job information from a Wellfound job page HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')
    job_data = {}
    
    try:
        # Extract company information
        job_data['company'] = {}
        
        # Find company name and link
        company_link = soup.find('a', {'rel': 'noopener noreferrer', 'target': '_blank', 'href': lambda x: x and '/company/' in x})
        if company_link:
            job_data['company']['link'] = 'https://wellfound.com' + company_link['href']
            
            # Company logo
            company_img = company_link.find('img')
            if company_img and company_img.get('src'):
                job_data['company']['logo'] = company_img['src']
        
        # Find company name separately
        company_name = soup.find('span', class_='text-sm font-semibold text-black')
        if company_name:
            job_data['company']['name'] = company_name.get_text(strip=True)
        
        # Company description
        company_desc = soup.find('div', class_='text-sm font-light text-neutral-500')
        if company_desc:
            job_data['company']['description'] = company_desc.get_text(strip=True)
        
        # Company tags/categories - remove duplicates
        company_tags = []
        tag_containers = soup.find_all('li', class_='styles_tooltip-container__1f8OY')
        for tag in tag_containers:
            tag_text = tag.find('div', class_='line-clamp-1')
            if tag_text:
                tag_value = tag_text.get_text(strip=True)
                if tag_value not in company_tags:
                    company_tags.append(tag_value)
        if company_tags:
            job_data['company']['tags'] = company_tags
        
        # Job title
        job_title = soup.find('h1', class_='inline text-xl font-semibold text-black')
        if job_title:
            job_data['title'] = job_title.get_text(strip=True)
        
        # Job location and type
        job_info_list = soup.find('ul', class_='block text-md text-black md:flex')
        if job_info_list:
            list_items = job_info_list.find_all('li')
            for item in list_items:
                text = item.get_text(strip=True)
                if 'Full Time' in text:
                    job_data['employment_type'] = 'Full Time'
                elif 'Part Time' in text:
                    job_data['employment_type'] = 'Part Time'
                elif 'Contract' in text:
                    job_data['employment_type'] = 'Contract'
                # Check for location link
                location_link = item.find('a')
                if location_link:
                    job_data['location'] = location_link.get_text(strip=True)
        
        # Posted date
        posted_date = soup.find('div', class_='mt-0.5 text-sm font-extralight text-neutral-500')
        if posted_date:
            posted_text = posted_date.get_text(strip=True)
            posted_text = posted_text.replace('Posted:', '').replace('Posted', '').strip()
            job_data['posted_date'] = posted_text
        
        # Visa sponsorship and relocation
        grid_sections = soup.find_all('div', class_='grid grid-cols-1 gap-6 rounded-b-xl bg-neutral-50 p-6 py-6 md:grid-cols-2')
        for grid in grid_sections:
            sections = grid.find_all('div')
            for section in sections:
                heading = section.find('span', class_='text-md font-semibold')
                if heading:
                    heading_text = heading.get_text(strip=True)
                    if 'Visa Sponsorship' in heading_text:
                        content = section.find('p')
                        if content:
                            job_data['visa_sponsorship'] = content.get_text(strip=True)
                    elif 'Relocation' in heading_text:
                        content = section.find('span', class_='flex items-center')
                        if content:
                            if 'Allowed' in content.get_text():
                                job_data['relocation'] = 'Allowed'
                            else:
                                job_data['relocation'] = content.get_text(strip=True)
        
        # Job description
        job_description_div = soup.find('div', {'id': 'job-description'})
        if job_description_div:
            paragraphs = job_description_div.find_all('p')
            description_parts = []
            structured_sections = {}
            current_section = None
            
            for p in paragraphs:
                text = p.get_text(strip=True)
                if not text:
                    continue
                
                # Check for section headers (bold text)
                strong_tags = p.find_all('strong')
                if strong_tags:
                    for strong in strong_tags:
                        strong_text = strong.get_text(strip=True)
                        if strong_text:
                            section_key = strong_text.lower().replace(' ', '_').replace(':', '')
                            current_section = section_key
                            structured_sections[current_section] = []
                            
                            remaining_text = text.replace(strong_text, '').strip()
                            if remaining_text:
                                structured_sections[current_section].append(remaining_text)
                            break
                else:
                    if current_section:
                        structured_sections[current_section].append(text)
                    else:
                        if 'overview' not in structured_sections:
                            structured_sections['overview'] = []
                        structured_sections['overview'].append(text)
                
                description_parts.append(text)
            
            job_data['description'] = {
                'full_text': '\n\n'.join(description_parts),
                'sections': structured_sections
            }
        
        # Apply button link
        apply_buttons = soup.find_all('button', string=lambda text: text and 'Apply Now' in text)
        for button in apply_buttons:
            onclick = button.get('onclick')
            if onclick and 'window.location.href' in onclick:
                start = onclick.find("'") + 1
                end = onclick.rfind("'")
                if start > 0 and end > start:
                    job_data['apply_link'] = 'https://wellfound.com' + onclick[start:end]
                    break
        
        return job_data
        
    except Exception as e:
        print(f"Error extracting job details: {str(e)}")
        return {"error": str(e)}

def handle_captcha_if_needed(driver, url, operation_name="operation"):
    """Handle CAPTCHA detection and resolution"""
    html = driver.page_source
    
    if is_captcha_page(html):
        print(f"CAPTCHA detected during {operation_name}! Opening a visible browser window.")
        print("Please solve the CAPTCHA and press Enter here when done.")
        
        # Get current cookies before quitting
        cookies = driver.get_cookies()
        driver.quit()
        
        # Open visible browser
        chrome_options = Options()
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        # Restore cookies
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except:
                pass
        driver.refresh()
        
        input(f"After solving the CAPTCHA in the browser window, press Enter here to continue with {operation_name}...")
        html = driver.page_source
        
        # Check again
        if is_captcha_page(html):
            print("CAPTCHA still detected. Please refresh the page in the browser if needed.")
            input("Press Enter when the page is loaded correctly...")
            html = driver.page_source
    
    return driver, html

def scrape_job_listings(driver, keyword, location):
    """Scrape job listings from search results"""
    url = build_search_url(keyword, location)
    print(f"\n=== STEP 1: Searching for jobs ===")
    print(f"Fetching: {url}")
    
    driver.get(url)
    time.sleep(5)
    
    # Handle CAPTCHA if needed
    driver, html = handle_captcha_if_needed(driver, url, "job search")
    
    # Save debug files for search
    driver.save_screenshot('debug_search_screenshot.png')
    with open('debug_search_page.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print('Search page HTML DUMP START (first 1000 chars)')
    print(html[:1000])
    print('Search page HTML DUMP END')
    
    # Parse job listings
    soup = BeautifulSoup(html, 'html.parser')
    jobs = []
    
    for card in soup.find_all('div', class_='mb-4 w-full px-4'):
        job = {}
        title_tag = card.find('a', class_='mr-2 text-sm font-semibold text-brand-burgandy hover:underline')
        if title_tag:
            job['title'] = title_tag.get_text(strip=True)
            job['link'] = validate_and_format_job_url(title_tag['href'])
        
        type_tag = card.find('span', class_='whitespace-nowrap rounded-lg bg-accent-yellow-100 px-2 py-1 text-[10px] font-semibold text-neutral-800')
        if type_tag:
            job['type'] = type_tag.get_text(strip=True)
        
        loc_tag = card.find('span', class_='pl-1 text-xs')
        if loc_tag:
            job['location'] = loc_tag.get_text(strip=True)
        
        date_tag = card.find('span', class_='text-xs lowercase text-dark-a')
        if date_tag:
            job['date_posted'] = date_tag.get_text(strip=True)
        
        # Find company info
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
        
        if job and job.get('link'):  # Only add jobs with valid links
            jobs.append(job)
    
    print(f"Found {len(jobs)} job listings")
    return jobs

def extract_detailed_job_info(driver, jobs, max_jobs=None):
    """Extract detailed information for each job"""
    print(f"\n=== STEP 2: Extracting detailed job information ===")
    
    detailed_jobs = []
    jobs_to_process = jobs[:max_jobs] if max_jobs else jobs
    
    for i, job in enumerate(jobs_to_process, 1):
        job_url = job.get('link')
        if not job_url:
            print(f"Job {i}: No URL found, skipping...")
            continue
        
        print(f"\nJob {i}/{len(jobs_to_process)}: {job.get('title', 'Unknown Title')}")
        print(f"URL: {job_url}")
        
        try:
            driver.get(job_url)
            time.sleep(3)  # Shorter wait between jobs
            
            # Handle CAPTCHA if needed
            driver, html = handle_captcha_if_needed(driver, job_url, f"job {i} details extraction")
            
            # Check if page loaded successfully
            if len(html) < 1000:
                print(f"⚠ Warning: Job {i} page seems incomplete, skipping...")
                continue
            
            # Extract detailed job information
            detailed_job = extract_job_details_from_html(html)
            
            # Merge with basic job info from search
            detailed_job.update({
                'search_info': job,
                'source_url': job_url,
                'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'extraction_order': i
            })
            
            # Print summary
            company_name = detailed_job.get('company', {}).get('name', job.get('company', 'Unknown'))
            job_title = detailed_job.get('title', job.get('title', 'Unknown'))
            location = detailed_job.get('location', job.get('location', 'Unknown'))
            
            print(f"✓ Company: {company_name}")
            print(f"✓ Title: {job_title}")
            print(f"✓ Location: {location}")
            
            # Check for extraction issues
            if 'error' in detailed_job:
                print(f"⚠ Extraction warning: {detailed_job['error']}")
            
            detailed_jobs.append(detailed_job)
            
        except Exception as e:
            print(f"✗ Error processing job {i}: {str(e)}")
            
            # Try to recover the browser session if needed
            try:
                driver.current_url  # Test if driver is still alive
            except:
                print("Browser session lost, attempting to restart...")
                try:
                    driver.quit()
                except:
                    pass
                
                # Restart browser
                chrome_options = Options()
                chrome_options.add_argument('--window-size=1920,1080')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
                driver = webdriver.Chrome(options=chrome_options)
                print("Browser session restarted.")
            
            # Add error job entry
            detailed_jobs.append({
                'search_info': job,
                'error': str(e),
                'source_url': job_url,
                'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'extraction_order': i
            })
        
        # Brief pause between jobs
        time.sleep(1)
    
    return detailed_jobs

def save_results(jobs_basic, jobs_detailed, keyword, location):
    """Save results to JSON files"""
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    
    # Save basic job listings
    basic_filename = f"jobs_search_{keyword}_{location}_{timestamp}.json"
    with open(basic_filename, 'w', encoding='utf-8') as f:
        json.dump(jobs_basic, f, ensure_ascii=False, indent=2)
    
    # Save detailed job information
    detailed_filename = f"jobs_detailed_{keyword}_{location}_{timestamp}.json"
    with open(detailed_filename, 'w', encoding='utf-8') as f:
        json.dump(jobs_detailed, f, ensure_ascii=False, indent=2)
    
    # Save summary report
    summary = {
        'search_info': {
            'keyword': keyword,
            'location': location,
            'search_timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        },
        'results_summary': {
            'total_jobs_found': len(jobs_basic),
            'total_jobs_detailed': len(jobs_detailed),
            'successful_extractions': len([j for j in jobs_detailed if 'error' not in j]),
            'failed_extractions': len([j for j in jobs_detailed if 'error' in j])
        },
        'files_created': {
            'basic_listings': basic_filename,
            'detailed_info': detailed_filename
        }
    }
    
    summary_filename = f"jobs_summary_{keyword}_{location}_{timestamp}.json"
    with open(summary_filename, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    return basic_filename, detailed_filename, summary_filename

def main():
    """Main function"""
    if len(sys.argv) < 3:
        print("Wellfound Job Scraper & Detailed Extractor")
        print("=" * 50)
        print("Usage: python job_scraper_complete.py <keyword> <location> [max_jobs] [output_prefix]")
        print("\nExamples:")
        print("  python job_scraper_complete.py 'software engineer' 'san francisco'")
        print("  python job_scraper_complete.py 'financial analyst' 'india' 5")
        print("  python job_scraper_complete.py 'data scientist' 'remote' 10 'data_jobs'")
        print("\nFeatures:")
        print("  - Searches for jobs by keyword and location")
        print("  - Extracts detailed information for each job found")
        print("  - Automatic CAPTCHA detection and handling")
        print("  - Shared browser session for efficiency")
        print("  - Comprehensive JSON output with timestamps")
        return
    
    keyword = sys.argv[1]
    location = sys.argv[2]
    max_jobs = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else None
    
    print("Wellfound Complete Job Scraper")
    print("=" * 50)
    print(f"Keyword: {keyword}")
    print(f"Location: {location}")
    print(f"Max jobs to detail: {max_jobs if max_jobs else 'All found'}")
    print("=" * 50)
    
    # Initialize browser
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Step 1: Search for jobs
        jobs_basic = scrape_job_listings(driver, keyword, location)
        
        if not jobs_basic:
            print("No jobs found in search results.")
            return
        
        # Step 2: Extract detailed information
        jobs_detailed = extract_detailed_job_info(driver, jobs_basic, max_jobs)
        
        # Step 3: Save results
        basic_file, detailed_file, summary_file = save_results(jobs_basic, jobs_detailed, keyword, location)
        
        # Print final summary
        print("\n" + "=" * 50)
        print("EXTRACTION COMPLETE!")
        print("=" * 50)
        print(f"Total jobs found: {len(jobs_basic)}")
        print(f"Detailed extractions: {len(jobs_detailed)}")
        print(f"Successful: {len([j for j in jobs_detailed if 'error' not in j])}")
        print(f"Failed: {len([j for j in jobs_detailed if 'error' in j])}")
        print("\nFiles created:")
        print(f"  📄 {basic_file}")
        print(f"  📋 {detailed_file}")
        print(f"  📊 {summary_file}")
        print(f"  🖼️ debug_search_screenshot.png")
        print(f"  📄 debug_search_page.html")
        
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
    except Exception as e:
        print(f"\n\nUnexpected error: {str(e)}")
    finally:
        try:
            driver.quit()
        except:
            pass
        print("\nBrowser closed. Done!")

if __name__ == "__main__":
    main()
