/**
 * analysis.js — логика на бутона "Analyze" (admin only).
 *
 * Самият бутон се рендира от reviews.js, но САМО ако текущият user е admin.
 * Тук закачаме click handler, който:
 *   1. Disabled-ва бутона + показва loading съобщение
 *   2. Вика analyzeMovie() от api.js (5-10 сек при първи request след startup)
 *   3. При успех с нови анализи → reload на страницата за да се видят оценките
 *   4. При успех без нови анализи → съобщение "вече е анализирано"
 *   5. При грешка → показва съобщението и re-enable-ва бутона
 *
 * Зависи от api.js (analyzeMovie функцията).
 *
 * Защо event delegation: бутонът се рендира динамично от reviews.js СЛЕД
 * като дойде API отговорът, тоест бутонът не съществува при DOMContentLoaded.
 * Event delegation решава това — listener-ът е на document и улавя кликове
 * на бутона, без значение кога е добавен в DOM-а.
 */


/**
 * Обработва клик на Analyze бутона.
 *
 * @param {Event} event – click event-ът
 */
async function handleAnalyzeClick(event) {
    const btn = event.target;
    const statusEl = document.getElementById("analyze-status");

    // Извличаме movieId от data атрибута на бутона.
    // Така analysis.js не трябва да дублира getMovieIdFromUrl() от reviews.js.
    const movieId = parseInt(btn.dataset.movieId, 10);
    if (Number.isNaN(movieId)) {
        console.error("Невалиден movie ID в analyze бутона");
        return;
    }

    // Запазваме оригиналния текст за да го възстановим при грешка
    const originalText = btn.textContent;

    // Loading state — disabled-ваме бутона + показваме съобщение
    btn.disabled = true;
    btn.textContent = "Анализирам...";
    if (statusEl) {
        statusEl.textContent = "Моля изчакайте 5–10 секунди (зареждане на ML моделите при първи request)...";
        statusEl.style.color = "";  // reset стария цвят ако е имало грешка
    }

    try {
        const result = await analyzeMovie(movieId);

        if (result.newly_analyzed_count > 0) {
            // Има нови анализи — reload-ваме за да се покажат
            // (по-чисто отколкото да rerender-ваме всичко през JS)
            window.location.reload();
        } else {
            // Нямаше нищо за анализ — само показваме съобщение
            if (statusEl) {
                statusEl.textContent = "Всички ревюта вече са анализирани.";
                statusEl.style.color = "green";
            }
            btn.disabled = false;
            btn.textContent = originalText;
        }
    } catch (error) {
        console.error("Грешка при анализ:", error);
        if (statusEl) {
            statusEl.textContent = `Грешка: ${error.message}`;
            statusEl.style.color = "red";
        }
        btn.disabled = false;
        btn.textContent = originalText;
    }
}


/**
 * Инициализация — закачаме event delegation listener на document.
 *
 * Listener-ът проверява дали кликнатият елемент е analyze бутонът.
 * Така не зависим от това КОГА reviews.js рендира бутона.
 */
function initAnalyze() {
    document.addEventListener("click", (event) => {
        if (event.target && event.target.id === "analyze-btn") {
            handleAnalyzeClick(event);
        }
    });
}


document.addEventListener("DOMContentLoaded", initAnalyze);
