/**
 * Логика за login и register страниците.
 *
 * Засега обработва само login. Когато създадем register.html,
 * ще добавим в същия файл и register функционалност (същата структура).
 *
 * Защо двете в един файл? Защото споделят логика – обработка на форма,
 * показване на грешки, редирект след успех. DRY принципът.
 */


/**
 * Обработва submit на login формата.
 *
 * @param {Event} event – submit event-ът от формата
 */
async function handleLoginSubmit(event) {
    // event.preventDefault() спира браузъра от default submit
    // (който щеше да зареди страницата отново с form data в URL-а).
    // Вместо това ние правим fetch заявката сами.
    event.preventDefault();

    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const submitButton = event.target.querySelector("button[type='submit']");
    const statusEl = document.getElementById("status");

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    // Изключваме бутона за да не може потребителят да цъка многократно
    // (което би пуснало множество заявки)
    submitButton.disabled = true;
    statusEl.textContent = "Влизане...";
    statusEl.style.color = "";  // reset цвят от предишна грешка

    try {
        const user = await login(email, password);

        statusEl.textContent = `Успешен вход! Здравей, ${user.username}.`;
        statusEl.style.color = "green";

        // Малка пауза за да види потребителят съобщението, после редирект.
        // setTimeout е по-добре от мигновен redirect – дава feedback.
        setTimeout(() => {
            window.location.href = "/";
        }, 800);
    } catch (error) {
        console.error("Login грешка:", error);
        statusEl.textContent = error.message || "Възникна грешка при входа.";
        statusEl.style.color = "red";
        submitButton.disabled = false;  // позволяваме нов опит
    }
}


/**
 * Главна функция за login страницата – инициализира формата.
 */
function initLoginPage() {
    const form = document.getElementById("login-form");
    if (!form) return;  // не сме на login страницата – нищо не правим

    if (isLoggedIn()) {
        window.location.href = "/";
        return;
    }

    form.addEventListener("submit", handleLoginSubmit);
}


// ============================================================
// Register функционалност
// ============================================================

/**
 * Обработва submit на register формата.
 *
 * @param {Event} event
 */
async function handleRegisterSubmit(event) {
    event.preventDefault();

    const usernameInput = document.getElementById("username");
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const submitButton = event.target.querySelector("button[type='submit']");
    const statusEl = document.getElementById("status");

    const username = usernameInput.value.trim();
    const email = emailInput.value.trim();
    const password = passwordInput.value;

    submitButton.disabled = true;
    statusEl.textContent = "Регистрация...";
    statusEl.style.color = "";

    try {
        const user = await register(username, email, password);

        statusEl.textContent = `Успешна регистрация! Добре дошъл, ${user.username}.`;
        statusEl.style.color = "green";

        // Редирект към главната страница – вече сме автоматично логнати
        setTimeout(() => {
            window.location.href = "/";
        }, 1200);
    } catch (error) {
        console.error("Register грешка:", error);
        statusEl.textContent = error.message || "Възникна грешка при регистрацията.";
        statusEl.style.color = "red";
        submitButton.disabled = false;
    }
}


/**
 * Главна функция за register страницата.
 */
function initRegisterPage() {
    const form = document.getElementById("register-form");
    if (!form) return;  // не сме на register страницата – нищо не правим

    if (isLoggedIn()) {
        window.location.href = "/";
        return;
    }

    form.addEventListener("submit", handleRegisterSubmit);
}


// auth.js се зарежда и от login.html, и от register.html –
// не знаем на коя страница сме. Затова викаме само init функцията
// за съответната форма (ако формата я няма на страницата,
// addEventListener просто няма да се изпълни – проверката е в init-а).

/**
 * При зареждане на страницата викаме инициализаторите за двете форми.
 * Всеки сам проверява дали неговата форма съществува на страницата.
 */
document.addEventListener("DOMContentLoaded", () => {
    initLoginPage();
    initRegisterPage();
});