"""
Препроцесиране на текст за inference.

ВАЖНО: Този модул повтаря 1:1 препроцесинга от 02_preprocessing.ipynb
(клетка 13, функция preprocess_text). Всяка промяна тук трябва да съответства
на промяна в notebook-а — иначе предсказанията на моделите ще са грешни.

Не зависи от TensorFlow или базата данни — само от стандартната библиотека
и numpy/keras за tokenization/padding (зареждат се от inference.py).
"""

import re


def preprocess_text(text: str) -> str:
    """
    Препроцесиране на ревю текст.

    Точно същата логика като в 02_preprocessing.ipynb. Стъпки:
      1. Lowercase
      2. Премахване на URL-и
      3. Емоджи → <smile> / <sad> / <wink> токени
      4. Изолиране на ! и ? като отделни токени
      5. Премахване на останалата пунктуация (запазва букви, цифри, ! ? < >)
      6. Нормализация на whitespace

    Args:
        text: входен текст (ревю)

    Returns:
        Почистен низ, готов за tokenizer.texts_to_sequences()
    """
    if not isinstance(text, str):
        return ''

    # 1. Lowercase
    text = text.lower()

    # 2. Премахване на URL-и
    text = re.sub(r'http\S+|www\.\S+', '', text)

    # 3. Емоджи токени (преди премахване на пунктуация!)
    # Smile: :) :)) :))) :-) =) и подобни
    text = re.sub(r'[:=][-]?[\)\]]+', ' <smile> ', text)
    # Sad: :( :(( :-( =(
    text = re.sub(r'[:=][-]?[\(\[]+', ' <sad> ', text)
    # Wink: ;) ;)) ;-)
    text = re.sub(r';[-]?[\)\]]+', ' <wink> ', text)

    # 4. Изолиране на ! и ? като отделни токени
    text = re.sub(r'!', ' ! ', text)
    text = re.sub(r'\?', ' ? ', text)

    # 5. Премахване на останалата пунктуация и специални символи
    # Запазваме: букви (кирилица + латиница), цифри, ! ? и <> за токените
    text = re.sub(r'[^а-яА-Яa-zA-Z0-9!?<>\s]', ' ', text)

    # 6. Нормализация на whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


# Бърз smoke test когато файлът се пусне директно (python preprocessing.py)
if __name__ == '__main__':
    samples = [
        'Невероятен!!! Ако искате да гледате нещо нестандартно, не се двоумете - това е филмът за вас ;))',
        'СТРАХОТЕН ФИЛМ, заслужава си всеки лев! :)',
        'Много слаб филм... Не препоръчвам :(',
        'Хобит: Неочаквано пътешествие е добре направен.',
        '',
        None,  # type: ignore
    ]
    for s in samples:
        print(f'Оригинал: {s!r}')
        print(f'Резултат: {preprocess_text(s)!r}')  # type: ignore
        print()