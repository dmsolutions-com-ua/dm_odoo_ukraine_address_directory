### GET Houses

https://api.dmsolutions.com.ua:2661/api/Houses?sRequest=8&houseMoniker=80e06ff6-f477-404f-8bea-1e8c531c8d8d&sLang=uk_UA

Search for houses by house number for particular street defined by houseMoniker from Streets response. Moniker lives for 15 min.

Метод получения списка номеров домов по начальным символам для конкртеной улицы, указывая houseMoniker, полученный в реквесте по улицам (Streets) Важно! Время жизни моникера, полученного после запроса по улицам - 15 минут. Возвращает объект в формате JSON.

В разі протермінування монікера ви отримаєте помилку з кодом 400 та JSON об'єктом:

> {
> "message": "Moniker expired"
> }

В разі якщо нічого не знайдено за вказаними параметрами - код 400 та JSON об'єктом:

> {
> "message": "Nothing found"
> }

Response:

У полі "House**String**" зібрано найбільш потрібну інформацію для точної ідентифікації будинку. Призначення цього поля - наповнення випадаючих списків з підказками варіантів. Напр.:

`"8Б"`
Тут буде об'єднано значення полів HouseNum, HouseNumAdd. **Формат і склад цього текстового рядка може коригуватися в майбутньому**. За потреби можна зібрати аналогічний рядок на свій власний смак з полів JSON відповіді.

AUTHORIZATIONBearer Token

This request is using Bearer Token from collection[Geodata.online](https://documenter.getpostman.com/view/2267163/7E8jGij?version=latest#auth-info-ccb379d0-eaf8-5b05-a8fe-83d4a6c073aa)

HEADERS

Authorization

Bearer {{token}}

PARAMS

sRequest

8

house number

houseMoniker

80e06ff6-f477-404f-8bea-1e8c531c8d8d

Required

sLang

uk_UA

Response language: uk, ru, en (uk default). Выбор языка выдачи (по умолчанию украинский)