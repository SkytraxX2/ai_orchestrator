import requests
class API:
    def __init__(self,url): self.url=url
    def get(self,path): return requests.get(f"{self.url}/{path}").json()
