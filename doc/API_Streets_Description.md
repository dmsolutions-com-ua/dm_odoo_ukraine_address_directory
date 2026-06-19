### GET Streets

https://api.dmsolutions.com.ua:2661/api/Streets?sRequest=шевч&stMoniker=3d89c719-2c33-4fe6-bf39-d49ad20c7ba0&sLang=uk_UA

Search streets by first letters and **stMoniker** from Citites response. Moniker lifetime is 15 minutes. Returns JSON object.

Метод пошуку вулиць за початковими символами для конкретного міста, вказуючи stMoniker, отриманий у відповіді по містах (Cities). Час життя монікера - 15 хв. Повертає об'єкт JSON.

В разі протермінування монікера ви отримаєте помилку з кодом 400 та JSON об'єктом:

> {
> "message": "Moniker expired"
> }

В разі якщо нічого не знайдено за вказаними параметрами - код 400 та JSON об'єктом:

> {
> "message": "Nothing found"
> }

Response:

У полі "**StreetString**" зібрано найбільш потрібну інформацію для точної ідентифікації вулиці. Призначення цього поля - наповнення випадаючих списків з підказками варіантів. Напр.:

`"вул. Шевченка"`

Тут буде вказано тип вулиці, назву, стару назву в дужках за наявності. **Формат і склад цього текстового рядка може коригуватися в майбутньому**. За потреби можна зібрати аналогічний рядок на свій власний смак з полів JSON відповіді.

AUTHORIZATIONBearer Token

This request is using Bearer Token from collection[Geodata.online](https://documenter.getpostman.com/view/2267163/7E8jGij?version=latest#auth-info-ccb379d0-eaf8-5b05-a8fe-83d4a6c073aa)

HEADERS

Authorization

Bearer {{token}}

PARAMS

sRequest

шевч

street name

stMoniker

3d89c719-2c33-4fe6-bf39-d49ad20c7ba0

Required

sLang

uk_UA

Response language: uk, ru, en (uk by default). Выбор языка выдачи (по умолчанию украинский)