/**
 * Рендерира navigation header-а на всяка страница.
 * Зависи от api.js (getCurrentUser, logout) — трябва да се зарежда след него.
 */


/** @returns {string} HTML низ на header-а според auth state */
function renderHeader() {
    const user = getCurrentUser();

    const logo = `<a href="/" class="nav-logo">FilmSight</a>`;

    let navRight;

    if (user === null) {
        navRight = `
            <div class="nav-right">
                <a href="/register" class="nav-btn nav-btn--outline">Регистрация</a>
                <a href="/login" class="nav-btn nav-btn--outline">Вход</a>
            </div>
        `;
    } else if (user.role === "admin") {
        navRight = `
            <div class="nav-right">
                <span class="nav-user nav-user-admin">👑 ${escapeHeaderText(user.username)}</span>
                <button id="logout-btn" class="nav-btn nav-btn--outline">Изход</button>
            </div>
        `;
    } else {
        navRight = `
            <div class="nav-right">
                <span class="nav-user">Здравей, ${escapeHeaderText(user.username)}</span>
                <button id="logout-btn" class="nav-btn nav-btn--outline">Изход</button>
            </div>
        `;
    }

    return `
        <nav class="nav">
            ${logo}
            <a href="/" class="nav-link">Начало</a>
            ${navRight}
        </nav>
    `;
}


/**
 * Escape за защита срещу XSS в username.
 * Дублирано от reviews.js, защото header.js се зарежда и на страници без reviews.js.
 *
 * @param {string} text
 * @returns {string}
 */
function escapeHeaderText(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}


/** Обработва клик на бутона Изход. */
function handleLogout() {
    logout();
    window.location.href = "/";
}


/** Намира .site-header контейнера и го рендира. */
function initHeader() {
    const container = document.querySelector(".site-header");
    if (!container) return;

    // Запазваме tagline елемента преди да пренапишем innerHTML
    const tagline = container.querySelector(".nav-tagline");
    container.innerHTML = renderHeader();
    if (tagline) container.appendChild(tagline);

    const logoutBtn = container.querySelector("#logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", handleLogout);
    }
}


document.addEventListener("DOMContentLoaded", initHeader);