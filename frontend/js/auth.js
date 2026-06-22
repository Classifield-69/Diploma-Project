/** Логика за login и register страниците. Зависи от api.js. */


/**
 * Показва статус съобщение в #status елемента.
 * @param {string} text
 * @param {'success'|'error'|''} type
 */
function setStatus(text, type = "") {
    const statusEl = document.getElementById("status");
    if (!statusEl) return;

    statusEl.textContent = text;
    statusEl.className = "auth-status";
    if (type) statusEl.classList.add(type);
}


// ============================================================
// Login
// ============================================================

/** @param {Event} event */
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

        setTimeout(() => {
            window.location.href = "/";
        }, 800);

    } catch (error) {
        console.error("Login грешка:", error);
        setStatus(error.message || "Възникна грешка при входа.", "error");
        submitButton.disabled = false;
    }
}

/** Инициализира login страницата. */
function initLoginPage() {
    const form = document.getElementById("login-form");
    if (!form) return;

    if (isLoggedIn()) {
        window.location.href = "/";
        return;
    }

    form.addEventListener("submit", handleLoginSubmit);
}


// ============================================================
// Register
// ============================================================

/** @param {Event} event */
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

        setTimeout(() => {
            window.location.href = "/";
        }, 1200);

    } catch (error) {
        console.error("Register грешка:", error);
        setStatus(error.message || "Възникна грешка при регистрацията.", "error");
        submitButton.disabled = false;
    }
}

/** Инициализира register страницата. */
function initRegisterPage() {
    const form = document.getElementById("register-form");
    if (!form) return;

    if (isLoggedIn()) {
        window.location.href = "/";
        return;
    }

    form.addEventListener("submit", handleRegisterSubmit);
}


// auth.js се зарежда и от двете страници — двете init функции сами проверяват дали са на правилната
document.addEventListener("DOMContentLoaded", () => {
    initLoginPage();
    initRegisterPage();
});