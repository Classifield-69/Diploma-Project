/**
 * Логика за страницата с детайли на филм (movie-details.html).
 *
 * Какво прави:
 * 1. Чете movie ID от URL-а (например /movies/5 → id = 5)
 * 2. Извиква API-то за детайлите на филма
 * 3. Извиква API-то за ревютата на филма
 * 4. Рендерира всичко на страницата
 */


/**
 * Извлича movie ID от URL-а.
 * URL pattern: /movies/<id> – например /movies/5
 *
 * @returns {number|null}
 */
function getMovieIdFromUrl() {
    const parts = window.location.pathname.split("/");
    const idString = parts[parts.length - 1];
    const id = parseInt(idString, 10);
    return Number.isNaN(id) ? null : id;
}

/**
 * Форматира ML оценка в четим вид.
 *
 * @param {number|null} value
 * @returns {string} "4.56 / 5.0" или null ако не е анализирано
 */
function formatRating(value) {
    if (value === null || value === undefined) return null;
    return `${value.toFixed(2)} / 5.0`;
}

/**
 * Рендерира горната секция на страницата:
 * постер вляво, инфо (заглавие, мета, оценки, analyze) вдясно.
 *
 * @param {object} movie – обект от /api/movies/<id>
 * @returns {string} – HTML низ
 */
function renderMovieInfo(movie) {
    const posterUrl = staticUrl(movie.poster_url);
    const genres = movie.genres.join(", ");
    const actors = movie.actors.join(", ");
    const reviewsCount = movie.stats.reviews_count;

    // ML оценки — ако са null показваме "pending" хапче
    const lstmRating   = formatRating(movie.stats.avg_lstm_prediction);
    const bilstmRating = formatRating(movie.stats.avg_bilstm_prediction);

    const lstmPill = lstmRating
        ? `<span class="score-pill score-pill--lstm">LSTM: ${lstmRating}</span>`
        : `<span class="score-pill score-pill--pending">LSTM: Не е анализирано</span>`;

    const bilstmPill = bilstmRating
        ? `<span class="score-pill score-pill--bilstm">BiLSTM: ${bilstmRating}</span>`
        : `<span class="score-pill score-pill--pending">BiLSTM: Не е анализирано</span>`;

    // Analyze бутон — само за admin
    const user = getCurrentUser();
    const isAdmin = user && user.role === "admin";

    const analyzeSection = isAdmin
        ? `<div class="analyze-section">
               <button id="analyze-btn" data-movie-id="${movie.id}">Analyze</button>
               <p id="analyze-status"></p>
           </div>`
        : "";

    return `
        <img
            src="${posterUrl}"
            alt="Постер на ${movie.title}"
            class="film-poster-large"
        >
        <div class="film-info-text">
            <div>
                <h1 class="film-title">
                    ${movie.title}
                    <span class="movie-year">(${movie.year})</span>
                </h1>
            </div>

            <hr class="film-divider">

            <div class="film-meta">
                <p><strong>Режисьор:</strong> ${movie.director}</p>
                <p><strong>Актьори:</strong> ${actors}</p>
                <p><strong>Жанрове:</strong> ${genres}</p>
                <p><strong>Брой ревюта:</strong> ${reviewsCount}</p>
            </div>

            <hr class="film-divider">

            <div class="film-scores">
                ${lstmPill}
                ${bilstmPill}
            </div>

            ${analyzeSection}
        </div>
    `;
}

/**
 * Форматира ISO datetime в български формат.
 * "2026-05-23T14:19:00" → "23.05.2026 г., 14:19"
 *
 * @param {string} isoString
 * @returns {string}
 */
function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString("bg-BG", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
}

/**
 * Рендерира едно ревю.
 *
 * @param {object} review – обект от /api/movies/<id>/reviews
 * @returns {string} – HTML низ
 */
function renderReview(review) {
    const date     = formatDate(review.created_at);
    const safeText = escapeHtml(review.text);

    // ML тагове — показваме само ако И двете оценки са налични
    const hasPredictions =
        review.lstm_prediction !== null &&
        review.bilstm_prediction !== null;

    const predictionsHtml = hasPredictions
        ? `<div class="review-predictions">
               <span class="review-tag">LSTM: ${review.lstm_prediction.toFixed(2)} / 5.0</span>
               <span class="review-tag">BiLSTM: ${review.bilstm_prediction.toFixed(2)} / 5.0</span>
           </div>`
        : `<div class="review-predictions">
               <span class="review-tag review-tag--empty">Все още не е анализирано</span>
           </div>`;

    return `
        <article class="review">
            <header class="review-header">
                <strong class="review-author">${escapeHtml(review.user.username)}</strong>
                <time class="review-date">${date}</time>
            </header>
            <p class="review-text">${safeText}</p>
            ${predictionsHtml}
        </article>
    `;
}

/**
 * Защита срещу XSS — превръща опасни символи в HTML entities.
 *
 * @param {string} text
 * @returns {string}
 */
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Главна функция — зарежда детайлите и ревютата паралелно.
 */
async function loadMovieDetailsPage() {
    const movieId        = getMovieIdFromUrl();
    const statusEl       = document.getElementById("status");
    const movieInfoEl    = document.getElementById("movie-info");
    const reviewsListEl  = document.getElementById("reviews-list");
    const reviewsHeading = document.getElementById("reviews-heading");

    if (movieId === null) {
        statusEl.textContent = "Невалиден URL – не може да се определи ID на филма.";
        statusEl.classList.add("error");
        return;
    }

    try {
        statusEl.textContent = "Зареждане...";

        // Двете заявки тръгват паралелно
        const [movieData, reviewsData] = await Promise.all([
            fetchMovieById(movieId),
            fetchMovieReviews(movieId),
        ]);

        // Рендерираме детайлите
        movieInfoEl.innerHTML = renderMovieInfo(movieData.movie);

        // Рендерираме ревютата
        const count = reviewsData.count;
        reviewsHeading.innerHTML = `
            <span class="section-title">Ревюта</span>
            <span class="section-count">${count} общо</span>
        `;
        reviewsHeading.style.display = "";

        reviewsListEl.innerHTML = count > 0
            ? reviewsData.reviews.map(renderReview).join("")
            : `<p class="reviews-empty">Все още няма ревюта за този филм.</p>`;

        // Скриваме статус съобщението
        statusEl.style.display = "none";

    } catch (error) {
        console.error("Грешка при зареждане:", error);
        statusEl.textContent = `Грешка: ${error.message}`;
        statusEl.classList.add("error");
    }
}

document.addEventListener("DOMContentLoaded", loadMovieDetailsPage);