import requests
x = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'
response = requests.get('https://39d33ac4-dd56-435e-9f77-ad8ba6b87376.modelrun.inference.cloud.ru/')
#response = requests.get(x, verify=False)     

print("Статус ответа:", response)
print("Содержимое ответа (текст):")
print(response.text)
print("\nЗаголовки ответа:")
print(response.headers)