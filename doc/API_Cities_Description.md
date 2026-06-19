### GET Cities

https://api.dmsolutions.com.ua:2661/api/Cities?sRequest=Тарас&sRegion=Микол

Search for cities by first letters, or postal code| KOATUU code| KATOTTG code. Parameters sRequest and sPostCode cannot be used simultaneously.

Метод отримання списку населених пунктів за першими символами та областю, або поштовим індексом/КОАТУУ. Повертає об'єкт у форматі JSON. Параметри **sRequest** та **sPostCode** не можуть використовуватися одночасно.

Параметр **sRegion** є необов'язковим. Використовується разом з sRequest для обмеження пошуку певною областю. Дуже корисно для пошуку населених пунктів з популярними назвами напр.: "Іванівка". Замість всіх існуючих Іванівок можна отримати тільки села з певної області. В значенні цього параметра допускається неповна назва області, напр.: "Микол".

Response:
У полі **"Area"** зазначено актуальну назву району.
У полі **"AreaOld"** зазначено назву району до реформи 2020р. Якщо раніше нас. пункт не підпорядковувався району - **"AreaOld"** буде "null". У полі **"CityString"** зібрано найбільш потрібну інформацію для точної ідентифікації населеного пункту. Напр.:

`"село Тарасівка, Врадіївська гр., Первомайський р-н (Врадіївський), Миколаївська обл."` Тут вказано назву, громаду, район, область та старі назви в дужках у випадку перейменувань. Призначення цього поля - наповнення випадаючих списків з підказками варіантів. **Формат і склад цього текстового рядка може коригуватися в майбутньому**. За потреби можна зібрати аналогічний рядок на свій власний смак з полів JSON відповіді.

AUTHORIZATIONBearer Token

This request is using Bearer Token from collection[Geodata.online](https://documenter.getpostman.com/view/2267163/7E8jGij?version=latest#auth-info-ccb379d0-eaf8-5b05-a8fe-83d4a6c073aa)

HEADERS

Authorization

Bearer {{token}}

PARAMS

sRequest

Тарас

City name (may be used instead of sPostCode).
Використовується як альтернатива sPostCode

sLang

ru_RU

Optional. response language (uk by default).
Вибір мови видачі (за замовчуванням українська)

sPostCode

UA80000000000093317

search by postcode, KOATUU, KATOTTG (may be used instead of sRequest).
приймає поштовий індекс, або КОАТУУ, або КАТОТТГ, альтернатива sRequest

sRegion

Микол

Optional. Limit search to specific region (область). Useful when searching for settlements with very popular name