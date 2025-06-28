# 🚀 WellScraper - Modern Job Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![Selenium](https://img.shields.io/badge/Selenium-4.0+-orange.svg)](https://selenium.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **A powerful, user-friendly job scraper for Wellfound (formerly AngelList) with a beautiful web interface, real-time extraction, and comprehensive job data management.**

![WellScraper Dashboard](https://github.com/user-attachments/assets/95880c8e-c14d-4f26-8d59-370570f55583)


## ✨ Features

### 🎯 **Smart Job Extraction**
- **Dual-phase scraping**: Search listings + detailed job information
- **CAPTCHA handling**: Automatic detection and manual resolution prompts
- **Rate limiting**: Respectful scraping with proper delays
- **Error recovery**: Robust error handling and retry mechanisms

### 🌐 **Beautiful Web Interface**
- **Real-time dashboard**: Live progress tracking with WebSocket updates
- **Job visualization**: Beautiful job cards with company logos and details
- **Historical management**: Complete CRUD operations for past extractions
- **Responsive design**: Works perfectly on desktop, tablet, and mobile

### 📊 **Comprehensive Data Management**
- **Multiple formats**: Export to JSON, CSV for analysis
- **Rich job data**: Company details, descriptions, requirements, benefits
- **Organized storage**: Automatic folder structure with debug files
- **Smart cleanup**: Automated old extraction management

### 🔧 **Developer-Friendly**
- **Modular architecture**: Clean, maintainable codebase
- **Extensive logging**: Debug information and extraction tracking
- **Configuration**: Easy customization of scraping parameters
- **Documentation**: Comprehensive guides and examples

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Chrome browser (for Selenium)
- Windows/Linux/macOS

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/chungus1310/wellscraper.git
   cd wellscraper
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Open your browser**
   ```
   http://localhost:5000
   ```

That's it! 🎉 You're ready to start scraping jobs.

## 📖 Usage Guide

### 🔍 **Starting a Job Search**

1. **Navigate to the main dashboard** at `http://localhost:5000`
2. **Enter your search criteria**:
   - **Keyword**: `software engineer`, `product manager`, `data scientist`, etc.
   - **Location**: `san francisco`, `new york`, `remote`, `america`, etc.
3. **Click "Start Extraction"** and watch the magic happen!

### 📊 **Real-time Monitoring with Style**

Watch your extraction progress in real-time:
- **Live job cards** appearing as they're scraped
- **Progress indicators** showing completion status
- **Error notifications** for any issues encountered
- **Statistics dashboard** with job counts and timing

### 📁 **Managing Results**

Visit the **History page** to:
- **View all extractions** with metadata and job counts
- **Download results** in JSON or CSV format
- **Preview job details** with comprehensive information
- **Delete old extractions** to save space
- **Bulk cleanup** of old data

### 🔧 **Advanced Features**

#### **Command Line Interface**
For power users, use the CLI script:
```bash
python job_scraper_complete.py --keyword "software engineer" --location "san francisco"
```

#### **Batch Processing**
Create multiple searches programmatically:
```python
from job_scraper_complete import WellfoundScraper

scraper = WellfoundScraper()
scraper.scrape_jobs("python developer", "remote")
```

## 📁 Project Structure

```
wellscraper/
├── 🌐 app.py                    # Flask web application with enhanced routes
├── 🤖 job_scraper_complete.py   # Main scraper engine (unchanged)
├── 📁 file_manager.py           # File operations & cleanup
├── 📋 requirements.txt          # Python dependencies
├── 🚀 start_scraper.bat         # Windows launcher
├── 📖 README.md                 # Updated documentation
├── 🎨 REVAMP_PLAN.md            # UI revamp tracking and notes
├── 📁 templates/               # Modern web interface templates
│   ├── 🏠 index.html           # Glassmorphic main dashboard
│   ├── 🏠 index_old.html       # Original design backup
│   ├── 📊 history.html         # Enhanced results management
│   └── 📊 history_old.html     # Original history backup
├── 📁 static/                  # Enhanced static assets
│   ├── 🎨 theme.css            # Modern glassmorphic styling
│   └── 📁 assets/              # Custom SVG icon collection
│       ├── 🔍 search-icon.svg  # Animated search icon
│       ├── 📈 history-icon.svg # History navigation icon
│       ├── 📥 download-icon.svg # Download action icon
│       ├── 🔄 refresh-icon.svg  # Refresh/reload icon
│       └── 🚀 logo.svg         # WellScraper brand logo
├── 📁 extractions/             # Scraped data storage
│   └── 📅 [keyword]_[location]_[timestamp]/
│       ├── 📁 results/         # JSON/CSV outputs
│       └── 📁 debug/           # Logs & debug files
├── 📁 .github/                 # GitHub workflows and templates
└── 📁 __pycache__/             # Python cache files
```

## 🎨 UI Features & Theming

### Design System
- **Theme**: Modern Data Mining/Tech Interface
- **Primary Colors**: Dark navy (#0A0E1A), Slate (#1A1F2E)
- **Accent Colors**: Neon cyan (#00D4FF), Electric blue (#0099CC)
- **Typography**: Inter for UI text, JetBrains Mono for code snippets
- **Effects**: Glassmorphism, smooth animations, micro-interactions

### Custom SVG Assets
All icons are custom-designed SVG graphics optimized for:
- **Scalability**: Crystal clear at any size
- **Performance**: Lightweight and fast loading
- **Consistency**: Unified design language
- **Accessibility**: Proper contrast and screen reader support

## ⚙️ Configuration

### Environment Variables
```bash
# Optional: Customize scraping behavior
export SCRAPER_DELAY=2          # Delay between requests (seconds)
export SCRAPER_TIMEOUT=30       # Page load timeout (seconds)
export SCRAPER_HEADLESS=true    # Run browser in headless mode

# Optional: UI customization
export WELLSCRAPER_THEME=dark   # Default theme (dark/light)
export ENABLE_ANIMATIONS=true   # Enable/disable UI animations
```

### Scraping Parameters
Edit `job_scraper_complete.py` to customize scraping behavior:
```python
# Timing configuration
DELAY_BETWEEN_JOBS = 2          # Seconds between job extractions
PAGE_LOAD_TIMEOUT = 30          # Maximum page load wait time
SEARCH_RESULTS_LIMIT = 100      # Maximum jobs to extract per search

# Browser configuration
HEADLESS_MODE = False           # Set to True for background operation
WINDOW_SIZE = (1920, 1080)      # Browser window dimensions
```

### UI Customization
The new interface can be customized via CSS custom properties in `static/theme.css`:
```css
:root {
  --primary-bg: #0A0E1A;        # Main background color
  --secondary-bg: #1A1F2E;      # Card/panel backgrounds
  --accent-primary: #00D4FF;    # Primary accent (cyan)
  --accent-secondary: #0099CC;  # Secondary accent (blue)
  --animation-speed: 0.3s;      # Global animation duration
  --glassmorphism-blur: 10px;   # Backdrop blur intensity
}
```

## 🗃️ Data Structure

### Search Results (`jobs_search_*.json`)
```json
{
  "title": "Senior Software Engineer",
  "company": "TechCorp",
  "location": "San Francisco",
  "type": "Full-time",
  "link": "https://wellfound.com/jobs/...",
  "company_desc": "Building the future...",
  "company_size": "51-200 Employees"
}
```

### Detailed Results (`jobs_detailed_*.json`)
```json
{
  "title": "Senior Software Engineer",
  "company": {
    "name": "TechCorp",
    "description": "Building the future...",
    "tags": ["B2B", "Scale Stage"],
    "link": "https://wellfound.com/company/..."
  },
  "location": "San Francisco",
  "employment_type": "Full Time",
  "description": {
    "full_text": "We are looking for...",
    "sections": {
      "overview": ["Company description..."],
      "requirements": ["5+ years experience..."]
    }
  },
  "apply_link": "https://wellfound.com/jobs/.../apply",
  "visa_sponsorship": "Available",
  "extracted_at": "2025-06-29T10:30:00Z"
}
```

## 🛠️ Development

### Running in Development Mode
```bash
# Enable debug mode with hot reload
export FLASK_ENV=development
export FLASK_DEBUG=true
python app.py
```

### Customizing the UI
1. **Edit themes**: Modify CSS custom properties in `static/theme.css`
2. **Add animations**: Extend the animation library in the CSS file
3. **Create new icons**: Add SVG files to `static/assets/`
4. **Modify layouts**: Update HTML templates in `templates/`

### Testing UI Changes
```bash
# Watch for CSS changes during development
# The browser will automatically reflect styling updates
# Test responsive design using browser dev tools
```

### Adding New Features
1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** with proper testing
4. **Commit your changes**: `git commit -m 'Add amazing feature'`
5. **Push to the branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**


## 🤝 Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

### Ways to Contribute
- 🐛 **Report bugs** via GitHub Issues
- 💡 **Suggest features** for enhancement
- 📖 **Improve documentation** and examples
- 🔧 **Submit code improvements** via Pull Requests
- ⭐ **Star the repository** to show support

### Contribution Guidelines
1. Ensure your code follows the existing style
2. Add tests for new functionality
3. Update documentation as needed
4. Keep commits focused and descriptive



## ❓ FAQ

### **Q: Is this legal?**
A: Yes! This scraper respects robots.txt, implements rate limiting, and follows ethical scraping practices. Always review website terms of service.

### **Q: How fast is the scraping?**
A: The scraper processes approximately 10-15 jobs per minute to be respectful to the server. Speed can be adjusted in configuration.

### **Q: Can I run this on a server?**
A: Absolutely! Set `HEADLESS_MODE = True` for server deployment. Works great on cloud platforms.

### **Q: What if I encounter CAPTCHAs?**
A: The scraper automatically detects CAPTCHAs and prompts you to solve them manually. It then continues automatically.

### **Q: Can I customize the data extracted?**
A: Yes! The scraper architecture is modular. You can easily modify the extraction logic in `job_scraper_complete.py`.

## 🔧 Troubleshooting

### Common Issues

#### **Chrome Driver Issues**
```bash
# Update Chrome and chromedriver
pip install --upgrade selenium
# Ensure Chrome browser is updated
```

#### **Permission Errors**
```bash
# On Windows, run as Administrator
# On Linux/Mac, check file permissions
chmod +x start_scraper.bat
```

#### **Network Timeouts**
```python
# Increase timeout in configuration
PAGE_LOAD_TIMEOUT = 60  # Increase from 30 to 60 seconds
```

#### **Memory Issues**
```python
# Reduce batch size for large extractions
BATCH_SIZE = 10  # Process fewer jobs at once
```

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## 🙏 Acknowledgments

- **[Selenium](https://selenium.dev)** - Web automation framework
- **[Flask](https://flask.palletsprojects.com/)** - Web application framework
- **[Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/)** - HTML parsing
- **[Wellfound](https://wellfound.com)** - Amazing platform for startup jobs



---

<div align="center">

**Built with ❤️ by [Chun](https://github.com/chungus1310)**

**WellScraper - Where modern design meets powerful job intelligence! 🚀**

**If you found this project helpful, please consider giving it a ⭐!**

[⬆ Back to Top](#-wellscraper---modern-job-intelligence-platform)

</div>
