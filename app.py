import streamlit as st
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import time
import re

def load_proxies(uploaded_file):
    if 'proxies' not in st.session_state:
        st.session_state.proxies = uploaded_file.getvalue().decode().splitlines()
    return st.session_state.proxies

def get_proxies(proxy):
    return {
        "http": proxy,
        "https": proxy,
    }

def is_valid_proxy(p):
    return re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}", p) is not None

def check_proxy(proxy, num_tests=3):
    if not is_valid_proxy(proxy):
        return proxy, float('inf'), float('inf'), 'Invalid format'

    ping_url = "http://mojeip.net.pl/asdfa/azenv.php"
    download_url = "http://ipv4.download.thinkbroadband.com/5MB.zip"
    
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.1, status_forcelist=[ 500, 502, 503, 504 ])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    ping_times = []
    download_speeds = []

    for i in range(num_tests):
        try:
            start_ping = time.time()
            ping_response = session.get(ping_url, proxies=get_proxies(proxy), timeout=10)
            ping_time = time.time() - start_ping if ping_response.status_code == 200 else float('inf')
            ping_times.append(ping_time)
        except (requests.exceptions.RequestException) as e:
            return proxy, float('inf'), float('inf'), str(e)

        try:
            start_download = time.time()
            download_response = session.get(download_url, proxies=get_proxies(proxy), timeout=20, stream=True)
            download_time = time.time() - start_download
            total_length = int(download_response.headers.get('content-length', 0))
            download_speed = (total_length / download_time) / (1024 * 1024) if total_length else float('inf')
            download_speeds.append(download_speed)
        except (requests.exceptions.RequestException) as e:
            return proxy, float('inf'), float('inf'), str(e)

    avg_ping_time = sum(ping_times) / len(ping_times) if ping_times else float('inf')
    avg_download_speed = sum(download_speeds) / len(download_speeds) if download_speeds else float('inf')

    return proxy, avg_ping_time, avg_download_speed, 'Success' if avg_ping_time != float('inf') and avg_download_speed != float('inf') else 'Failure'

def main():
    st.title('Proxy Server Speed Checker')
    uploaded_file = st.file_uploader("Choose a .txt file", type="txt")
    input_proxies = st.text_area("Or paste your proxies here")
    download_speed_threshold = st.number_input('Enter minimum average download speed (MB/s)', min_value=0.0, value=1.0)
    
    proxies = []
    if uploaded_file is not None:
        proxies = load_proxies(uploaded_file)
    elif input_proxies != "":
        proxies = input_proxies.splitlines()

    if proxies:
        data = []
        successful_proxies = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check_proxy, proxy): proxy for proxy in proxies}
            progress_bar = st.progress(0)
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                data.append(result)
                if result[3] == 'Success' and result[2] >= download_speed_threshold:
                    successful_proxies.append(result[0])
                progress_bar.progress((i + 1) / len(proxies))
        
        # Save successful proxies to a .txt file
        with open('successful_proxies.txt', 'w') as f:
            for proxy in successful_proxies:
                f.write(f"{proxy}\n")

        df = pd.DataFrame(data, columns=['Proxy', 'Avg Ping (s)', 'Avg Download Speed (MB/s)', 'Status'])
        st.write(df)


if __name__ == "__main__":
    main()
