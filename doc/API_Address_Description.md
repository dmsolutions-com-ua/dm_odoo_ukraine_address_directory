### GET Address

https://api.dmsolutions.com.ua:2661/api/Address?sLang=ru_RU&sRequest=город Киев ул. Маккейна Джона (ул. Кудри Ивана) 1
For one line address input. Shows suggestions from partial address.

Для введення адреси одним рядком. Повертає підказки по неповній адресі.
У полі "Area" зазначено актуальну назву району. У полі "AreaOld" зазначено назву району до реформи 2020р. Якщо раніше нас. пункт не підпорядковувався району - "AreaOld" буде "null".
AUTHORIZATIONBearer Token

This request is using Bearer Token from collection[Geodata.online](https://documenter.getpostman.com/view/2267163/7E8jGij?version=latest#auth-info-ccb379d0-eaf8-5b05-a8fe-83d4a6c073aa)

HEADERS

Authorization

Bearer {{token}}

PARAMS

sLang

ru_RU

response language (default ukrainian). Вибір мови (якщо не вказано - українська)

sRequest

город Киев ул. Маккейна Джона (ул. Кудри Ивана) 1

Start typing address (city, street, house)
