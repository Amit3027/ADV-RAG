import requests

def main():
    try:
        resp = requests.get('http://localhost:8502/')
        print('Status code:', resp.status_code)
        if resp.status_code == 200:
            print('Streamlit app is reachable.')
        else:
            print('Unexpected status code.')
    except Exception as e:
        print('Error contacting Streamlit app:', e)

if __name__ == '__main__':
    main()
