from neo4j.v1 import GraphDatabase
import requests


class DataBase(object):
    def __init__(self, username, password, url="bolt://localhost:7687"):
        self.neo_url = url
        self.neo_driver = GraphDatabase.driver(self.neo_url, auth=(username, password))
        self.session = self.neo_driver.session()
        self.tx = self.session.begin_transaction()
        print("init DBneo4j success!")

    def __exit__(self, *args):
        self.tx.close()
        self.session.close()
        self.neo_driver.close()

    def execute(self, neo_sql, args):
        print("execute sql begin : %s" % neo_sql)
        records = self.tx.run(neo_sql, args)
        print("execute sql success")
        return [record for record in records]


class Spider(object):
    def __init__(self, host, verify=False):
        self.host = host
        self.req = requests.session()
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)Chrome/59.0.3071.115 Safari/537.36",
            "Referer": host
        }
        self.verify = verify
        if "https:" in host:
            self.isSSL = True

    def __exit__(self, *args):
        self.req.close()

    def get(self, path=None, params=None, is_json=False, headers=None):
        url = self.host + path
        headers = dict(headers, **self.header)
        return self.execute(url, params=params, headers=headers, is_json=is_json, method="GET")

    def post(self, path=None, params=None, headers=None, is_json=True):
        url = self.host + path
        headers = dict(headers, **self.header)
        return self.execute(url, params=params, headers=headers, is_json=is_json, method="POST")

    def execute(self, url, params, headers, is_json, method="GET"):
        result = ""
        if method == "GET":
            if self.isSSL:
                s = self.req.get(url, params=params, headers=headers, verify=self.verify)
            else:
                s = self.req.get(url, params=params, headers=headers)
        else:
            if self.isSSL:
                s = self.req.post(url, json=params, headers=headers, verify=self.verify)
            else:
                s = self.req.post(url, json=params, headers=headers)
        if s.status_code == 200:
            if is_json:
                result = s.json()
            else:
                result = s.text
        return result

    def get_req(self):
        return self.req
