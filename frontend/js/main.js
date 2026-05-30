/**
 * Логика за главната страница (index.html).
 *
 * Какво прави:
 * 1. При зареждане – извиква API-то за филмите
 * 2. За всеки филм създава карта (постер + заглавие)
 * 3. Добавя картите в #movies-grid
 * 4. Хваща грешки и ги показва на потребителя
 */

/**
 * Рендерира една карта за филм.
 * Показва само постер и заглавие – оценките са на страницата на филма.
 *
 * @param {object} movie – филмов обект от API-то
 * @returns {string} – HTML низ
 */
function renderMovieCard(movie) {
    const posterUrl = staticUrl(movie.poster_url);

    return `
        <a href="/movies/${movie.id}" class="movie-card-link">
            <article class="movie-card" data-movie-id="${movie.id}">
                <img
                    src="${posterUrl}"
                    alt="Постер на ${movie.title}"
                    class="movie-poster"
                >
                <div class="movie-info">
                    <h3 class="movie-title">${movie.title}</h3>
                </div>
            </article>
        </a>
    `;
}

/**
 * Зарежда филмите от API-то и ги показва на страницата.
 */
async function loadMovies() {
    const gridElement = document.getElementById("movies-grid");
    const countElement = document.getElementById("movies-count");

    try {
        const data = await fetchMovies();

        // Показваме броя филми до заглавието "Всички филми"
        if (countElement) {
            countElement.textContent = `${data.count} заглавия`;
        }

        gridElement.innerHTML = data.movies.map(renderMovieCard).join("");
    } catch (error) {
        console.error("Грешка при зареждане на филмите:", error);
        gridElement.innerHTML = `<p class="error-msg">Грешка при зареждане: ${error.message}</p>`;
    }
}

document.addEventListener("DOMContentLoaded", loadMovies);