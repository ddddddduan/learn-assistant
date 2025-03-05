import json

def video_config():
    with open('../conf/config.json', 'r') as f:
        config = json.load(f)

    base_url = config['romte']['base_url']
    access_token = config['auth']['access_token']
    db_path = config['db']['db_path']

    return base_url,access_token,db_path

if __name__ == '__main__':
    base_url,access_token,db_path = video_config()
    print(base_url)