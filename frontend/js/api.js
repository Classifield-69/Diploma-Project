/**
 * API wrapper – единственото място където се правят fetch заявки.
 *
 * Всички останали JS файлове викат функциите оттук, вместо да правят
 * fetch директно. Така ако нещо в API-то се промени (URL, headers,
 * error handling), променяме само този файл.
 *
 * Защо така:
 * - Едно място за base URL → лесна смяна (dev/production)
 * - Едно място за JWT token → автоматично се добавя към всички заявки
 * - Едно място за error handling → консистентни грешки
 */

// Base URL на backend API-то. Празен string означава "същия origin" –
// тъй като Flask сервира и frontend-а, и API-то на същия порт (5001),
// можем да ползваме относителни пътища като /api/movies.
const API_BASE = "";

// Префикс за статичните файлове (постери, икони и т.н.)
// Backend връща poster_url като /img/posters/x.webp, но Flask ги
// сервира на /static/img/posters/x.webp – затова добавяме префикс.
const STATIC_PREFIX = "/static";


/**
 * Превръща API-овски път към статичен файл в реален URL за браузъра.
 * Пример: "/img/posters/oppenheimer.webp" → "/static/img/posters/oppenheimer.webp"
 */
function staticUrl(path) {
    return STATIC_PREFIX + path;
}


/**
 * Базова fetch функция – обвива fetch() с обработка на JSON и грешки.
 *
 * @param {string} endpoint – пътят след API_BASE (напр. "/api/movies")
 * @param {object} options – стандартните fetch опции (method, body, и т.н.)
 * @returns {Promise<object>} – парснатият JSON отговор
 * @throws {Error} – ако response статусът е >= 400
 */
async function apiRequest(endpoint, options = {}) {
    const url = API_BASE + endpoint;

    // Default headers – Content-Type за JSON заявки
    const headers = {
        "Content-Type": "application/json",
        ...options.headers,
    };

    // Ако имаме JWT token в localStorage – добавяме го автоматично.
    // (login.html по-късно ще го запазва там след успешен login)
    const token = localStorage.getItem("jwt_token");
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(url, { ...options, headers });

    // Парсваме JSON отговора (дори при грешка – Flask връща JSON с error message)
    const data = await response.json();

    if (!response.ok) {
        // Хвърляме грешка с message-а от backend-а (ако има такъв)
        throw new Error(data.error || data.message || `HTTP ${response.status}`);
    }

    return data;
}


// ============================================================
// Конкретни API функции – по-добре от това да викаме apiRequest
// директно от main.js, защото имената им документират какво правят.
// ============================================================

/**
 * Взима списък с всички филми.
 * @returns {Promise<{count: number, movies: Array}>}
 */
async function fetchMovies() {
    return apiRequest("/api/movies");
}

/**
 * Взима детайли за конкретен филм по ID.
 * @param {number} movieId
 * @returns {Promise<object>}
 */
async function fetchMovieById(movieId) {
    return apiRequest(`/api/movies/${movieId}`);
}

/**
 * Взима всички ревюта за конкретен филм.
 * @param {number} movieId
 * @returns {Promise<{count: number, movie_id: number, reviews: Array}>}
 */
async function fetchMovieReviews(movieId) {
    return apiRequest(`/api/movies/${movieId}/reviews`);
}



// ============================================================
// Authentication функции
// ============================================================

// Ключове за localStorage – на едно място, за да няма typo-та
const TOKEN_KEY = "jwt_token";
const USER_KEY = "current_user";
/**
 * Логва потребител и записва токена + user данните в localStorage.
 *
 * @param {string} email
 * @param {string} password
 * @returns {Promise<object>} – обект с user данни ({id, username, email, role})
 * @throws {Error} – при грешен login (401) или мрежова грешка
 */
async function login(email, password) {
    const data = await apiRequest("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
    });

    // Запазваме токена – api.js ще го добавя автоматично към всяка следваща заявка
    localStorage.setItem(TOKEN_KEY, data.access_token);

    // Запазваме и user данните – за да ги показваме без допълнителна заявка
    // (име в navbar-а, например). JSON.stringify, защото localStorage пази
    // само string-ове.
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));

    return data.user;
}
/**
 * Излиза от системата – изтрива токена и user данните.
 * Не прави API заявка (JWT е stateless – няма какво да се "обяви" на сървъра).
 */
function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
}
/**
 * Връща текущия логнат user от localStorage (без API заявка).
 *
 * Бързо, но данните може да са остарели (ако user-ът е променен в базата).
 * За пресни данни – ползвай fetchCurrentUser().
 *
 * @returns {object|null} – user обектът или null ако не е логнат
 */
function getCurrentUser() {
    const userJson = localStorage.getItem(USER_KEY);
    if (!userJson) {
        return null;
    }
    try {
        return JSON.parse(userJson);
    } catch {
        // Ако localStorage е counterfeit-нат, чистим го
        localStorage.removeItem(USER_KEY);
        return null;
    }
}
/**
 * Проверява дали имаме валиден токен (без да проверява със сървъра).
 *
 * Само наличие на токен – може токенът да е изтекъл, ще се види при
 * първата защитена заявка (която ще върне 401).
 *
 * @returns {boolean}
 */
function isLoggedIn() {
    return localStorage.getItem(TOKEN_KEY) !== null;
}
/**
 * Взима пресни данни за текущия user от сървъра.
 * Полезно за проверка дали токенът все още е валиден.
 *
 * @returns {Promise<object>} – user обект
 * @throws {Error} – при 401 (изтекъл/невалиден токен)
 */
async function fetchCurrentUser() {
    const data = await apiRequest("/api/auth/me");
    return data.user;
}



/**
 * Регистрира нов user и веднага го логва (запазва токена).
 *
 * Backend-ът връща access_token при register също – удобно е,
 * защото потребителят не трябва да въвежда паролата си втори път.
 *
 * @param {string} username
 * @param {string} email
 * @param {string} password
 * @returns {Promise<object>} – user обект ({id, username, email, role})
 * @throws {Error} – при невалидни данни (400) или conflict (409)
 */
async function register(username, email, password) {
    const data = await apiRequest("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, email, password }),
    });

    // Автоматичен login след register – запазваме токена и user данните,
    // точно както в login() функцията.
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));

    return data.user;
}