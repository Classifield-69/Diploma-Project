/**
 * Логика за страницата с детайли на филм (movie-details.html).
 *
 * Какво прави:
 * 1. Чете movie ID от URL-а (например /movies/5 → id = 5)
 * 2. Извиква API-то за детайлите на филма
 * 3. Извиква API-то за ревютата на филма
 * 4. Рендерира всичко на страницата
 *
 * Засега е read-only – не позволява писане на ревюта.
 * Когато имплементираме login, ще добавим форма за писане.
 */


/**
 * Извлича movie ID от URL-а.
 * URL pattern: /movies/<id> – например /movies/5
 *
 * @returns {number|null} – ID-то или null ако не може да се извлече
 */
function getMovieIdFromUrl() {
    // window.location.pathname = "/movies/5"
    // split("/") = ["", "movies", "5"]
    // последният елемент е ID-то
    const parts = window.location.pathname.split("/");
    const idString = parts[parts.length - 1];
    const id = parseInt(idString, 10);

    return Number.isNaN(id) ? null : id;
}


/**
 * Рендерира детайлите на филма (постер, заглавие, актьори, и т.н.)
 *
 * @param {object} movie – обект от /api/movies/<id>
 * @returns {string} – HTML низ
 */
function renderMovieInfo(movie) {
    const posterUrl = staticUrl(movie.poster_url);
    const genres = movie.genres.join(", ");
    const actors = movie.actors.join(", ");
    const reviewsCount = movie.stats.reviews_count;

    return `
        <img
            src="${posterUrl}"
            alt="Постер на ${movie.title}"
            class="movie-poster-large"
        >
        <div class="movie-info-text">
            <h1>${movie.title} <span class="movie-year">(${movie.year})</span></h1>
            <p><strong>Режисьор:</strong> ${movie.director}</p>
            <p><strong>Актьори:</strong> ${actors}</p>
            <p><strong>Жанрове:</strong> ${genres}</p>
            <p><strong>Брой ревюта:</strong> ${reviewsCount}</p>
        </div>
    `;
}


/**
 * Форматира ISO datetime низ в по-четим вид.
 * "2026-05-23T14:19:00" → "23.05.2026 г., 14:19"
 *
 * @param {string} isoString
 * @returns {string}
 */
function formatDate(isoString) {
    const date = new Date(isoString);
    // toLocaleString с "bg-BG" дава български формат на датата
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
    const date = formatDate(review.created_at);
    // textContent-style escape за да не позволим HTML injection –
    // потребителски текст не трябва да се вкарва директно в innerHTML.
    // Тук използваме textContent на временен елемент.
    const safeText = escapeHtml(review.text);

    return `
        <article class="review">
            <header class="review-header">
                <strong class="review-author">${escapeHtml(review.user.username)}</strong>
                <time class="review-date">${date}</time>
            </header>
            <p class="review-text">${safeText}</p>
        </article>
    `;
}


/**
 * Защитава срещу HTML/XSS injection в потребителски текст.
 * Превръща опасни символи (<, >, &, ", ') в техните HTML entities.
 *
 * Пример: <script>alert(1)</script> → &lt;script&gt;alert(1)&lt;/script&gt;
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
 * Главна функция – зарежда детайлите на филма и ревютата паралелно.
 */
async function loadMovieDetailsPage() {
    const movieId = getMovieIdFromUrl();
    const statusEl = document.getElementById("status");
    const movieInfoEl = document.getElementById("movie-info");
    const reviewsListEl = document.getElementById("reviews-list");
    const reviewsHeadingEl = document.getElementById("reviews-heading");

    if (movieId === null) {
        statusEl.textContent = "Невалиден URL – не може да се определи ID на филма.";
        statusEl.style.color = "red";
        return;
    }

    try {
        statusEl.textContent = "Зареждане...";

        // Promise.all – двете заявки тръгват паралелно, не една след друга.
        // Спестява време, защото не зависят една от друга.
        const [movieData, reviewsData] = await Promise.all([
            fetchMovieById(movieId),
            fetchMovieReviews(movieId),
        ]);

        // Рендерираме детайлите на филма
        movieInfoEl.innerHTML = renderMovieInfo(movieData.movie);

        // Рендерираме ревютата (ако има)
        if (reviewsData.count > 0) {
            reviewsHeadingEl.textContent = `Ревюта (${reviewsData.count})`;
            reviewsHeadingEl.style.display = "";  // прави го видим
            reviewsListEl.innerHTML = reviewsData.reviews.map(renderReview).join("");
        } else {
            reviewsHeadingEl.textContent = "Ревюта";
            reviewsHeadingEl.style.display = "";
            reviewsListEl.innerHTML = "<p>Все още няма ревюта за този филм.</p>";
        }

        // Скриваме статус съобщението – всичко е заредено
        statusEl.style.display = "none";
    } catch (error) {
        console.error("Грешка при зареждане:", error);
        statusEl.textContent = `Грешка: ${error.message}`;
        statusEl.style.color = "red";
    }
}


document.addEventListener("DOMContentLoaded", loadMovieDetailsPage);