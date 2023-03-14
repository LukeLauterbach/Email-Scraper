<div id="top"></div>

<h3 align="center">Email Scraper</h3>

  <p align="center">
    <a href="https://github.com/LukeLauterbach/Email-Scraper">View Demo</a>
    ·
    <a href="https://github.com/LukeLauterbach/Email-Scraper/issues">Report Bug</a>
    ·
    <a href="https://github.com/LukeLauterbach/Email-Scraper/issues">Request Feature</a>
  </p>
</div>


<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#options">Options</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

This script will automatically spider a website, hunting for email addresses on each page. A database of scraped URLs will be kept with the status of if these pages have been scraped, allowing spidering to continue at a later time.

![image](https://user-images.githubusercontent.com/104774644/225120128-d68bc49a-9049-4a9d-9107-276e8d24b960.png)


### Built With

* [Python](https://www.python.org/)


<p align="right">(<a href="#top">back to top</a>)</p>



<!-- GETTING STARTED -->
## Getting Started

This script relies on Google's Programmable Search Engine, which will require a short setup in order to get an ID and API key. After initial setup is complete, running the script is a simple command.

## Usage

```shell
python3 emailScraper.py -e [EMAIL DOMAIN] -p [INITIAL PAGE TO SCRAPE] 
```

## Options
Options | Description
-|-
-h | Help Menu
-e | Email domain to look for
-p | Root page to start searching
-n | Number of pages to spider (optional)
-o | Output filename (will default to the email domain name)
-d | Add a delay between web requests
-db | Debug Mode

<p align="right">(<a href="#top">back to top</a>)</p>
