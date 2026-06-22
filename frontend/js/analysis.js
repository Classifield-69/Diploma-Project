/** Логика на бутона "Analyze" (само за admin). Зависи от api.js. */


/** @param {Event} event */
async function handleAnalyzeClick(event) {
    const btn = event.target;
    const statusEl = document.getElementById("analyze-status");

    const movieId = parseInt(btn.dataset.movieId, 10);
    if (Number.isNaN(movieId)) {
        console.error("Невалиден movie ID в analyze бутона");
        return;
    }

    const originalText = btn.textContent;

    btn.disabled = true;
    btn.textContent = "Анализирам...";
    if (statusEl) {
        statusEl.textContent = "Моля изчакайте 5–10 секунди (зареждане на ML моделите при първи request)...";
        statusEl.style.color = "";
    }

    try {
        const result = await analyzeMovie(movieId);

        if (result.newly_analyzed_count > 0) {
            window.location.reload();
        } else {
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
 * Инициализация — event delegation, защото бутонът се рендира динамично от reviews.js.
 */
function initAnalyze() {
    document.addEventListener("click", (event) => {
        if (event.target && event.target.id === "analyze-btn") {
            handleAnalyzeClick(event);
        }
    });
}


document.addEventListener("DOMContentLoaded", initAnalyze);