from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import json
import os
import sys
import time
import threading
import shutil
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables for tracking extraction
extraction_status = {
    'active': False,
    'progress': 0,
    'current_job': '',
    'total_jobs': 0,
    'completed_jobs': 0,
    'errors': 0,
    'keyword': '',
    'location': '',
    'start_time': None,
    'results': []
}

def get_base_url(location):
    """Get the correct base URL based on location type"""
    if location.lower() == 'remote':
        return "https://wellfound.com/role/r/"
    else:
        return "https://wellfound.com/role/l/"

def build_search_url(keyword, location):
    """Build search URL for job listings"""
    keyword = keyword.lower().replace(' ', '-')
    base_url = get_base_url(location)
    
    if location.lower() == 'remote':
        return f"{base_url}{keyword}"
    else:
        location = location.lower().replace(' ', '-')
        return f"{base_url}{keyword}/{location}"

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
        return {"error": str(e)}

def handle_captcha_if_needed(driver, url, operation_name="operation"):
    """Handle CAPTCHA detection with auto-retry after 5 seconds"""
    html = driver.page_source
    
    if is_captcha_page(html):
        socketio.emit('status_update', {
            'type': 'captcha_detected',
            'message': f'Browser check detected during {operation_name}. Opening browser window and auto-retrying in 5 seconds...'
        })
        
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
        
        # Auto-retry after 5 seconds
        socketio.emit('status_update', {
            'type': 'auto_retry',
            'message': f'Auto-retrying in 5 seconds...'
        })
        time.sleep(5)
        html = driver.page_source
        
        # Check again
        if is_captcha_page(html):
            socketio.emit('status_update', {
                'type': 'manual_intervention',
                'message': 'Manual intervention needed. Please refresh the browser page if needed.'
            })
            time.sleep(3)  # Give a moment for user to act if needed
            html = driver.page_source
    
    return driver, html

def create_extraction_folder(keyword, location):
    """Create organized folder structure for extraction results"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Sanitize keyword and location for folder name
    safe_keyword = keyword.replace(' ', '-').replace('/', '-').replace('\\', '-')
    safe_location = location.replace(' ', '-').replace('/', '-').replace('\\', '-')
    
    base_folder = f"extractions/{safe_keyword}_{safe_location}_{timestamp}"
    
    # Create folders
    folders = {
        'base': base_folder,
        'results': f"{base_folder}/results",
        'debug': f"{base_folder}/debug",
        'temp': f"{base_folder}/temp"
    }
    
    for folder in folders.values():
        os.makedirs(folder, exist_ok=True)
    
    return folders

def cleanup_temp_files(folders):
    """Clean up temporary and debug files"""
    try:
        # Move debug files to debug folder
        debug_files = ['debug_search_screenshot.png', 'debug_search_page.html', 'debug_job_screenshot.png', 'debug_job_page.html']
        for file in debug_files:
            if os.path.exists(file):
                shutil.move(file, f"{folders['debug']}/{file}")
        
        # Clean up temp folder
        if os.path.exists(folders['temp']):
            shutil.rmtree(folders['temp'])
            
        socketio.emit('status_update', {
            'type': 'cleanup',
            'message': 'Temporary files cleaned up successfully'
        })
    except Exception as e:
        socketio.emit('status_update', {
            'type': 'error',
            'message': f'Cleanup error: {str(e)}'
        })

def scrape_jobs_with_details(keyword, location, max_jobs=None):
    """Main scraping function with real-time updates"""
    global extraction_status
    
    driver = None  # Initialize driver variable
    
    try:
        # Create timestamp for this extraction
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        extraction_status.update({
            'active': True,
            'progress': 0,
            'keyword': keyword,
            'location': location,
            'start_time': datetime.now(),
            'results': [],
            'completed_jobs': 0,
            'errors': 0,
            'extraction_id': f"{keyword.replace(' ', '-')}_{location.replace(' ', '-')}_{timestamp}",
            'timestamp': timestamp
        })
        
        # Create organized folders
        folders = create_extraction_folder(keyword, location)
        
        # Create initial JSON files immediately for real-time monitoring
        initial_search_data = {
            'extraction_info': {
                'keyword': keyword,
                'location': location,
                'start_time': datetime.now().isoformat(),
                'status': 'initializing'
            },
            'jobs': []
        }
        
        initial_detailed_data = {
            'extraction_info': {
                'keyword': keyword,
                'location': location,
                'start_time': datetime.now().isoformat(),
                'status': 'initializing'
            },
            'jobs': []
        }
        
        # Create real-time file paths
        search_filename = f"{folders['results']}/jobs_search_{timestamp}.json"
        detailed_filename = f"{folders['results']}/jobs_detailed_{timestamp}.json"
        progress_filename = f"{folders['results']}/extraction_progress_{timestamp}.json"
        
        # Write initial files
        with open(search_filename, 'w', encoding='utf-8') as f:
            json.dump(initial_search_data, f, ensure_ascii=False, indent=2)
        
        with open(detailed_filename, 'w', encoding='utf-8') as f:
            json.dump(initial_detailed_data, f, ensure_ascii=False, indent=2)
        
        # Create progress tracking file
        progress_data = {
            'extraction_id': extraction_status['extraction_id'],
            'keyword': keyword,
            'location': location,
            'start_time': datetime.now().isoformat(),
            'status': 'initializing',
            'total_jobs': 0,
            'completed_jobs': 0,
            'errors': 0,
            'progress_percentage': 0,
            'current_job': '',
            'files': {
                'search_file': search_filename,
                'detailed_file': detailed_filename
            }
        }
        
        with open(progress_filename, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
        
        # Store filenames in extraction_status for later use
        extraction_status.update({
            'search_filename': search_filename,
            'detailed_filename': detailed_filename,
            'progress_filename': progress_filename,
            'folders': folders
        })
        
        # Initialize browser
        socketio.emit('status_update', {
            'type': 'browser_init',
            'message': 'Initializing browser...'
        })
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        # Step 1: Search for jobs
        url = build_search_url(keyword, location)
        socketio.emit('status_update', {
            'type': 'search_start',
            'message': f'Searching for jobs: {url}'
        })
        
        driver.get(url)
        time.sleep(5)
        
        # Handle CAPTCHA if needed
        driver, html = handle_captcha_if_needed(driver, url, "job search")
        
        # Save search debug files
        driver.save_screenshot(f"{folders['debug']}/search_screenshot.png")
        with open(f"{folders['debug']}/search_page.html", 'w', encoding='utf-8') as f:
            f.write(html)
        
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
            
            if job and job.get('link'):
                jobs.append(job)
        
        # Update search results file in real-time
        search_data = {
            'extraction_info': {
                'keyword': keyword,
                'location': location,
                'start_time': extraction_status['start_time'].isoformat(),
                'search_completed_at': datetime.now().isoformat(),
                'status': 'search_completed'
            },
            'jobs': jobs
        }
        
        with open(search_filename, 'w', encoding='utf-8') as f:
            json.dump(search_data, f, ensure_ascii=False, indent=2)
        
        extraction_status['total_jobs'] = len(jobs)
        jobs_to_process = jobs[:max_jobs] if max_jobs else jobs
        
        # Update progress file
        progress_data.update({
            'total_jobs': len(jobs_to_process),
            'status': 'extracting_details',
            'search_completed_at': datetime.now().isoformat()
        })
        
        with open(progress_filename, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
        
        socketio.emit('status_update', {
            'type': 'search_complete',
            'message': f'Found {len(jobs)} jobs. Processing {len(jobs_to_process)} jobs...',
            'total_jobs': len(jobs_to_process)
        })
        
        # Step 2: Extract detailed information
        detailed_jobs = []
        
        for i, job in enumerate(jobs_to_process, 1):
            job_url = job.get('link')
            if not job_url:
                continue
            
            extraction_status['current_job'] = job.get('title', 'Unknown')
            extraction_status['progress'] = (i / len(jobs_to_process)) * 100
            
            # Emit progress update
            socketio.emit('job_progress', {
                'current': i,
                'total': len(jobs_to_process),
                'job_title': job.get('title', 'Unknown'),
                'company': job.get('company', 'Unknown'),
                'progress': extraction_status['progress']
            })
            
            # Emit status update
            socketio.emit('status_update', {
                'type': 'extracting_job',
                'message': f'Extracting job {i}/{len(jobs_to_process)}: {job.get("title", "Unknown")} at {job.get("company", "Unknown")}',
                'progress': extraction_status['progress']
            })
            
            # Force flush
            socketio.sleep(0.1)
            
            try:
                driver.get(job_url)
                time.sleep(2)
                
                # Handle CAPTCHA if needed
                driver, html = handle_captcha_if_needed(driver, job_url, f"job {i} details")
                
                if len(html) < 1000:
                    continue
                
                # Extract detailed job information
                detailed_job = extract_job_details_from_html(html)
                detailed_job.update({
                    'search_info': job,
                    'source_url': job_url,
                    'extracted_at': datetime.now().isoformat(),
                    'extraction_order': i
                })
                
                detailed_jobs.append(detailed_job)
                extraction_status['completed_jobs'] += 1
                extraction_status['results'].append(detailed_job)
                
                # Update detailed jobs file in real-time
                detailed_data = {
                    'extraction_info': {
                        'keyword': keyword,
                        'location': location,
                        'start_time': extraction_status['start_time'].isoformat(),
                        'last_updated': datetime.now().isoformat(),
                        'status': 'extracting_details',
                        'completed_jobs': extraction_status['completed_jobs'],
                        'total_jobs': len(jobs_to_process)
                    },
                    'jobs': detailed_jobs
                }
                
                with open(detailed_filename, 'w', encoding='utf-8') as f:
                    json.dump(detailed_data, f, ensure_ascii=False, indent=2)
                
                # Update progress file
                progress_data.update({
                    'completed_jobs': extraction_status['completed_jobs'],
                    'progress_percentage': (extraction_status['completed_jobs'] / len(jobs_to_process)) * 100,
                    'current_job': job.get('title', 'Unknown'),
                    'last_updated': datetime.now().isoformat()
                })
                
                with open(progress_filename, 'w', encoding='utf-8') as f:
                    json.dump(progress_data, f, ensure_ascii=False, indent=2)
                
                # Emit real-time update with job data
                socketio.emit('job_extracted', {
                    'job': detailed_job,
                    'index': i,
                    'progress': extraction_status['progress'],
                    'completed': extraction_status['completed_jobs'],
                    'total': len(jobs_to_process)
                })
                
                # Force flush the socket
                socketio.sleep(0.1)
                
            except Exception as e:
                extraction_status['errors'] += 1
                error_job = {
                    'search_info': job,
                    'error': str(e),
                    'source_url': job_url,
                    'extracted_at': datetime.now().isoformat(),
                    'extraction_order': i
                }
                detailed_jobs.append(error_job)
                
                # Update files even for errors
                detailed_data = {
                    'extraction_info': {
                        'keyword': keyword,
                        'location': location,
                        'start_time': extraction_status['start_time'].isoformat(),
                        'last_updated': datetime.now().isoformat(),
                        'status': 'extracting_details',
                        'completed_jobs': extraction_status['completed_jobs'],
                        'total_jobs': len(jobs_to_process),
                        'errors': extraction_status['errors']
                    },
                    'jobs': detailed_jobs
                }
                
                with open(detailed_filename, 'w', encoding='utf-8') as f:
                    json.dump(detailed_data, f, ensure_ascii=False, indent=2)
                
                # Update progress file
                progress_data.update({
                    'errors': extraction_status['errors'],
                    'last_updated': datetime.now().isoformat(),
                    'current_job': f"Error: {job.get('title', 'Unknown')}"
                })
                
                with open(progress_filename, 'w', encoding='utf-8') as f:
                    json.dump(progress_data, f, ensure_ascii=False, indent=2)
                
                socketio.emit('job_error', {
                    'job': job,
                    'error': str(e),
                    'index': i
                })
        
        # Save final results
        final_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Final update to detailed jobs file
        final_detailed_data = {
            'extraction_info': {
                'keyword': keyword,
                'location': location,
                'start_time': extraction_status['start_time'].isoformat(),
                'completed_at': datetime.now().isoformat(),
                'status': 'completed',
                'completed_jobs': extraction_status['completed_jobs'],
                'total_jobs': len(jobs_to_process),
                'errors': extraction_status['errors']
            },
            'jobs': detailed_jobs
        }
        
        with open(detailed_filename, 'w', encoding='utf-8') as f:
            json.dump(final_detailed_data, f, ensure_ascii=False, indent=2)
        
        # Update progress file to completed
        progress_data.update({
            'status': 'completed',
            'completed_at': datetime.now().isoformat(),
            'progress_percentage': 100,
            'current_job': 'Extraction completed'
        })
        
        with open(progress_filename, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
        
        # Save summary
        summary = {
            'search_info': {
                'keyword': keyword,
                'location': location,
                'search_timestamp': extraction_status['start_time'].isoformat(),
                'search_url': url
            },
            'results_summary': {
                'total_jobs_found': len(jobs),
                'total_jobs_processed': len(jobs_to_process),
                'successful_extractions': extraction_status['completed_jobs'],
                'failed_extractions': extraction_status['errors']
            },
            'files_created': {
                'basic_listings': search_filename,
                'detailed_info': detailed_filename,
                'progress_file': progress_filename,
                'extraction_folder': folders['base']
            },
            'extraction_id': extraction_status['extraction_id']
        }
        
        summary_filename = f"{folders['results']}/summary_{timestamp}.json"
        with open(summary_filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # Cleanup
        cleanup_temp_files(folders)
        
        extraction_status['active'] = False
        
        print(f"Emitting extraction_complete event with summary: {type(summary)}")
        socketio.emit('extraction_complete', {
            'summary': summary,
            'total_time': (datetime.now() - extraction_status['start_time']).total_seconds()
        })
        print("extraction_complete event emitted successfully")
        
    except Exception as e:
        print(f"Exception in scrape_jobs_with_details: {str(e)}")
        extraction_status['active'] = False
        socketio.emit('extraction_error', {
            'error': str(e)
        })
        print("extraction_error event emitted")
    finally:
        try:
            if driver:
                driver.quit()
                print("Driver quit successfully")
        except Exception as e:
            print(f"Error quitting driver: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_extraction', methods=['POST'])
def start_extraction():
    if extraction_status['active']:
        return jsonify({'error': 'Extraction already in progress'}), 400
    
    data = request.get_json()
    keyword = data.get('keyword')
    location = data.get('location')
    max_jobs = data.get('max_jobs')
    
    if not keyword or not location:
        return jsonify({'error': 'Keyword and location are required'}), 400
    
    # Start extraction in background thread
    thread = threading.Thread(target=scrape_jobs_with_details, args=(keyword, location, max_jobs))
    thread.daemon = True
    thread.start()
    
    # Wait a brief moment for extraction_id to be set
    time.sleep(0.5)
    
    return jsonify({
        'message': 'Extraction started',
        'extraction_id': extraction_status.get('extraction_id', ''),
        'timestamp': extraction_status.get('timestamp', '')
    })

@app.route('/status')
def get_status():
    return jsonify(extraction_status)

@app.route('/debug/extraction/<extraction_id>')
def debug_extraction(extraction_id):
    """Debug endpoint to see raw extraction data"""
    try:
        extraction_path = f"extractions/{extraction_id}"
        results_path = f"{extraction_path}/results"
        
        debug_info = {
            'extraction_id': extraction_id,
            'path': extraction_path,
            'exists': os.path.exists(extraction_path),
            'results_path': results_path,
            'results_exists': os.path.exists(results_path),
            'files': []
        }
        
        if os.path.exists(results_path):
            for file in os.listdir(results_path):
                if file.endswith('.json'):
                    file_path = f"{results_path}/{file}"
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            debug_info['files'].append({
                                'filename': file,
                                'type': type(data).__name__,
                                'size': len(data) if isinstance(data, (list, dict)) else 1,
                                'keys': list(data.keys()) if isinstance(data, dict) else None,
                                'sample': str(data)[:500] + '...' if len(str(data)) > 500 else str(data)
                            })
                    except Exception as e:
                        debug_info['files'].append({
                            'filename': file,
                            'error': str(e)
                        })
        
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug/reset_status', methods=['POST'])
def reset_status():
    """Debug endpoint to reset extraction status"""
    global extraction_status
    extraction_status.update({
        'active': False,
        'progress': 0,
        'current_job': '',
        'total_jobs': 0,
        'completed_jobs': 0,
        'errors': 0,
        'keyword': '',
        'location': '',
        'start_time': None,
        'results': []
    })
    return jsonify({'message': 'Status reset successfully'})

@app.route('/extraction_progress/<extraction_id>')
def get_extraction_progress(extraction_id):
    """Get real-time progress by reading the progress file"""
    try:
        # Find the progress file for this extraction
        extraction_dir = f"extractions/{extraction_id}"
        if not os.path.exists(extraction_dir):
            return jsonify({'error': 'Extraction not found'}), 404
        
        # Look for progress file
        results_dir = f"{extraction_dir}/results"
        if not os.path.exists(results_dir):
            return jsonify({'error': 'Results directory not found'}), 404
        
        progress_file = None
        for file in os.listdir(results_dir):
            if file.startswith('extraction_progress_') and file.endswith('.json'):
                progress_file = f"{results_dir}/{file}"
                break
        
        if not progress_file or not os.path.exists(progress_file):
            return jsonify({'error': 'Progress file not found'}), 404
        
        # Read progress data
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)
        
        return jsonify(progress_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extraction_jobs/<extraction_id>')
def get_extraction_jobs(extraction_id):
    """Get current jobs data by reading the detailed jobs file"""
    try:
        # Find the detailed jobs file for this extraction
        extraction_dir = f"extractions/{extraction_id}"
        if not os.path.exists(extraction_dir):
            return jsonify({'error': 'Extraction not found'}), 404
        
        results_dir = f"{extraction_dir}/results"
        if not os.path.exists(results_dir):
            return jsonify({'error': 'Results directory not found'}), 404
        
        detailed_file = None
        for file in os.listdir(results_dir):
            if file.startswith('jobs_detailed_') and file.endswith('.json'):
                detailed_file = f"{results_dir}/{file}"
                break
        
        if not detailed_file or not os.path.exists(detailed_file):
            return jsonify({'error': 'Detailed jobs file not found'}), 404
        
        # Read jobs data
        with open(detailed_file, 'r', encoding='utf-8') as f:
            jobs_data = json.load(f)
        
        return jsonify(jobs_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/results/<path:filename>')
def download_file(filename):
    return send_from_directory('extractions', filename, as_attachment=True)

@app.route('/extractions')
def list_extractions():
    """List all available extractions"""
    try:
        from file_manager import FileManager
        fm = FileManager()
        extractions = fm.list_extractions()
        return jsonify(extractions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extractions/<extraction_id>')
def get_extraction_details(extraction_id):
    """Get details of a specific extraction"""
    try:
        from file_manager import FileManager
        fm = FileManager()
        details = fm.get_extraction_summary(extraction_id)
        return jsonify(details)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extractions/<extraction_id>/results')
def get_extraction_results(extraction_id):
    """Get the results of a specific extraction"""
    try:
        extraction_path = f"extractions/{extraction_id}"
        if not os.path.exists(extraction_path):
            return jsonify({'error': 'Extraction not found'}), 404
        
        results_path = f"{extraction_path}/results"
        files = []
        
        if os.path.exists(results_path):
            for file in os.listdir(results_path):
                if file.endswith('.json') and not file.startswith('extraction_progress'):
                    file_path = f"{results_path}/{file}"
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                            # Extract jobs from the data structure
                            jobs = []
                            if isinstance(data, list):
                                jobs = data
                            elif isinstance(data, dict):
                                if 'jobs' in data:
                                    jobs = data['jobs']
                                elif 'results' in data:
                                    jobs = data['results']
                                elif file.startswith('jobs_detailed_') or file.startswith('jobs_search_'):
                                    # These files might have job data even if not in 'jobs' key
                                    jobs = [data] if data else []
                                else:
                                    jobs = []  # Summary or other files
                            
                            # Filter out empty jobs and null entries
                            jobs = [job for job in jobs if job and isinstance(job, dict) and job.get('job_title') or job.get('title')]
                            
                            files.append({
                                'filename': file,
                                'data': data,
                                'jobs': jobs,
                                'size': len(jobs)
                            })
                    except Exception as e:
                        print(f"Error reading file {file}: {e}")
                        files.append({
                            'filename': file,
                            'error': str(e),
                            'jobs': [],
                            'size': 0
                        })
        
        return jsonify({
            'extraction_id': extraction_id,
            'files': files
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extractions/<extraction_id>', methods=['DELETE'])
def delete_extraction(extraction_id):
    """Delete an extraction and all its files"""
    try:
        from file_manager import FileManager
        fm = FileManager()
        fm.delete_extraction(extraction_id)
        return jsonify({'message': 'Extraction deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extractions/<extraction_id>/export/<format>')
def export_extraction(extraction_id, format):
    """Export extraction results in different formats"""
    try:
        from file_manager import FileManager
        fm = FileManager()
        
        if format not in ['json', 'csv']:
            return jsonify({'error': 'Unsupported format. Use json or csv'}), 400
        
        file_path = fm.export_results(extraction_id, format)
        return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path), as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cleanup')
def cleanup_old_extractions():
    """Clean up old extractions (older than 7 days)"""
    try:
        from file_manager import FileManager
        fm = FileManager()
        deleted_count = fm.cleanup_old_extractions(days=7)
        return jsonify({
            'message': f'Cleaned up {deleted_count} old extractions',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history')
def history():
    """Render the extraction history page"""
    return render_template('history.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'data': 'Connected to job scraper'})

@socketio.on('test_event')
def handle_test_event(data):
    print(f'Test event received: {data}')
    emit('test_response', {'message': 'Socket connection working!'})

if __name__ == '__main__':
    os.makedirs('extractions', exist_ok=True)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
