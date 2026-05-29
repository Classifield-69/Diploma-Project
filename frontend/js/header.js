/**
 * header.js — рендериране на site-wide navigation header.
 *
 * Зарежда се на ВСЯКА страница. Намира контейнера #site-header
 * и го запълва с нав според auth state-а:
 *   - Гост:  лого + "Вход" + "Регистрация"
 *   - User:  лого + "Здравей, {username}" + "Изход"
 *   - Admin: лого + "👑 {username}" + "Изход"
 *
 * Зависи от api.js за getCurrentUser() и logout().
 * Затова api.js трябва да се зарежда ПРЕДИ header.js.
 */


/**
 * Рендерира HTML-а на header-а според auth state.
 *
 * @returns {string} HTML низ
 */
function renderHeader() {
    const user = getCurrentUser();

    // Логото е винаги едно и също — линк към началната страница
    const logo = `<a href="/" class="site-logo">🎬 Филмови ревюта</a>`;

    // Динамичната част — auth actions вдясно
    let actions;

    if (user === null) {
        // Гост — линкове за вход и регистрация
        actions = `
            <a href="/login" class="nav-link">Вход</a>
            <a href="/register" class="nav-link">Регистрация</a>
        `;
    } else if (user.role === "admin") {
        // Admin — име с корона + Изход
        actions = `
            <span class="nav-user nav-user-admin">👑 ${escapeHeaderText(user.username)}</span>
            <button id="logout-btn" class="nav-link nav-button">Изход</button>
        `;
    } else {
        // Обикновен user — поздрав + Изход
        actions = `
            <span class="nav-user">Здравей, ${escapeHeaderText(user.username)}</span>
            <button id="logout-btn" class="nav-link nav-button">Изход</button>
        `;
    }

    return `
        <nav class="site-header-inner">
            ${logo}
            <div class="nav-actions">${actions}</div>
        </nav>
    `;
}


/**
 * Локален escape за защита срещу XSS в username.
 *
 * Дублираме escapeHtml от reviews.js, защото header.js се зарежда и на
 * страници, които НЕ зареждат reviews.js (index, login, register).
 * По-добре малко дублирана функция, отколкото да караме всяка страница
 * да зарежда reviews.js само заради едно escape.
 *
 * @param {string} text
 * @returns {string}
 */
function escapeHeaderText(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}


/**
 * Обработва клик на Изход бутона.
 */
function handleLogout() {
    logout();  // от api.js — изтрива token + user от localStorage
    // Redirect към началната страница. Header.js ще се изпълни отново
    // на новата страница и ще се рендира като "Гост" view, понеже
    // localStorage вече е чист.
    window.location.href = "/";
}


/**
 * Инициализира header-а — намира контейнера и го рендира.
 */
function initHeader() {
    const container = document.getElementById("site-header");
    if (!container) return;  // на тази страница няма header контейнер

    container.innerHTML = renderHeader();

    // Закачаме listener за Изход бутона (ако сме рендирали такъв).
    // querySelector на самия container, за да не търсим в целия DOM.
    const logoutBtn = container.querySelector("#logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", handleLogout);
    }
}


document.addEventListener("DOMContentLoaded", initHeader);
