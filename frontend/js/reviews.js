/** Логика за страницата с детайли на филм (movie-details.html). Зависи от api.js. */


/**
 * Извлича movie ID от URL-а (/movies/<id>).
 * @returns {number|null}
 */
function getMovieIdFromUrl() {
    const parts = window.location.pathname.split("/");
    const id = parseInt(parts[parts.length - 1], 10);
    return Number.isNaN(id) ? null : id;
}

/**
 * Форматира ML оценка — връща null ако стойността липсва.
 * @param {number|null} value
 * @returns {string|null} напр. "4.56 / 5.0"
 */
function formatRating(value) {
    if (value === null || value === undefined) return null;
    return `${value.toFixed(2)} / 5.0`;
}

/**
 * Рендерира горната секция: постер вляво, инфо вдясно.
 * @param {object} movie
 * @returns {string} HTML низ
 */
function renderMovieInfo(movie) {
    const posterUrl = staticUrl(movie.poster_url);
    const genres = movie.genres.join(", ");
    const actors = movie.actors.join(", ");
    const reviewsCount = movie.stats.reviews_count;

    const lstmRating   = formatRating(movie.stats.avg_lstm_prediction);
    const bilstmRating = formatRating(movie.stats.avg_bilstm_prediction);

    const lstmPill = lstmRating
        ? `<span class="score-pill score-pill--lstm">LSTM: ${lstmRating}</span>`
        : `<span class="score-pill score-pill--pending">LSTM: Не е анализирано</span>`;

    const bilstmPill = bilstmRating
        ? `<span class="score-pill score-pill--bilstm">BiLSTM: ${bilstmRating}</span>`
        : `<span class="score-pill score-pill--pending">BiLSTM: Не е анализирано</span>`;

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
 * @param {object} review
 * @returns {string} HTML низ
 */
function renderReview(review) {
    const date     = formatDate(review.created_at);
    const safeText = escapeHtml(review.text);

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
 * @param {string} text
 * @returns {string}
 */
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Рендерира формата за ревю.
 * Логнат user → форма; гост → линк към /login.
 * @param {number} movieId
 * @returns {string} HTML низ
 */
function renderReviewForm(movieId) {
    if (!isLoggedIn()) {
        return `
            <div class="review-form-section">
                <p class="review-form-login">
                    <a href="/login">Влез в акаунта си</a>, за да напишеш ревю.
                </p>
            </div>
        `;
    }

    return `
        <div class="review-form-section">
            <form id="review-form" class="review-form" novalidate>
                <textarea
                    id="review-text"
                    class="review-textarea"
                    placeholder="Напиши своето ревю... (поне 10 символа)"
                    rows="4"
                    minlength="10"
                    maxlength="5000"
                    required
                ></textarea>
                <div class="review-form-footer">
                    <span id="review-char-count" class="review-char-count">0 / 5000</span>
                    <button type="submit" class="review-submit-btn">Публикувай</button>
                </div>
                <p id="review-status" class="review-status"></p>
            </form>
        </div>
    `;
}


/** Закача submit handler и брояч на символи към формата за ревю. */
function initReviewForm(movieId) {
    const form = document.getElementById("review-form");
    if (!form) return;

    const textarea  = document.getElementById("review-text");
    const charCount = document.getElementById("review-char-count");
    const statusEl  = document.getElementById("review-status");
    const submitBtn = form.querySelector("button[type='submit']");

    textarea.addEventListener("input", () => {
        charCount.textContent = `${textarea.value.length} / 5000`;
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const text = textarea.value.trim();
        if (text.length < 10) {
            statusEl.textContent = "Ревюто трябва да е поне 10 символа.";
            statusEl.className = "review-status error";
            return;
        }

        submitBtn.disabled = true;
        statusEl.textContent = "Публикуване...";
        statusEl.className = "review-status";

        try {
            await postReview(movieId, text);
            window.location.reload();
        } catch (error) {
            console.error("Грешка при публикуване:", error);
            statusEl.textContent = error.message || "Грешка при публикуване.";
            statusEl.className = "review-status error";
            submitBtn.disabled = false;
        }
    });
}


/** Зарежда детайлите и ревютата паралелно и рендерира страницата. */
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

        const [movieData, reviewsData] = await Promise.all([
            fetchMovieById(movieId),
            fetchMovieReviews(movieId),
        ]);

        movieInfoEl.innerHTML = renderMovieInfo(movieData.movie);

        const count = reviewsData.count;
        reviewsHeading.innerHTML = `
            <span class="section-title">Ревюта</span>
            <span class="section-count">${count} общо</span>
        `;
        reviewsHeading.style.display = "";

        const formContainer = document.getElementById("review-form-container");
        if (formContainer) {
            formContainer.innerHTML = renderReviewForm(movieId);
            initReviewForm(movieId);
        }

        reviewsListEl.innerHTML = count > 0
            ? reviewsData.reviews.map(renderReview).join("")
            : `<p class="reviews-empty">Все още няма ревюта за този филм.</p>`;

        statusEl.style.display = "none";

    } catch (error) {
        console.error("Грешка при зареждане:", error);
        statusEl.textContent = `Грешка: ${error.message}`;
        statusEl.classList.add("error");
    }
}

document.addEventListener("DOMContentLoaded", loadMovieDetailsPage);