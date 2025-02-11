import os
import time
import pyperclip
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

app = Flask(__name__)
socketio = SocketIO(app)
driver = None  # WebDriver instance


def initialize_driver():
    """Initialize Selenium WebDriver (Headless Chrome)"""
    global driver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)


def get_xpath(element):
    """Generate unique XPath for an element"""
    script = '''
    function getElementXPath(element) {
        if (element.id !== '')
            return '//*[@id="' + element.id + '"]';
        if (element === document.body)
            return element.tagName;

        let ix = 0;
        const siblings = element.parentNode.childNodes;

        for (let i = 0; i < siblings.length; i++) {
            const sibling = siblings[i];
            if (sibling === element)
                return getElementXPath(element.parentNode) + '/' + element.tagName + '[' + (ix + 1) + ']';
            if (sibling.nodeType === 1 && sibling.tagName === element.tagName)
                ix++;
        }
    }
    return getElementXPath(arguments[0]);
    '''
    return driver.execute_script(script, element)


@app.route('/')
def index():
    """Render Home Page"""
    return render_template('index.html')


@app.route('/scrape', methods=['POST'])
def scrape():
    """Scrape elements from a webpage"""
    global driver
    data = request.json
    url = data.get('url', '').strip()

    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    try:
        if not driver:
            initialize_driver()
        driver.get(url)
        time.sleep(3)  # Wait for the page to load

        elements = driver.find_elements(By.XPATH, '''
            //a | //button | //input | //textarea | //select |
            //img | //h1 | //h2 | //h3 | //h4 | //h5 | //h6
        ''')

        element_list = []
        for element in elements:
            tag_name = element.tag_name.lower()
            element_type = element.get_attribute('type') or ''
            element_text = element.text.strip()[:50]
            xpath = get_xpath(element)

            element_list.append({
                'tag': tag_name,
                'type': element_type,
                'text': element_text,
                'xpath': xpath
            })

        return jsonify({'status': 'success', 'elements': element_list})

    except WebDriverException as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/copy_xpath', methods=['POST'])
def copy_xpath():
    """Copy XPath to clipboard"""
    data = request.json
    xpath = data.get('xpath', '')

    if xpath:
        pyperclip.copy(xpath)
        return jsonify({'status': 'success', 'message': 'XPath copied!'})

    return jsonify({'status': 'error', 'message': 'No XPath provided'})


@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Shutdown the WebDriver"""
    global driver
    if driver:
        driver.quit()
        driver = None
    return jsonify({'status': 'success', 'message': 'WebDriver closed'})


if __name__ == "__main__":
    socketio.run(app, debug=True)
