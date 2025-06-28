import json
import sys
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def extract_job_details_from_html(html_content):
    """
    Extract detailed job information from a Wellfound job page HTML
    """
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
        
        # Find company name separately (it might be outside the link)
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
                if tag_value not in company_tags:  # Avoid duplicates
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
            # Clean up the posted date text
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
                            job_data['relocation'] = content.get_text(strip=True).replace('Allowed', '').strip()
                            if 'Allowed' in content.get_text():
                                job_data['relocation'] = 'Allowed'
        
        # Job description
        job_description_div = soup.find('div', {'id': 'job-description'})
        if job_description_div:
            # Extract all paragraphs and format them
            paragraphs = job_description_div.find_all('p')
            description_parts = []
            structured_sections = {}
            
            current_section = None
            
            for p in paragraphs:
                text = p.get_text(strip=True)
                if not text:  # Skip empty paragraphs
                    continue
                
                # Check if this paragraph contains a section header (bold text)
                strong_tags = p.find_all('strong')
                if strong_tags:
                    for strong in strong_tags:
                        strong_text = strong.get_text(strip=True)
                        if strong_text:
                            # This is likely a section header
                            section_key = strong_text.lower().replace(' ', '_').replace(':', '')
                            current_section = section_key
                            structured_sections[current_section] = []
                            
                            # Remove the strong text from the paragraph and add remainder
                            remaining_text = text.replace(strong_text, '').strip()
                            if remaining_text:
                                structured_sections[current_section].append(remaining_text)
                            break
                else:
                    # Regular paragraph content
                    if current_section:
                        structured_sections[current_section].append(text)
                    else:
                        # No current section, add to general
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
                # Extract URL from onclick
                start = onclick.find("'") + 1
                end = onclick.rfind("'")
                if start > 0 and end > start:
                    job_data['apply_link'] = 'https://wellfound.com' + onclick[start:end]
                    break
        
        return job_data
        
    except Exception as e:
        print(f"Error extracting job details: {str(e)}")
        return {"error": str(e)}

def validate_and_format_url(url):
    """
    Validate and format the job URL to ensure it's properly formatted
    """
    if not url:
        return None
    
    # If it's already a full URL, return as is
    if url.startswith('http'):
        return url
    
    # If it starts with /, prepend the base domain
    if url.startswith('/'):
        return 'https://wellfound.com' + url
    
    # If it's just a job ID or partial path, construct the full URL
    if url.startswith('jobs/') or url.isdigit() or '-' in url:
        if not url.startswith('jobs/'):
            url = 'jobs/' + url
        return 'https://wellfound.com/' + url
    
    # Default case - assume it's a job identifier
    return 'https://wellfound.com/jobs/' + url

def is_captcha_page(html):
    """
    Check if the page contains CAPTCHA or anti-bot measures
    """
    return 'captcha' in html.lower() or 'interstitial' in html.lower() or 'cf-chl' in html.lower()

def extract_job_from_url(job_url, output_file="job_details.json", cookie_string=None):
    """
    Extract job details from a Wellfound job URL with CAPTCHA handling
    """
    print(f"Fetching job details from: {job_url}")
    
    # Start with headless browser
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        driver.get(job_url)
        
        # Add cookies if provided
        if cookie_string:
            # Parse cookie string and add to driver
            for cookie in cookie_string.split(';'):
                if '=' in cookie:
                    name, value = cookie.strip().split('=', 1)
                    driver.add_cookie({'name': name, 'value': value})
            driver.refresh()
        
        time.sleep(5)  # Wait for page to load
        
        html = driver.page_source
        
        # Check for CAPTCHA and handle it if detected
        if is_captcha_page(html):
            print("CAPTCHA detected! Opening a visible browser window. Please solve the CAPTCHA and press Enter here when done.")
            driver.quit()
            
            # Open visible browser for CAPTCHA solving
            chrome_options = Options()
            # Remove headless mode for CAPTCHA solving
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(job_url)
            
            # Add cookies to the new visible session as well
            if cookie_string:
                for cookie in cookie_string.split(';'):
                    if '=' in cookie:
                        name, value = cookie.strip().split('=', 1)
                        driver.add_cookie({'name': name, 'value': value})
                driver.refresh()
            
            input("After solving the CAPTCHA in the browser window, press Enter here to continue...")
            
            # Get the page content after CAPTCHA is solved
            html = driver.page_source
        
        # Save debug files
        driver.save_screenshot('debug_job_screenshot.png')
        with open('debug_job_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print('HTML DUMP START (first 1000 chars)')
        print(html[:1000])
        print('HTML DUMP END')
        
        # Check if we still have CAPTCHA after user intervention
        if is_captcha_page(html):
            print("CAPTCHA still detected. Please refresh the page in the browser and try again.")
            input("Press Enter when the job page is loaded correctly...")
            html = driver.page_source
        
        # Check if page loaded successfully
        if len(html) < 1000:
            print("Warning: Page seems to have loaded incompletely. Content may be missing.")
        
        # Extract job details
        job_data = extract_job_details_from_html(html)
        
        # Add metadata
        job_data['source_url'] = job_url
        job_data['extracted_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        job_data['html_length'] = len(html)
        
        # Save to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, ensure_ascii=False, indent=2)
        
        print(f"Job details extracted and saved to {output_file}")
        
        # Print summary of extracted data
        if 'company' in job_data and 'name' in job_data['company']:
            print(f"✓ Company: {job_data['company']['name']}")
        if 'title' in job_data:
            print(f"✓ Job Title: {job_data['title']}")
        if 'location' in job_data:
            print(f"✓ Location: {job_data['location']}")
        if 'posted_date' in job_data:
            print(f"✓ Posted: {job_data['posted_date']}")
        
        # Check for potential extraction issues
        if 'error' in job_data:
            print(f"⚠ Extraction had issues: {job_data['error']}")
        elif not job_data.get('title'):
            print("⚠ Warning: Job title not found - page might not have loaded correctly")
        
        return job_data
        
    except Exception as e:
        print(f"Error scraping job: {str(e)}")
        return {"error": str(e), "url": job_url, "extracted_at": time.strftime('%Y-%m-%d %H:%M:%S')}
    
    finally:
        try:
            driver.quit()
        except:
            pass

def extract_job_from_file(html_file_path, output_file="job_details.json"):
    """
    Extract job details from a local HTML file
    """
    print(f"Extracting job details from local file: {html_file_path}")
    
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        job_data = extract_job_details_from_html(html_content)
        job_data['source_file'] = html_file_path
        job_data['extracted_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Save to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, ensure_ascii=False, indent=2)
        
        print(f"Job details extracted and saved to {output_file}")
        return job_data
        
    except Exception as e:
        print(f"Error extracting from file: {str(e)}")
        return {"error": str(e)}

def main():
    """
    Main function to handle command line arguments
    """
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h', 'help']:
        print("Usage:")
        print("  python extract_job.py <job_url> [output_file]")
        print("  python extract_job.py --file <html_file> [output_file]")
        print("\nURL Examples:")
        print("  python extract_job.py https://wellfound.com/jobs/3021779-senior-financial-analyst")
        print("  python extract_job.py /jobs/3021779-senior-financial-analyst")
        print("  python extract_job.py 3021779-senior-financial-analyst")
        print("  python extract_job.py jobs/3021779-senior-financial-analyst")
        print("\nFile Examples:")
        print("  python extract_job.py --file test.html job_details.json")
        print("  python extract_job.py --file tag.html")
        print("\nFeatures:")
        print("  - Automatic CAPTCHA detection and handling")
        print("  - Works with full URLs, partial URLs, or job IDs")
        print("  - Extracts structured job data to JSON")
        print("  - Debug files saved for troubleshooting")
        return
    
    if sys.argv[1] == '--file':
        if len(sys.argv) < 3:
            print("Error: Please provide the HTML file path")
            return
        
        html_file = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else "job_details.json"
        extract_job_from_file(html_file, output_file)
        
    else:
        job_url = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "job_details.json"
        
        # Validate and format URL
        job_url = validate_and_format_url(job_url)
        if not job_url:
            print("Error: Invalid URL provided")
            return
        
        print(f"Formatted URL: {job_url}")
        extract_job_from_url(job_url, output_file)

if __name__ == "__main__":
    main()
