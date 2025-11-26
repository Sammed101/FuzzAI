import requests

# Make a GET request to the given URL
# Returns: (status_code, response_length)
def make_request(url):
    try:
        response = requests.get(url, timeout=5)
        status_code = response.status_code
        response_length = len(response.content)
        return status_code, response_length
    except requests.exceptions.Timeout:
        # Timeout occurred
        return 'TIMEOUT', 0
    except requests.exceptions.RequestException as e:
        # Other request errors
        return f'ERROR', 0
