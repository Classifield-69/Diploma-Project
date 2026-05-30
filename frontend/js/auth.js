/**
 * Логика за login и register страниците.
 * Двете форми са в един файл защото споделят структура (DRY принцип).
 * Зависи от api.js (login, register, isLoggedIn функциите).
 */


/**
 * Показва статус съобщение в #status елемента.
 * Добавя CSS клас за оцветяване вместо inline style.
 *
 * @param {string} text    – съобщението
 * @param {'success'|'error'|''} type – типа (определя цвета)
 */
function setStatus(text, type = "") {
    const statusEl = document.getElementById("status");
    if (!statusEl) return;

    statusEl.textContent = text;
    statusEl.className = "auth-status";          // reset
    if (type) statusEl.classList.add(type);      // добавяме success или error
}


// ============================================================
// LOGIN
// ============================================================

/**
 * Обработва submit на login формата.
 *
 * @param {Event} event – submit event-ът
 */
async function handleLoginSubmit(event) {
    event.preventDefault();

    const emailInput    = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const submitButton  = event.target.querySelector("button[type='submit']");

    const email    = emailInput.value.trim();
    const password = passwordInput.value;

    submitButton.disabled = true;
    setStatus("Влизане...", "");

    try {
        const user = await login(email, password);

        setStatus(`Успешен вход! Здравей, ${user.username}.`, "success");

        // Кратка пауза за да види потребителят съобщението, после редирект
        setTimeout(() => {
            window.location.href = "/";
        }, 800);

    } catch (error) {
        console.error("Login грешка:", error);
        setStatus(error.message || "Възникна грешка при входа.", "error");
        submitButton.disabled = false;
    }
}

/**
 * Инициализира login страницата.
 */
function initLoginPage() {
    const form = document.getElementById("login-form");
    if (!form) return;  // не сме на login страницата

    // Ако вече сме логнати — редирект към начало
    if (isLoggedIn()) {
        window.location.href = "/";
        return;
    }

    form.addEventListener("submit", handleLoginSubmit);
}


// ============================================================
// REGISTER
// ============================================================

/**
 * Обработва submit на register формата.
 *
 * @param {Event} event
 */
async function handleRegisterSubmit(event) {
    event.preventDefault();

    const usernameInput = document.getElementById("username");
    const emailInput    = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const submitButton  = event.target.querySelector("button[type='submit']");

    const username = usernameInput.value.trim();
    const email    = emailInput.value.trim();
    const password = passwordInput.value;

    submitButton.disabled = true;
    setStatus("Регистрация...", "");

    try {
        const user = await register(username, email, password);

        setStatus(`Успешна регистрация! Добре дошъл, ${user.username}.`, "success");

        // Редирект към начало — вече сме автоматично логнати
        setTimeout(() => {
            window.location.href = "/";
        }, 1200);

    } catch (error) {
        console.error("Register грешка:", error);
        setStatus(error.message || "Възникна грешка при регистрацията.", "error");
        submitButton.disabled = false;
    }
}

/**
 * Инициализира register страницата.
 */
function initRegisterPage() {
    const form = document.getElementById("register-form");
    if (!form) return;  // не сме на register страницата

    if (isLoggedIn()) {
        window.location.href = "/";
        return;
    }

    form.addEventListener("submit", handleRegisterSubmit);
}


// ============================================================
// INIT — auth.js се зарежда и от двете страници
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
    initLoginPage();
    initRegisterPage();
});