-- ============================================================
-- Схема на базата данни за дипломен проект
-- Уеб-базирана система за анализ на филмови ревюта 
-- посредством невронни мрежи (LSTM и BiLSTM)
-- ============================================================

USE movie_reviews_db;

-- ============================================================
-- Таблица: users
-- Съхранява регистрираните потребители на системата.
-- Ролите са 'user' (стандартен потребител) и 'admin'.
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(50) NOT NULL UNIQUE,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            ENUM('user', 'admin') NOT NULL DEFAULT 'user',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Таблица: movies
-- Съхранява филмите с техните метаданни.
-- ============================================================
CREATE TABLE IF NOT EXISTS movies (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title           VARCHAR(255) NOT NULL,
    year            SMALLINT UNSIGNED NOT NULL,
    director        VARCHAR(255) NOT NULL,
    poster_url      VARCHAR(500),
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_title (title),
    INDEX idx_year (year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Таблица: genres
-- Нормализирана таблица с жанровете.
-- Един филм може да има няколко жанра (many-to-many).
-- ============================================================
CREATE TABLE IF NOT EXISTS genres (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(50) NOT NULL UNIQUE,
    
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Свързваща таблица: movie_genres
-- Реализира връзка many-to-many между movies и genres.
-- ============================================================
CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id        INT UNSIGNED NOT NULL,
    genre_id        INT UNSIGNED NOT NULL,
    
    PRIMARY KEY (movie_id, genre_id),
    
    FOREIGN KEY (movie_id) REFERENCES movies(id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id) 
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Таблица: actors
-- Нормализирана таблица с актьорите.
-- Един филм може да има няколко актьора (many-to-many).
-- ============================================================
CREATE TABLE IF NOT EXISTS actors (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Свързваща таблица: movie_actors
-- Реализира връзка many-to-many между movies и actors.
-- ============================================================
CREATE TABLE IF NOT EXISTS movie_actors (
    movie_id        INT UNSIGNED NOT NULL,
    actor_id        INT UNSIGNED NOT NULL,
    
    PRIMARY KEY (movie_id, actor_id),
    
    FOREIGN KEY (movie_id) REFERENCES movies(id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (actor_id) REFERENCES actors(id) 
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Таблица: reviews
-- Съхранява ревютата за филмите.
-- 
-- Полета за sentiment (стойности от 0.00 до 100.00):
--   - true_sentiment: реалната оценка (от OpenAI при генериране)
--   - lstm_prediction: предсказание от еднопосочната LSTM мрежа
--   - bilstm_prediction: предсказание от двупосочната BiLSTM мрежа
-- 
-- LSTM и BiLSTM полетата са NULL докато admin не натисне 
-- бутона "Analyze" за съответния филм.
-- ============================================================
CREATE TABLE IF NOT EXISTS reviews (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id             INT UNSIGNED NOT NULL,
    movie_id            INT UNSIGNED NOT NULL,
    text                TEXT NOT NULL,
    true_sentiment      DECIMAL(5, 2) DEFAULT NULL,
    lstm_prediction     DECIMAL(5, 2) DEFAULT NULL,
    bilstm_prediction   DECIMAL(5, 2) DEFAULT NULL,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (movie_id) REFERENCES movies(id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    
    INDEX idx_user_id (user_id),
    INDEX idx_movie_id (movie_id),
    INDEX idx_created_at (created_at),
    
    -- Проверки за валидност на sentiment стойностите (0-100)
    CONSTRAINT chk_true_sentiment 
    CHECK (true_sentiment IS NULL OR 
           (true_sentiment >= 0 AND true_sentiment <= 100)),
    CONSTRAINT chk_lstm_prediction 
        CHECK (lstm_prediction IS NULL OR 
               (lstm_prediction >= 0 AND lstm_prediction <= 100)),
    CONSTRAINT chk_bilstm_prediction 
        CHECK (bilstm_prediction IS NULL OR 
               (bilstm_prediction >= 0 AND bilstm_prediction <= 100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Край на schema.sql
-- ============================================================