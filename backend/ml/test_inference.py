# ─── Smoke test при директно пускане ───────────────────────────────────
if __name__ == '__main__':
    print('\n=== SMOKE TEST ===\n')

    test_reviews = [
        'Страхотен филм! Невероятна актьорска игра :)',
        'Много слаб филм, не препоръчвам на никого :(',
        'Беше окей, нищо особено',
        'Шедьовър! Гледах го три пъти подред!',
        'Загуба на време. Скучен и предсказуем.',
    ]

    results = predict(test_reviews)

    print(f'\n{"Текст":<60} {"LSTM":>6} {"BiLSTM":>7}')
    print('─' * 75)
    for text, r in zip(test_reviews, results):
        short = text if len(text) <= 58 else text[:55] + '...'
        print(f'{short:<60} {r["lstm_rating"]:>6.2f} {r["bilstm_rating"]:>7.2f}')
