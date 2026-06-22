/** Единственото място където се правят fetch заявки към backend-а. */

// Празен string = същия origin (Flask сервира frontend и API на един порт)
const API_BASE = "";
const STATIC_PREFIX = "";


/** Превръща път към статичен файл в URL за браузъра. */
function staticUrl(path) {
    return STATIC_PREFIX + path;
}


/**
 * Базова fetch функция с обработка на JSON и грешки.
 *
 * @param {string} endpoint – напр. "/api/movies"
 * @param {object} options  – стандартни fetch опции
 * @returns {Promise<object>}
 * @throws {Error} при response статус >= 400
 */
async function apiRequest(endpoint, options = {}) {
    const url = API_BASE + endpoint;

    const headers = {
        "Content-Type": "application/json",
        ...options.headers,
    };

    const token = localStorage.getItem("jwt_token");
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(url, { ...options, headers });
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || data.message || `HTTP ${response.status}`);
    }

    return data;
}


// ============================================================
// Филми
// ============================================================

/** @returns {Promise<{count: number, movies: Array}>} */
async function fetchMovies() {
    return apiRequest("/api/movies");
}

/** @param {number} movieId */
async function fetchMovieById(movieId) {
    return apiRequest(`/api/movies/${movieId}`);
}

/** @param {number} movieId */
async function fetchMovieReviews(movieId) {
    return apiRequest(`/api/movies/${movieId}/reviews`);
}

/**
 * Пуска ML анализ върху ревютата на филм. Admin-only endpoint.
 * Анализират се само ревютата с NULL предсказания.
 * Първото извикване след startup отнема 5–10 сек (зареждане на TensorFlow).
 *
 * @param {number} movieId
 * @returns {Promise<object>} {status, message, newly_analyzed_count, total_reviews, ...}
 * @throws {Error} 401 | 403 | 404
 */
async function analyzeMovie(movieId) {
    return apiRequest(`/api/movies/${movieId}/analyze`, {
        method: "POST",
    });
}


// ============================================================
// Автентикация
// ============================================================

// Ключове за localStorage — на едно място, за да няма typo-та
const TOKEN_KEY = "jwt_token";
const USER_KEY = "current_user";

/**
 * Логва потребител и записва токена и user данните в localStorage.
 *
 * @param {string} email
 * @param {string} password
 * @returns {Promise<object>} {id, username, email, role}
 * @throws {Error} при грешен login (401) или мрежова грешка
 */
async function login(email, password) {
    const data = await apiRequest("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
    });

    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));

    return data.user;
}

/** Излиза от системата — изтрива токена и user данните от localStorage. */
function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
}

/**
 * Връща текущия логнат user от localStorage (без API заявка).
 * @returns {object|null}
 */
function getCurrentUser() {
    const userJson = localStorage.getItem(USER_KEY);
    if (!userJson) return null;
    try {
        return JSON.parse(userJson);
    } catch {
        localStorage.removeItem(USER_KEY);
        return null;
    }
}

/**
 * Проверява дали имаме токен в localStorage (без проверка със сървъра).
 * @returns {boolean}
 */
function isLoggedIn() {
    return localStorage.getItem(TOKEN_KEY) !== null;
}

/**
 * Взима пресни данни за текущия user от сървъра.
 * @returns {Promise<object>}
 * @throws {Error} при 401 (изтекъл/невалиден токен)
 */
async function fetchCurrentUser() {
    const data = await apiRequest("/api/auth/me");
    return data.user;
}

/**
 * Публикува ново ревю за филм. Изисква JWT токен.
 *
 * @param {number} movieId
 * @param {string} text – 10–5000 символа
 * @returns {Promise<object>}
 * @throws {Error} 400 | 401 | 404
 */
async function postReview(movieId, text) {
    return apiRequest("/api/reviews", {
        method: "POST",
        body: JSON.stringify({ movie_id: movieId, text }),
    });
}

/**
 * Регистрира нов user и веднага го логва (запазва токена).
 *
 * @param {string} username
 * @param {string} email
 * @param {string} password
 * @returns {Promise<object>} {id, username, email, role}
 * @throws {Error} 400 | 409
 */
async function register(username, email, password) {
    const data = await apiRequest("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, email, password }),
    });

    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));

    return data.user;
}