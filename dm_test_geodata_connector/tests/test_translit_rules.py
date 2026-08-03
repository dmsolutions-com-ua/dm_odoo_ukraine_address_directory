from odoo.addons.dm_geodata_connector.models.geodata_translit import transliterate
from odoo.tests.common import TransactionCase

# Приклади з таблиці транслітерації Постанови КМУ №55 від 27.01.2010 — по одному
# на кожну літеру українського алфавіту, дослівно як у додатку до постанови.
_OFFICIAL_EXAMPLES = [
    ("Алушта", "Alushta"),                  # А
    ("Борщагівка", "Borshchahivka"),        # Б (і Щ)
    ("Вінниця", "Vinnytsia"),               # В
    ("Гадяч", "Hadiach"),                   # Г
    ("Ґалаґан", "Galagan"),                 # Ґ
    ("Донецьк", "Donetsk"),                 # Д (і м'який знак)
    ("Рівне", "Rivne"),                     # Е
    ("Єнакієве", "Yenakiieve"),             # Є на початку і в середині
    ("Гаєвич", "Haievych"),                 # Є не на початку
    ("Житомир", "Zhytomyr"),                # Ж
    ("Закарпаття", "Zakarpattia"),          # З
    ("Медвин", "Medvyn"),                   # И
    ("Іванків", "Ivankiv"),                 # І
    ("Їжакевич", "Yizhakevych"),            # Ї на початку
    ("Кадиївка", "Kadyivka"),               # Ї не на початку
    ("Йосипівка", "Yosypivka"),             # Й на початку
    ("Олексій", "Oleksii"),                 # Й не на початку
    ("Київ", "Kyiv"),                       # К
    ("Лебедин", "Lebedyn"),                 # Л
    ("Миколаїв", "Mykolaiv"),               # М
    ("Ніжин", "Nizhyn"),                    # Н
    ("Одеса", "Odesa"),                     # О
    ("Полтава", "Poltava"),                 # П
    ("Решетилівка", "Reshetylivka"),        # Р
    ("Суми", "Sumy"),                       # С
    ("Тернопіль", "Ternopil"),              # Т
    ("Ужгород", "Uzhhorod"),                # У
    ("Фастів", "Fastiv"),                   # Ф
    ("Харків", "Kharkiv"),                  # Х
    ("Біла Церква", "Bila Tserkva"),        # Ц
    ("Чернівці", "Chernivtsi"),             # Ч
    ("Шостка", "Shostka"),                  # Ш
    ("Щербухи", "Shcherbukhy"),             # Щ
    ("Юрій", "Yurii"),                      # Ю на початку
    ("Корюківка", "Koriukivka"),            # Ю не на початку
    ("Яготин", "Yahotyn"),                  # Я на початку
    ("Костянтин", "Kostiantyn"),            # Я не на початку
]


class TestTranslitRules(TransactionCase):
    """The local transliterator must reproduce the official CMU No. 55 table:
    every letter, both positional variants, and the notes under the table
    (the "зг" -> "zgh" digraph, the dropped soft sign and apostrophe)."""

    def test_official_table_examples(self):
        for source, expected in _OFFICIAL_EXAMPLES:
            with self.subTest(source=source):
                self.assertEqual(transliterate(source), expected)

    def test_zgh_digraph(self):
        # Примітка 1: "зг" -> "zgh" (на відміну від "ж" -> "zh").
        self.assertEqual(transliterate("Згорани"), "Zghorany")
        self.assertEqual(transliterate("Розгон"), "Rozghon")
        # Контроль: одиночна "ж" лишається "zh".
        self.assertEqual(transliterate("Жашків"), "Zhashkiv")

    def test_apostrophe_and_soft_sign_dropped(self):
        # Примітка 2: не відтворюються; апостроф при цьому не розриває слово,
        # тож "я" після нього — НЕ початок слова ("ia", а не "ya").
        self.assertEqual(transliterate("Знам'янка"), "Znamianka")
        self.assertEqual(transliterate("Знам’янка"), "Znamianka")
        self.assertEqual(transliterate("Луцьк"), "Lutsk")

    def test_uppercase_input(self):
        self.assertEqual(transliterate("ЖИТОМИР"), "ZHYTOMYR")
        self.assertEqual(transliterate("ЩЕРБУХИ"), "SHCHERBUKHY")
        self.assertEqual(transliterate("РОЗГОН"), "ROZGHON")

    def test_word_boundaries(self):
        # Дефіс і пробіл починають нове слово; апостроф — ні (див. вище).
        self.assertEqual(transliterate("Івано-Франківськ"), "Ivano-Frankivsk")
        self.assertEqual(transliterate("Переяслав-Хмельницький"),
                         "Pereiaslav-Khmelnytskyi")
        self.assertEqual(transliterate("Кам'янець-Подільський"),
                         "Kamianets-Podilskyi")

    def test_abbreviations_and_punctuation(self):
        # Крапки, дефіси й цифри проходять наскрізь — абревіатури зберігають форму.
        self.assertEqual(transliterate("вул."), "vul.")
        self.assertEqual(transliterate("просп."), "prosp.")
        self.assertEqual(transliterate("обл."), "obl.")
        self.assertEqual(transliterate("р-н"), "r-n")
        self.assertEqual(transliterate("смт"), "smt")
        self.assertEqual(transliterate("м."), "m.")
        self.assertEqual(transliterate("14Д"), "14D")

    def test_empty_and_latin_input(self):
        self.assertEqual(transliterate(""), "")
        self.assertEqual(transliterate(False), "")
        self.assertEqual(transliterate(None), "")
        # Ідемпотентність: латиниця на вході лишається незмінною.
        self.assertEqual(transliterate("vul. Khreshchatyk, 1B"),
                         "vul. Khreshchatyk, 1B")

    def test_no_cyrillic_leaks(self):
        source = "Львівська обл., смт Брюховичі, вул. Ґудзика, 14Д, кв. 5"
        result = transliterate(source)
        self.assertFalse(
            [ch for ch in result if "Ѐ" <= ch <= "ӿ"],
            "transliterated text must not contain Cyrillic: %s" % result)
        self.assertEqual(
            result, "Lvivska obl., smt Briukhovychi, vul. Gudzyka, 14D, kv. 5")
