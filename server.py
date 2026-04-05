import requests

url = 'https://fdsdsgdsgsgs.b-cdn.net/api/v1/search?q='

q = input('What is your search?')

response = requests.get(url + q)

print(response.json())
